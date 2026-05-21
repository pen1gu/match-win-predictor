from __future__ import annotations

import asyncio
import math
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sofascore_httpx import SofascoreClient
from sofascore_httpx.parsers import (
    ParsedLineupPlayer,
    ParsedLineupSide,
    ParsedLineups,
    ParsedPlayerStats,
    ParsedTeamStats,
)

from server.app.models.games.game import Game
from server.app.models.games.game_details import GameDetails
from server.app.models.games.game_infos import GameInfos
from server.app.models.players.player import Player
from server.app.models.players.player_game_details import PlayerGameDetails
from server.app.models.players.player_infos import PlayerInfos
from server.app.models.teams.team import Team
from server.app.tasks.ingest_helpers import extract_season_label
from server.config.settings import settings
from server.utils.logger.get_logger import get_logger

logger = get_logger(__name__)


def _safe_int(value: Any) -> int | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        value = value.replace("%", "").replace(",", "").strip()
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, str):
        value = value.replace("%", "").replace(",", "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def build_models_from_schedule_row(
    row: pd.Series,
    *,
    league: str,
    season: str,
) -> list[Any]:
    game_id = int(row["game_id"])
    home_name = str(row["home_team"])
    away_name = str(row["away_team"])
    match_date = row["date"]
    if isinstance(match_date, pd.Timestamp):
        match_date = match_date.to_pydatetime()
    if match_date.tzinfo is None:
        match_date = match_date.replace(tzinfo=timezone.utc)

    home_score = _safe_int(row.get("home_score"))
    away_score = _safe_int(row.get("away_score"))
    finished = home_score is not None and away_score is not None

    models: list[Any] = [
        Game(id=game_id),
        GameInfos(
            id=game_id,
            home_team_name=home_name,
            away_team_name=away_name,
            match_date=match_date,
            match_name=f"{home_name} - {away_name}",
            league_name=league,
            league=league,
            season=season,
            match_round=str(row.get("round") or row.get("week") or ""),
            finished=finished,
            cancelled=False,
            next_match=not finished,
        ),
    ]
    return models


def _map_team_stats(stats: dict[str, Any]) -> dict[str, Any]:
    return {
        "possession": _safe_float(stats.get("ballPossession")),
        "shots_total": _safe_int(_first_present(stats.get("totalShotsOnGoal"), stats.get("totalShots"))),
        "shots_on_target": _safe_int(_first_present(stats.get("shotsOnGoal"), stats.get("shotsOnTarget"))),
        "corners": _safe_int(stats.get("cornerKicks")),
        "fouls": _safe_int(stats.get("fouls")),
        "yellow_cards": _safe_int(stats.get("yellowCards")),
        "red_cards": _safe_int(stats.get("redCards")),
        "expected_goals_value": _safe_float(_first_present(stats.get("expectedGoals"), stats.get("xg"))),
        "attack_stats": stats,
    }


def _lineup_side_models(
    game_id: int,
    side: ParsedLineupSide | None,
    *,
    is_home: bool,
    home_team_id: int,
    away_team_id: int,
) -> tuple[GameDetails | None, list[Any]]:
    if side is None:
        return None, []

    # Always bind lineup players to the match home/away team FK (side.team_id can be wrong).
    team_id = home_team_id if is_home else away_team_id
    starters = [p.player_id for p in side.starters]
    subs = [p.player_id for p in side.substitutes]
    ratings = {
        str(p.player_id): p.rating
        for p in side.starters + side.substitutes
        if p.rating is not None
    }

    detail = GameDetails(
        id=game_id,
        team_id=team_id,
        is_home=is_home,
        formation=side.formation,
        starting_players=starters,
        substitute_players=subs,
        player_ratings={k: float(v) for k, v in ratings.items()},
    )

    extras: list[Any] = []
    for player in side.starters + side.substitutes:
        extras.extend(
            [
                Player(id=player.player_id),
                PlayerInfos(
                    id=player.player_id,
                    team_id=team_id,
                    name=player.name,
                    shirt_number=player.shirt_number,
                    position=[player.position] if player.position else None,
                ),
                _player_game_details_from_lineup(game_id, team_id, player),
            ]
        )
    return detail, extras


def _player_game_details_from_lineup(
    game_id: int,
    team_id: int,
    player: ParsedLineupPlayer,
) -> PlayerGameDetails:
    return PlayerGameDetails(
        game_id=game_id,
        id=player.player_id,
        team_id=team_id,
        position=player.position,
        is_starter=player.is_starter,
        rating=player.rating,
    )


def _apply_parsed_player_stats(target: PlayerGameDetails, parsed: ParsedPlayerStats) -> None:
    if parsed.minutes_played is not None:
        target.minutes_played = parsed.minutes_played
    if parsed.rating is not None:
        target.rating = parsed.rating
    target.goals = parsed.goals
    target.assists = parsed.assists
    raw = parsed.raw or {}
    for key, attr in (
        ("totalShots", "shots_total"),
        ("shotsOnTarget", "shots_on_target"),
        ("expectedGoals", "expected_goals"),
        ("expectedGoalsOnTarget", "expected_goals_on_target"),
        ("expectedAssists", "expected_assists"),
        ("accuratePass", "passes_completed"),
        ("totalPass", "passes_attempted"),
        ("touches", None),
    ):
        value = raw.get(key)
        if value is None or attr is None:
            continue
        if attr == "expected_goals" or attr == "expected_goals_on_target" or attr == "expected_assists":
            target_val = _safe_float(value)
        else:
            target_val = _safe_int(value)
        if target_val is not None:
            setattr(target, attr, target_val)
    if raw.get("yellowCards") is not None:
        target.yellow_cards = _safe_int(raw.get("yellowCards")) or 0
    if raw.get("redCards") is not None:
        target.red_cards = _safe_int(raw.get("redCards")) or 0
    if raw.get("fouls") is not None:
        target.fouls = _safe_int(raw.get("fouls"))


async def _enrich_player_stats(
    client: SofascoreClient,
    game_id: int,
    models: list[Any],
) -> None:
    if not settings.ingest_fetch_player_stats:
        return
    by_player: dict[int, PlayerGameDetails] = {
        m.id: m for m in models if isinstance(m, PlayerGameDetails)
    }
    for player_id, pgd in by_player.items():
        try:
            parsed = await client.get_player_stats(game_id, player_id)
            _apply_parsed_player_stats(pgd, parsed)
        except Exception as exc:
            logger.debug("player stats skip game_id=%s player_id=%s: %s", game_id, player_id, exc)
        await asyncio.sleep(0.05)


async def build_models_from_game_detail(
    client: SofascoreClient,
    game_id: int,
) -> list[Any]:
    event = await client.get_event(game_id)
    lineups = await client.get_lineups(game_id)
    team_stats = await client.get_team_stats(game_id)
    incidents = await client.get_incidents(game_id)

    home_team_id = event.home_team.id
    away_team_id = event.away_team.id
    match_date = event.start_timestamp or datetime.now(tz=timezone.utc)
    season_label = extract_season_label(event.season_name)

    models: list[Any] = [
        Team(id=home_team_id, name=event.home_team.name, league=event.league_name),
        Team(id=away_team_id, name=event.away_team.name, league=event.league_name),
        Game(id=game_id),
        GameInfos(
            id=game_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_team_name=event.home_team.name,
            away_team_name=event.away_team.name,
            match_date=match_date,
            match_name=f"{event.home_team.name} - {event.away_team.name}",
            league_name=event.league_name,
            season=season_label,
            match_round=event.round_name,
            # league: keep schedule value (soccerdata key, e.g. ESP-La Liga) — do not set here
            stadium=event.stadium,
            referee=event.referee,
            finished=event.finished,
            cancelled=event.cancelled,
            next_match=not event.finished,
            events=incidents,
        ),
    ]

    home_detail = GameDetails(
        id=game_id,
        team_id=home_team_id,
        is_home=True,
        score=event.home_score or 0,
    )
    away_detail = GameDetails(
        id=game_id,
        team_id=away_team_id,
        is_home=False,
        score=event.away_score or 0,
    )

    _apply_team_stats(home_detail, away_detail, team_stats)
    models.extend([home_detail, away_detail])

    home_lineup_detail, home_extras = _lineup_side_models(
        game_id, lineups.home, is_home=True, home_team_id=home_team_id, away_team_id=away_team_id
    )
    away_lineup_detail, away_extras = _lineup_side_models(
        game_id, lineups.away, is_home=False, home_team_id=home_team_id, away_team_id=away_team_id
    )

    if home_lineup_detail:
        _merge_game_details(home_detail, home_lineup_detail)
    if away_lineup_detail:
        _merge_game_details(away_detail, away_lineup_detail)

    models.extend(home_extras)
    models.extend(away_extras)
    await _enrich_player_stats(client, game_id, models)
    return models


def _apply_team_stats(
    home: GameDetails,
    away: GameDetails,
    stats: ParsedTeamStats,
) -> None:
    if stats.home:
        mapped = _map_team_stats(stats.home.stats)
        for key, value in mapped.items():
            if key == "attack_stats":
                home.attack_stats = value
            elif hasattr(home, key):
                setattr(home, key, value)
    if stats.away:
        mapped = _map_team_stats(stats.away.stats)
        for key, value in mapped.items():
            if key == "attack_stats":
                away.attack_stats = value
            elif hasattr(away, key):
                setattr(away, key, value)


def _merge_game_details(target: GameDetails, source: GameDetails) -> None:
    for field in (
        "formation",
        "starting_players",
        "substitute_players",
        "player_ratings",
    ):
        value = getattr(source, field)
        if value:
            setattr(target, field, value)


def create_sofascore_client() -> SofascoreClient:
    return SofascoreClient(
        timeout=settings.http_timeout,
        max_retries=settings.http_max_retries,
        headers={"User-Agent": settings.user_agent},
    )
