from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer
from sqlmodel import Field, Relationship, SQLModel

from server.utils.model.db_model import TimestampMixin

if TYPE_CHECKING:
    from server.app.models.games.game_details import GameDetails
    from server.app.models.players.player import Player
    from server.app.models.players.player_infos import PlayerInfos


class Team(TimestampMixin, SQLModel, table=True):
    __tablename__ = "teams"

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=False),
        description="Sofascore team id",
    )
    name: str = Field(max_length=255, unique=True)
    country: str | None = Field(default=None, max_length=128)
    league: str | None = Field(default=None, max_length=128)
    league_id: int | None = None
    founded: int | None = None
    stadium: str | None = Field(default=None, max_length=255)
    stadium_capacity: int | None = None
    stadium_location: str | None = Field(default=None, max_length=255)
    stadium_city: str | None = Field(default=None, max_length=128)

    player_infos: list["PlayerInfos"] = Relationship(back_populates="team")
    game_details: list["GameDetails"] = Relationship(back_populates="team")
