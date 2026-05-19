from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.app.compute.player_rating import compute_player_rating
from server.app.models.games.game_details import GameDetails
from server.app.models.games.game_infos import GameInfos
from server.app.models.players.player import Player
from server.app.models.players.player_infos import PlayerInfos
from server.app.models.teams.team import Team
from server.app.schemas.games import LineupRatingPoint, LineupRatingsRead, TeamMetricPoint, TeamStatsComparisonRead

METRIC_LABELS = {
    "score": "득점",
    "expected_goals": "기대득점",
    "possession": "점유율",
    "shots_total": "슈팅",
    "shots_on_target": "유효슈팅",
    "corners": "코너",
    "big_chances": "빅찬스",
    "team_rating": "팀 평점",
}


def _team_name(teams: dict[int, Team], team_id: int | None, fallback: str | None) -> str:
    if team_id is not None and team_id in teams:
        return teams[team_id].name
    return fallback or "Unknown"


async def get_team_stats_comparison(session: AsyncSession, game_id: int) -> TeamStatsComparisonRead:
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

    team_ids = [team_id for team_id in (info.home_team_id, info.away_team_id) if team_id is not None]
    teams: dict[int, Team] = {}
    if team_ids:
        teams_result = await session.execute(select(Team).where(Team.id.in_(team_ids)))
        teams = {t.id: t for t in teams_result.scalars().all()}

    metrics = [
        TeamMetricPoint(key="score", label=METRIC_LABELS["score"], home=home_detail.score, away=away_detail.score),
        TeamMetricPoint(
            key="expected_goals",
            label=METRIC_LABELS["expected_goals"],
            home=home_detail.expected_goals_value,
            away=away_detail.expected_goals_value,
        ),
        TeamMetricPoint(
            key="possession",
            label=METRIC_LABELS["possession"],
            home=home_detail.possession,
            away=away_detail.possession,
        ),
        TeamMetricPoint(
            key="shots_total",
            label=METRIC_LABELS["shots_total"],
            home=home_detail.shots_total,
            away=away_detail.shots_total,
        ),
        TeamMetricPoint(
            key="shots_on_target",
            label=METRIC_LABELS["shots_on_target"],
            home=home_detail.shots_on_target,
            away=away_detail.shots_on_target,
        ),
        TeamMetricPoint(
            key="corners",
            label=METRIC_LABELS["corners"],
            home=home_detail.corners,
            away=away_detail.corners,
        ),
        TeamMetricPoint(
            key="big_chances",
            label=METRIC_LABELS["big_chances"],
            home=home_detail.big_chances,
            away=away_detail.big_chances,
        ),
        TeamMetricPoint(
            key="team_rating",
            label=METRIC_LABELS["team_rating"],
            home=home_detail.team_rating,
            away=away_detail.team_rating,
        ),
    ]

    return TeamStatsComparisonRead(
        game_id=game_id,
        home_team_name=_team_name(teams, info.home_team_id, info.home_team_name),
        away_team_name=_team_name(teams, info.away_team_id, info.away_team_name),
        match_date=info.match_date,
        league_name=info.league_name,
        metrics=metrics,
    )


async def get_lineup_ratings(session: AsyncSession, game_id: int) -> LineupRatingsRead:
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

    starter_ids = (home_detail.starting_players or []) + (away_detail.starting_players or [])
    if not starter_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="선발 라인업 선수 정보가 부족합니다.",
        )

    players_result = await session.execute(
        select(Player)
        .where(Player.id.in_(starter_ids))
        .options(
            selectinload(Player.info),
            selectinload(Player.match_affect_features),
            selectinload(Player.game_details),
        )
    )
    players = {p.id: p for p in players_result.scalars().all()}
    if len(players) != len(starter_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="선발 라인업 선수 정보가 부족합니다.",
        )

    infos_result = await session.execute(
        select(PlayerInfos).where(PlayerInfos.id.in_(starter_ids))
    )
    names = {i.id: i.name for i in infos_result.scalars().all()}

    team_ids = [team_id for team_id in (info.home_team_id, info.away_team_id) if team_id is not None]
    teams: dict[int, Team] = {}
    if team_ids:
        teams_result = await session.execute(select(Team).where(Team.id.in_(team_ids)))
        teams = {t.id: t for t in teams_result.scalars().all()}

    points: list[LineupRatingPoint] = []
    home_starters = set(home_detail.starting_players or [])
    for pid in starter_ids:
        player = players[pid]
        ratings_map = home_detail.player_ratings if pid in home_starters else away_detail.player_ratings
        match_rating = ratings_map.get(str(pid)) if ratings_map else None
        points.append(
            LineupRatingPoint(
                player_id=pid,
                name=names.get(pid, f"Player {pid}"),
                is_home=pid in home_starters,
                model_rating=compute_player_rating(player),
                match_rating=match_rating,
            )
        )

    points.sort(key=lambda p: p.model_rating, reverse=True)
    return LineupRatingsRead(
        game_id=game_id,
        home_team_name=_team_name(teams, info.home_team_id, info.home_team_name),
        away_team_name=_team_name(teams, info.away_team_id, info.away_team_name),
        players=points,
    )
