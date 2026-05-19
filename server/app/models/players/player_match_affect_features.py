from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel

from server.utils.model.db_model import TimestampMixin

if TYPE_CHECKING:
    from server.app.models.players.player import Player
    from server.app.models.teams.team import Team


class PlayerMatchAffectFeatures(TimestampMixin, SQLModel, table=True):
    __tablename__ = "player_match_affect_features"

    id: int = Field(primary_key=True, foreign_key="players.id", ondelete="CASCADE")
    team_id: int | None = Field(default=None, foreign_key="teams.id", ondelete="SET NULL")
    performance_trend: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    injury_history: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    current_form: str | None = Field(default=None, max_length=32)
    form_rating: float | None = None
    recent_matches: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    availability_status: str | None = Field(default=None, max_length=64)

    player: "Player" = Relationship(back_populates="match_affect_features")
