from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, DateTime, JSON
from sqlmodel import Field, Relationship, SQLModel

from server.utils.model.db_model import TimestampMixin

if TYPE_CHECKING:
    from server.app.models.games.game import Game


class GameInfos(TimestampMixin, SQLModel, table=True):
    __tablename__ = "game_infos"

    id: int = Field(
        primary_key=True,
        foreign_key="games.id",
        ondelete="CASCADE",
        description="Sofascore game_id",
    )
    home_team_id: int | None = Field(default=None, foreign_key="teams.id")
    away_team_id: int | None = Field(default=None, foreign_key="teams.id")
    home_team_name: str | None = Field(default=None, max_length=255)
    away_team_name: str | None = Field(default=None, max_length=255)
    match_date: datetime = Field(sa_type=DateTime(timezone=True), sa_column_kwargs={"nullable": False})
    match_name: str | None = None
    league_name: str | None = None
    league: str | None = Field(default=None, max_length=128)
    season: str | None = Field(default=None, max_length=32)
    match_round: str | None = None
    match_time_utc: str | None = None
    stadium: str | None = None
    referee: str | None = None
    attendance: int | None = None
    weather: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    next_match: bool = Field(default=False)
    finished: bool = Field(default=False)
    cancelled: bool = Field(default=False)
    halfs_info: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    events: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSON))
    shotmap: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    game: "Game" = Relationship(back_populates="game_infos")
