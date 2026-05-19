from datetime import datetime

from pydantic import BaseModel, Field


class ScoreRead(BaseModel):
    home: int | None = None
    away: int | None = None


class GameStatsRead(BaseModel):
    expected_goals: float | None = None
    possession: float | None = None
    shots_total: int | None = None
    shots_on_target: int | None = None
    corners: int | None = None
    big_chances: int | None = None
    team_rating: float | None = None


class OutcomesRead(BaseModel):
    home: float | None = None
    draw: float | None = None
    away: float | None = None


class GameSummaryRead(BaseModel):
    game_id: int
    home_team: str
    away_team: str
    league_name: str | None = None
    match_round: str | None = None
    match_date: datetime
    finished: bool
    stadium: str | None = None
    score: ScoreRead
    stats: GameStatsRead | None = None
    outcomes: OutcomesRead | None = None


class LatestGamesRead(BaseModel):
    ok: bool = True
    count: int
    games: list[GameSummaryRead]


class GameOutcomesRead(BaseModel):
    game_id: int
    home_team_name: str
    away_team_name: str
    home: float
    draw: float
    away: float


class TeamMetricPoint(BaseModel):
    key: str
    label: str
    home: float | None = None
    away: float | None = None


class TeamStatsComparisonRead(BaseModel):
    game_id: int
    home_team_name: str
    away_team_name: str
    match_date: datetime
    league_name: str | None = None
    metrics: list[TeamMetricPoint]


class LineupRatingPoint(BaseModel):
    player_id: int
    name: str
    is_home: bool
    model_rating: float
    match_rating: float | None = None


class LineupRatingsRead(BaseModel):
    game_id: int
    home_team_name: str
    away_team_name: str
    players: list[LineupRatingPoint]
