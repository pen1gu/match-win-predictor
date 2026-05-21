from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.models.games.game_details import GameDetails
from server.app.models.games.game_infos import GameInfos
from server.app.models.session import async_session_factory
from server.config.settings import Settings, settings
from server.utils.logger.get_logger import get_logger, prepare_third_party_logging, suppress_noisy_loggers

logger = get_logger(__name__)

_SEASON_YEAR_RE = re.compile(r"^(\d{2,4})/(\d{2,4})$")
_SEASON_LONG_YEAR_RE = re.compile(r"^(\d{4})/(\d{4})$")


def parse_leagues(cfg: Settings | None = None) -> list[str]:
    cfg = cfg or settings
    return cfg.backfill_league_list


def extract_season_label(text: str | None) -> str | None:
    """Pull YY/YY or YYYY/YYYY from Sofascore season labels (e.g. 'LaLiga 24/25')."""
    if not text:
        return None
    match = re.search(r"(\d{2,4}/\d{2,4})", text)
    if match:
        return normalize_season(match.group(1))
    return normalize_season(text)


def normalize_season(year: str) -> str:
    """Convert soccerdata year labels (e.g. 24/25, 00/01) to 2024/2025 style."""
    year = year.strip()
    if _SEASON_LONG_YEAR_RE.match(year):
        return year
    match = _SEASON_YEAR_RE.match(year)
    if not match:
        return year
    start, end = match.group(1), match.group(2)
    if len(start) == 4:
        return f"{start}/{end}"
    start_i = int(start)
    end_i = int(end)
    century = 2000 if start_i < 50 else 1900
    return f"{century + start_i}/{century + end_i}"


def season_start_year(season: str) -> int:
    normalized = normalize_season(season)
    match = _SEASON_LONG_YEAR_RE.match(normalized) or _SEASON_YEAR_RE.match(normalized)
    if not match:
        return 0
    start = match.group(1)
    return int(start) if len(start) == 4 else (2000 + int(start) if int(start) < 50 else 1900 + int(start))


def sofascore_reader(league: str, season: str):
    prepare_third_party_logging()
    import soccerdata as sd

    suppress_noisy_loggers()
    data_dir = Path(settings.sofascore_data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return sd.Sofascore(leagues=league, seasons=season, data_dir=data_dir)


def _league_cache_path(league: str) -> Path:
    return Path(settings.sofascore_data_dir) / "leagues" / f"{league}.json"


def _read_league_season_years(league: str) -> list[str]:
    path = _league_cache_path(league)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    seasons = data.get("seasons") or []
    return [str(s.get("year", "")).strip() for s in seasons if s.get("year")]


def load_league_seasons(league: str) -> list[str]:
    years = _read_league_season_years(league)
    if years:
        return [normalize_season(y) for y in years]
    logger.info("league cache miss, priming soccerdata reader: league=%s", league)
    reader = sofascore_reader(league, "2024/2025")
    try:
        reader.read_schedule()
    except Exception as exc:
        logger.warning("read_schedule prime failed for %s: %s", league, exc)
    years = _read_league_season_years(league)
    if not years:
        raise FileNotFoundError(f"No season metadata for league={league} under {settings.sofascore_data_dir}")
    return [normalize_season(y) for y in years]


def current_season_for_league(league: str) -> str:
    seasons = load_league_seasons(league)
    return max(seasons, key=season_start_year)


def seasons_for_backfill(
    league: str,
    *,
    start_year: int,
    through_exclusive: str | None = None,
) -> list[str]:
    seasons = load_league_seasons(league)
    filtered = [s for s in seasons if season_start_year(s) >= start_year]
    if through_exclusive is not None:
        cutoff = season_start_year(through_exclusive)
        filtered = [s for s in filtered if season_start_year(s) < cutoff]
    return sorted(filtered, key=season_start_year)


@dataclass
class SeasonCheckpoint:
    schedule_done: bool = False
    last_detail_game_id: int | None = None
    detail_failures: int = 0


@dataclass
class IngestCheckpoint:
    path: Path
    historical: dict[str, dict[str, SeasonCheckpoint]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path | None = None) -> IngestCheckpoint:
        path = Path(path or settings.ingest_state_path)
        if not path.exists():
            return cls(path=path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        historical: dict[str, dict[str, SeasonCheckpoint]] = {}
        for league, seasons in (raw.get("historical") or {}).items():
            historical[league] = {}
            for season, data in (seasons or {}).items():
                historical[league][season] = SeasonCheckpoint(
                    schedule_done=bool(data.get("schedule_done")),
                    last_detail_game_id=data.get("last_detail_game_id"),
                    detail_failures=int(data.get("detail_failures") or 0),
                )
        return cls(path=path, historical=historical)

    def get_season(self, league: str, season: str) -> SeasonCheckpoint:
        return self.historical.setdefault(league, {}).setdefault(season, SeasonCheckpoint())

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "historical": {
                league: {
                    season: {
                        "schedule_done": cp.schedule_done,
                        "last_detail_game_id": cp.last_detail_game_id,
                        "detail_failures": cp.detail_failures,
                    }
                    for season, cp in seasons.items()
                }
                for league, seasons in self.historical.items()
            }
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _lineup_missing(column) -> object:
    """True when starting_players is null or empty JSON array."""
    return or_(
        column.is_(None),
        func.coalesce(func.json_array_length(column), 0) == 0,
    )


async def fetch_game_ids_needing_detail(
    session: AsyncSession,
    *,
    league: str,
    season: str,
    after_game_id: int | None = None,
    only_finished: bool = True,
    only_past_matches: bool = False,
) -> list[int]:
    """Games missing teams, game_details, or lineups (full ingest incomplete)."""
    home_gd = GameDetails.__table__.alias("home_gd")
    away_gd = GameDetails.__table__.alias("away_gd")

    home_has_lineup = func.coalesce(func.json_array_length(home_gd.c.starting_players), 0) > 0
    away_has_lineup = func.coalesce(func.json_array_length(away_gd.c.starting_players), 0) > 0
    lineup_partial = or_(
        and_(home_has_lineup, ~away_has_lineup),
        and_(~home_has_lineup, away_has_lineup),
    )

    incomplete = or_(
        GameInfos.home_team_id.is_(None),
        GameInfos.away_team_id.is_(None),
        home_gd.c.id.is_(None),
        away_gd.c.id.is_(None),
        lineup_partial,
    )

    stmt = (
        select(GameInfos.id)
        .outerjoin(
            home_gd,
            and_(home_gd.c.id == GameInfos.id, home_gd.c.is_home.is_(True)),
        )
        .outerjoin(
            away_gd,
            and_(away_gd.c.id == GameInfos.id, away_gd.c.is_home.is_(False)),
        )
        .where(
            GameInfos.league == league,
            GameInfos.season == season,
            incomplete,
        )
        .order_by(GameInfos.id)
    )
    if only_finished:
        stmt = stmt.where(GameInfos.finished.is_(True))
    if only_past_matches:
        stmt = stmt.where(GameInfos.match_date <= func.now())
    if after_game_id is not None:
        stmt = stmt.where(GameInfos.id > after_game_id)
    result = await session.execute(stmt)
    return [row[0] for row in result.all()]


async def list_game_ids_needing_detail(
    *,
    league: str,
    season: str,
    after_game_id: int | None = None,
    only_finished: bool = True,
    only_past_matches: bool = False,
) -> list[int]:
    async with async_session_factory() as session:
        return await fetch_game_ids_needing_detail(
            session,
            league=league,
            season=season,
            after_game_id=after_game_id,
            only_finished=only_finished,
            only_past_matches=only_past_matches,
        )


async def ingest_season_full_details(
    league: str,
    season: str,
    checkpoint: IngestCheckpoint | None,
    *,
    only_finished: bool,
    only_past_matches: bool = False,
) -> int:
    """Fetch game detail (teams, players, stats) for every incomplete game in the season."""
    from server.app.crawler.sofascore_page import SofascorePageCrawlerSession
    from server.app.tasks.task import fetch_game_detail_task

    season_cp = checkpoint.get_season(league, season) if checkpoint is not None else None
    after_id = season_cp.last_detail_game_id if season_cp else None
    detail_count = 0

    async with SofascorePageCrawlerSession() as crawler:
        while True:
            game_ids = await list_game_ids_needing_detail(
                league=league,
                season=season,
                after_game_id=after_id,
                only_finished=only_finished,
                only_past_matches=only_past_matches,
            )
            if not game_ids:
                break

            for game_id in game_ids:
                try:
                    await fetch_game_detail_task(
                        game_id,
                        league=league,
                        season=season,
                        crawler=crawler,
                    )
                    detail_count += 1
                    if season_cp is not None and checkpoint is not None:
                        season_cp.last_detail_game_id = game_id
                        checkpoint.save()
                except Exception as exc:
                    if season_cp is not None and checkpoint is not None:
                        season_cp.detail_failures += 1
                        checkpoint.save()
                    logger.exception(
                        "detail ingest failed: league=%s season=%s game_id=%s err=%s",
                        league,
                        season,
                        game_id,
                        exc,
                    )
                after_id = game_id
                if settings.ingest_detail_delay_sec > 0:
                    await asyncio.sleep(settings.ingest_detail_delay_sec)

    return detail_count
