from __future__ import annotations

from pathlib import Path

import soccerdata as sd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.app.compute.player_rating import compute_player_rating
from server.app.integrations.sofascore_ingest import (
    build_models_from_game_detail,
    build_models_from_schedule_row,
    create_sofascore_client,
)
from server.app.models.players.player import Player
from server.app.models.players.player_rating import PlayerRating
from server.app.models.session import async_session_factory
from server.app.store.db_store import save
from server.config.settings import settings
from server.utils.logger.get_logger import get_logger

logger = get_logger(__name__)


def _sofascore_reader(league: str, season: str) -> sd.Sofascore:
    data_dir = Path(settings.sofascore_data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return sd.Sofascore(leagues=league, seasons=season, data_dir=data_dir)


async def fetch_games_for_league_season_task(league: str, season: str) -> int:
    reader = _sofascore_reader(league, season)
    schedule = reader.read_schedule()
    count = 0
    async with async_session_factory() as session:
        for _, row in schedule.iterrows():
            models = build_models_from_schedule_row(row, league=league, season=season)
            await save(session, models)
            count += 1
    logger.info("Ingested %s schedule rows for %s %s", count, league, season)
    return count


async def fetch_game_detail_task(game_id: int) -> None:
    client = create_sofascore_client()
    models = await build_models_from_game_detail(client, game_id)
    async with async_session_factory() as session:
        await save(session, models)
    logger.info("Ingested Sofascore detail for game_id=%s", game_id)


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
    "compute_player_rating_task",
    "compute_all_player_ratings_task",
]
