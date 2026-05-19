from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.app.compute.player_rating import predict_match_outcomes
from server.app.models.games.game_details import GameDetails
from server.app.models.games.game_infos import GameInfos
from server.app.models.players.player import Player
from server.app.models.teams.team import Team
from server.app.schemas.games import (
    GameStatsRead,
    GameSummaryRead,
    LatestGamesRead,
    OutcomesRead,
    ScoreRead,
)


def _team_name(teams: dict[int, Team], team_id: int | None, fallback: str | None) -> str:
    if team_id is not None and team_id in teams:
        return teams[team_id].name
    return fallback or "Unknown"


async def _load_players_for_lineup(
    session: AsyncSession,
    player_ids: list[int],
) -> list[Player]:
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


async def _game_outcomes(session: AsyncSession, game_id: int) -> OutcomesRead | None:
    home_detail, away_detail, home_players, away_players = await _get_lineup_context(
        session, game_id
    )
    if not home_detail or not away_detail or not home_players or not away_players:
        return None
    outcomes = predict_match_outcomes(home_players, away_players)
    return OutcomesRead(**outcomes)


async def _get_lineup_context(session: AsyncSession, game_id: int):
    stmt = select(GameDetails).where(GameDetails.id == game_id)
    result = await session.execute(stmt)
    details = list(result.scalars().all())
    home_detail = next((d for d in details if d.is_home), None)
    away_detail = next((d for d in details if not d.is_home), None)
    home_players = await _load_players_for_lineup(session, home_detail.starting_players or []) if home_detail else []
    away_players = await _load_players_for_lineup(session, away_detail.starting_players or []) if away_detail else []
    return home_detail, away_detail, home_players, away_players


async def get_latest_games(
    session: AsyncSession,
    *,
    limit: int = 10,
    include_outcomes: bool = False,
) -> LatestGamesRead:
    stmt = (
        select(GameInfos)
        .order_by(GameInfos.match_date.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    infos = list(result.scalars().all())

    team_ids = {
        team_id
        for info in infos
        for team_id in (info.home_team_id, info.away_team_id)
        if team_id is not None
    }
    teams: dict[int, Team] = {}
    if team_ids:
        teams_result = await session.execute(select(Team).where(Team.id.in_(team_ids)))
        teams = {t.id: t for t in teams_result.scalars().all()}

    summaries: list[GameSummaryRead] = []
    for info in infos:
        details_result = await session.execute(
            select(GameDetails).where(GameDetails.id == info.id)
        )
        details = list(details_result.scalars().all())
        home_detail = next((d for d in details if d.is_home), None)
        away_detail = next((d for d in details if not d.is_home), None)

        stats = None
        if home_detail or away_detail:
            stats = GameStatsRead(
                expected_goals=home_detail.expected_goals_value if home_detail else None,
                possession=home_detail.possession if home_detail else None,
                shots_total=home_detail.shots_total if home_detail else None,
                shots_on_target=home_detail.shots_on_target if home_detail else None,
                corners=home_detail.corners if home_detail else None,
                big_chances=home_detail.big_chances if home_detail else None,
                team_rating=home_detail.team_rating if home_detail else None,
            )

        outcomes = None
        if include_outcomes:
            outcomes = await _game_outcomes(session, info.id)

        summaries.append(
            GameSummaryRead(
                game_id=info.id,
                home_team=_team_name(teams, info.home_team_id, info.home_team_name),
                away_team=_team_name(teams, info.away_team_id, info.away_team_name),
                league_name=info.league_name,
                match_round=info.match_round,
                match_date=info.match_date,
                finished=info.finished,
                stadium=info.stadium,
                score=ScoreRead(
                    home=home_detail.score if home_detail else None,
                    away=away_detail.score if away_detail else None,
                ),
                stats=stats,
                outcomes=outcomes,
            )
        )

    return LatestGamesRead(count=len(summaries), games=summaries)
