from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, JSON
from sqlmodel import Field, Relationship, SQLModel

from server.utils.model.db_model import TimestampMixin

if TYPE_CHECKING:
    from server.app.models.players.player import Player
    from server.app.models.teams.team import Team


class PlayerInfos(TimestampMixin, SQLModel, table=True):
    __tablename__ = "player_infos"

    id: int = Field(primary_key=True, foreign_key="players.id", ondelete="CASCADE")
    team_id: int | None = Field(default=None, foreign_key="teams.id", ondelete="SET NULL")
    name: str = Field(max_length=255)
    age: int | None = None
    position: list[str] | None = Field(default=None, sa_column=Column(JSON))
    role: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    shirt_number: int | None = None
    height: int | None = None
    weight: int | None = None
    birth_date: str | None = Field(default=None, max_length=32)
    birth_place: str | None = Field(default=None, max_length=255)
    birth_country: str | None = Field(default=None, max_length=128)
    birth_state: str | None = Field(default=None, max_length=128)
    nationality_code: str | None = Field(default=None, max_length=16)
    current_market_value: int | None = None
    fan_rating: float | None = None
    season_statistics: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))

    player: "Player" = Relationship(back_populates="info")
    team: "Team" = Relationship(back_populates="player_infos")
