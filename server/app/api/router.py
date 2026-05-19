from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.models.session import get_session
from server.app.schemas.games import LatestGamesRead
from server.app.schemas.health import HealthRead
from server.app.services.games_service import get_latest_games
from server.app.services.predictions_service import get_game_outcomes
from server.app.services.visualization_service import get_lineup_ratings, get_team_stats_comparison
from server.config.settings import settings

router = APIRouter(prefix=settings.api_v1_prefix)


@router.get("/health", response_model=HealthRead)
async def health() -> HealthRead:
    return HealthRead()


@router.get("/games/latest", response_model=LatestGamesRead)
async def latest_games(
    limit: int = Query(default=10, ge=1, le=30),
    include_outcomes: bool = False,
    session: AsyncSession = Depends(get_session),
) -> LatestGamesRead:
    return await get_latest_games(session, limit=limit, include_outcomes=include_outcomes)


@router.get("/predictions/games/{game_id}/outcomes")
async def game_outcomes(game_id: int, session: AsyncSession = Depends(get_session)):
    return await get_game_outcomes(session, game_id)


@router.get("/visualization/games/{game_id}/team-stats")
async def game_team_stats(game_id: int, session: AsyncSession = Depends(get_session)):
    return await get_team_stats_comparison(session, game_id)


@router.get("/visualization/games/{game_id}/lineup-ratings")
async def game_lineup_ratings(game_id: int, session: AsyncSession = Depends(get_session)):
    return await get_lineup_ratings(session, game_id)
