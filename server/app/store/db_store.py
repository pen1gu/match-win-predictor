from __future__ import annotations

from typing import Any, Sequence, TypeVar

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from server.app.models.games.game import Game
from server.app.models.games.game_details import GameDetails
from server.app.models.games.game_infos import GameInfos
from server.app.models.players.player import Player
from server.app.models.players.player_game_details import PlayerGameDetails
from server.app.models.players.player_infos import PlayerInfos
from server.app.models.teams.team import Team
from server.utils.logger.get_logger import get_logger

T = TypeVar("T", bound=SQLModel)

logger = get_logger(__name__)

_SAVE_ORDER: dict[type[SQLModel], int] = {
    Team: 0,
    Game: 1,
    GameInfos: 2,
    GameDetails: 3,
    Player: 4,
    PlayerInfos: 5,
    PlayerGameDetails: 6,
}


def _primary_key_columns(model: type[SQLModel]) -> list[str]:
    if hasattr(model, "__upsert_conflict_cols__"):
        return list(model.__upsert_conflict_cols__)  # type: ignore[attr-defined]
    table = model.__table__  # type: ignore[attr-defined]
    return [col.name for col in table.primary_key.columns]


async def upsert_model(session: AsyncSession, model: T) -> T:
    model_type = type(model)
    data = model.model_dump(exclude_unset=True)
    conflict_cols = _primary_key_columns(model_type)
    stmt = insert(model_type).values(**data)
    update_cols = {
        col: stmt.excluded[col]
        for col in data
        if col not in conflict_cols and col != "created_at"
    }
    if update_cols:
        stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=update_cols)
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
    await session.execute(stmt)
    return model


def _model_label(model: SQLModel) -> str:
    model_type = type(model)
    pk_cols = _primary_key_columns(model_type)
    pk_values = ", ".join(f"{col}={getattr(model, col)!r}" for col in pk_cols)
    return f"{model_type.__name__}({pk_values})"


def _sort_models_for_save(models: Sequence[SQLModel]) -> list[SQLModel]:
    return sorted(models, key=lambda model: _SAVE_ORDER.get(type(model), 99))


async def save(session: AsyncSession, models: Sequence[SQLModel]) -> None:
    if not models:
        return
    for model in _sort_models_for_save(models):
        await upsert_model(session, model)
        logger.debug("upserted %s", _model_label(model))
    await session.commit()
    logger.debug("committed %d model(s): %s", len(models), ", ".join(_model_label(m) for m in models))
