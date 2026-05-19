from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer
from sqlmodel import Field, Relationship, SQLModel

from server.utils.model.db_model import TimestampMixin

if TYPE_CHECKING:
    from server.app.models.players.player_game_details import PlayerGameDetails
    from server.app.models.players.player_infos import PlayerInfos
    from server.app.models.players.player_match_affect_features import PlayerMatchAffectFeatures
    from server.app.models.players.player_rating import PlayerRating


class Player(TimestampMixin, SQLModel, table=True):
    __tablename__ = "players"

    id: int = Field(
        sa_column=Column(Integer, primary_key=True, autoincrement=False),
        description="Sofascore player id",
    )

    info: "PlayerInfos" = Relationship(back_populates="player")
    match_affect_features: "PlayerMatchAffectFeatures" = Relationship(back_populates="player")
    game_details: list["PlayerGameDetails"] = Relationship(back_populates="player")
    ratings: list["PlayerRating"] = Relationship(back_populates="player")
