from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from server.app.models.players.player import Player


class PlayerRating(SQLModel, table=True):
    __tablename__ = "player_ratings"

    id: int | None = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="players.id", ondelete="CASCADE", index=True)
    rating: float
    created_at: datetime | None = Field(
        default=None,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now(), "nullable": False},
    )

    player: "Player" = Relationship(back_populates="ratings")
