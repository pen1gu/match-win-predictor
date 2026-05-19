from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, ForeignKeyConstraint, JSON
from sqlmodel import Field, Relationship, SQLModel

from server.utils.model.db_model import TimestampMixin

if TYPE_CHECKING:
    from server.app.models.games.game import Game
    from server.app.models.players.player import Player
    from server.app.models.teams.team import Team


class PlayerGameDetails(TimestampMixin, SQLModel, table=True):
    __tablename__ = "player_game_details"
    __table_args__ = (
        ForeignKeyConstraint(
            ["game_id", "team_id"],
            ["game_details.id", "game_details.team_id"],
            name="fk_player_game_details_game_details",
        ),
    )

    game_id: int = Field(primary_key=True, foreign_key="games.id", ondelete="CASCADE")
    id: int = Field(primary_key=True, foreign_key="players.id", ondelete="CASCADE")
    team_id: int = Field(foreign_key="teams.id", ondelete="CASCADE")

    position: str | None = None
    minutes_played: int | None = None
    is_starter: bool = Field(default=False)
    substitution_in_minute: int | None = None
    substitution_out_minute: int | None = None
    rating: float | None = None
    is_man_of_the_match: bool = Field(default=False)
    goals: int = Field(default=0)
    assists: int = Field(default=0)
    shots_total: int | None = None
    shots_on_target: int | None = None
    expected_goals: float | None = None
    expected_goals_on_target: float | None = None
    expected_assists: float | None = None
    passes_completed: int | None = None
    passes_attempted: int | None = None
    pass_accuracy: float | None = None
    tackles: int | None = None
    interceptions: int | None = None
    clearances: int | None = None
    shot_events: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    yellow_cards: int = Field(default=0)
    red_cards: int = Field(default=0)
    fouls: int | None = None
    season_average_rating: float | None = None

    game: "Game" = Relationship(back_populates="player_game_details")
    player: "Player" = Relationship(back_populates="game_details")
    team: "Team" = Relationship()
