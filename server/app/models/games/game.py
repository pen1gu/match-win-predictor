from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer
from sqlmodel import Field, Relationship, SQLModel

from server.utils.model.db_model import TimestampMixin

if TYPE_CHECKING:
    from server.app.models.games.game_details import GameDetails
    from server.app.models.games.game_infos import GameInfos
    from server.app.models.players.player_game_details import PlayerGameDetails


class Game(TimestampMixin, SQLModel, table=True):
    """Sofascore event — PK is `read_schedule.game_id`."""

    __tablename__ = "games"

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=False),
        description="Sofascore game_id",
    )

    game_infos: "GameInfos" = Relationship(back_populates="game")
    game_details: list["GameDetails"] = Relationship(back_populates="game")
    player_game_details: list["PlayerGameDetails"] = Relationship(back_populates="game")
