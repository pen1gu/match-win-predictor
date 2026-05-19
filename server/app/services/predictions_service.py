from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.app.compute.player_rating import predict_match_outcomes
from server.app.models.games.game_details import GameDetails
from server.app.models.games.game_infos import GameInfos
from server.app.models.players.player import Player
from server.app.models.teams.team import Team
from server.app.schemas.games import GameOutcomesRead


def _team_name(teams: dict[int, Team], team_id: int | None, fallback: str | None) -> str:
    if team_id is not None and team_id in teams:
        return teams[team_id].name
    return fallback or "Unknown"


async def _load_players(session: AsyncSession, player_ids: list[int]) -> list[Player]:
    if not player_ids:
        return []
    stmt = (
        select(Player)
        .where(Player.id.in_(player_ids))
        .options(
            selectinload(Player.info),
            selectinload(Player.match_affect_features),
            selectinload(Player.game_details),
        )
    )
    result = await session.execute(stmt)
    players = list(result.scalars().all())
    if len(players) != len(player_ids):
        return []
    return players


async def get_game_outcomes(session: AsyncSession, game_id: int) -> GameOutcomesRead:
    info_result = await session.execute(select(GameInfos).where(GameInfos.id == game_id))
    info = info_result.scalar_one_or_none()
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="경기를 찾을 수 없습니다.")

    details_result = await session.execute(select(GameDetails).where(GameDetails.id == game_id))
    details = list(details_result.scalars().all())
    home_detail = next((d for d in details if d.is_home), None)
    away_detail = next((d for d in details if not d.is_home), None)
    if home_detail is None or away_detail is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="홈/어웨이 경기 상세가 부족합니다.",
        )

    home_players = await _load_players(session, home_detail.starting_players or [])
    away_players = await _load_players(session, away_detail.starting_players or [])
    if not home_players or not away_players:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="선발 라인업 선수 정보가 부족합니다.",
        )

    team_ids = [team_id for team_id in (info.home_team_id, info.away_team_id) if team_id is not None]
    teams: dict[int, Team] = {}
    if team_ids:
        teams_result = await session.execute(select(Team).where(Team.id.in_(team_ids)))
        teams = {t.id: t for t in teams_result.scalars().all()}

    outcomes = predict_match_outcomes(home_players, away_players)
    return GameOutcomesRead(
        game_id=game_id,
        home_team_name=_team_name(teams, info.home_team_id, info.home_team_name),
        away_team_name=_team_name(teams, info.away_team_id, info.away_team_name),
        **outcomes,
    )
