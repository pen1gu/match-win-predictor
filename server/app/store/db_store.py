from __future__ import annotations

from typing import Any, Sequence, TypeVar

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

T = TypeVar("T", bound=SQLModel)


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


async def save(session: AsyncSession, models: Sequence[SQLModel]) -> None:
    for model in models:
        await upsert_model(session, model)
    await session.commit()
