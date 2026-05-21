from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.app.compute.player_rating import compute_player_rating
from server.app.integrations.sofascore_ingest import build_models_from_schedule_row
from server.app.crawler.sofascore_page import SofascorePageCrawlerSession
from server.app.integrations.sofascore_page_ingest import build_models_from_page_crawl
from server.app.models.players.player import Player
from server.app.models.players.player_rating import PlayerRating
from server.app.models.session import async_session_factory
from server.app.store.db_store import save
from server.app.tasks.ingest_helpers import sofascore_reader
from server.utils.logger.get_logger import get_logger

logger = get_logger(__name__)


async def fetch_games_for_league_season_task(league: str, season: str) -> int:
    logger.info("schedule ingest start: league=%s season=%s", league, season)
    reader = sofascore_reader(league, season)
    schedule = reader.read_schedule()
    total_rows = len(schedule)
    logger.info("schedule rows loaded: count=%d league=%s season=%s", total_rows, league, season)
    count = 0
    async with async_session_factory() as session:
        for _, row in schedule.iterrows():
            game_id = int(row["game_id"])
            home_team = str(row["home_team"])
            away_team = str(row["away_team"])
            models = build_models_from_schedule_row(row, league=league, season=season)
            await save(session, models)
            count += 1
            logger.debug(
                "schedule row saved: %d/%d game_id=%s %s vs %s",
                count,
                total_rows,
                game_id,
                home_team,
                away_team,
            )
            if count == 1 or count == total_rows or count % 50 == 0:
                logger.info(
                    "schedule progress: %d/%d latest game_id=%s %s vs %s",
                    count,
                    total_rows,
                    game_id,
                    home_team,
                    away_team,
                )
    logger.info("schedule ingest done: saved=%d league=%s season=%s", count, league, season)
    return count


async def fetch_game_detail_task(
    game_id: int,
    *,
    league: str | None = None,
    season: str | None = None,
    crawler: SofascorePageCrawlerSession | None = None,
) -> None:
    """Full game ingest: teams, game_infos FK, game_details, players, player_game_details."""
    logger.info("detail ingest start: game_id=%s", game_id)
    models = await build_models_from_page_crawl(
        game_id,
        league=league,
        season=season,
        crawler=crawler,
    )
    logger.info("detail models built: game_id=%s model_count=%d", game_id, len(models))
    async with async_session_factory() as session:
        await save(session, models)
    logger.info("detail ingest done: game_id=%s", game_id)


async def compute_player_rating_task(player_id: int) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Player)
            .where(Player.id == player_id)
            .options(
                selectinload(Player.info),
                selectinload(Player.match_affect_features),
                selectinload(Player.game_details),
            )
        )
        player = result.scalar_one_or_none()
        if player is None:
            return
        rating_value = compute_player_rating(player)
        last_result = await session.execute(
            select(PlayerRating)
            .where(PlayerRating.player_id == player_id)
            .order_by(PlayerRating.created_at.desc())
            .limit(1)
        )
        last = last_result.scalar_one_or_none()
        if last and last.rating == rating_value:
            return
        session.add(PlayerRating(player_id=player_id, rating=rating_value))
        await session.commit()


async def compute_all_player_ratings_task() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(Player.id))
        player_ids = [row[0] for row in result.all()]
    for player_id in player_ids:
        try:
            await compute_player_rating_task(player_id)
        except Exception as exc:
            logger.exception("player rating failed for %s: %s", player_id, exc)


tasks = [
    "fetch_games_for_league_season_task",
    "fetch_game_detail_task",
    "historical_backfill_task",
    "current_season_ingest_task",
    "compute_player_rating_task",
    "compute_all_player_ratings_task",
]
