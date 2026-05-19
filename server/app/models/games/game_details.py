from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel

from server.utils.model.db_model import TimestampMixin

if TYPE_CHECKING:
    from server.app.models.games.game import Game
    from server.app.models.teams.team import Team


class GameDetails(TimestampMixin, SQLModel, table=True):
    __tablename__ = "game_details"

    id: int = Field(primary_key=True, foreign_key="games.id", ondelete="CASCADE")
    team_id: int = Field(primary_key=True, foreign_key="teams.id", ondelete="CASCADE")

    is_home: bool = Field(default=False)
    score: int = Field(default=0)
    penalty_score: int | None = None
    is_penalty_loser: bool = Field(default=False)
    score_str: str | None = None
    penalty_shootout_reason: str | None = None
    expected_goals_value: float | None = None
    expected_assists_value: float | None = None
    expected_goals_on_target_value: float | None = None
    possession: float | None = None
    shots_total: int | None = None
    shots_on_target: int | None = None
    big_chances: int | None = None
    big_chances_missed: int | None = None
    corners: int | None = None
    fouls: int | None = None
    yellow_cards: int | None = None
    red_cards: int | None = None
    accurate_passes: int | None = None
    total_passes: int | None = None
    offsides: int | None = None
    attack_stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    passing_stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    defense_stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    duel_stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    discipline_stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    general_stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    starting_players: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    substitute_players: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    player_ratings: dict[str, float] = Field(default_factory=dict, sa_column=Column(JSON))
    lineup_power_rating: float | None = None
    formation: str | None = Field(default=None, max_length=16)
    team_rating: float | None = None
    potm_player_id: int | None = Field(default=None, foreign_key="players.id", ondelete="SET NULL")

    game: "Game" = Relationship(back_populates="game_details")
    team: "Team" = Relationship(back_populates="game_details")
