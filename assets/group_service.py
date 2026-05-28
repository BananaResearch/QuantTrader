"""策略组合 CRUD service。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..engine.errors import GroupNotFound, GroupWeightInvalid
from ..models import StrategyGroup

WEIGHT_TOLERANCE = 1e-6


def _validate_weights(allocations: list[dict[str, Any]]) -> None:
    if not allocations:
        raise GroupWeightInvalid("组合不能为空", detail={})
    total = sum(float(a["weight"]) for a in allocations)
    if abs(total - 1.0) > WEIGHT_TOLERANCE:
        raise GroupWeightInvalid(
            f"权重之和必须为 1.0，当前 {total}", detail={"sum": total}
        )


async def list_groups(
    db: AsyncSession, *, page: int = 1, page_size: int = 20
) -> tuple[list[StrategyGroup], int]:
    stmt = (
        select(StrategyGroup)
        .order_by(StrategyGroup.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.scalars(stmt)).all())
    total = int(await db.scalar(select(sa_func.count()).select_from(StrategyGroup)) or 0)
    return items, total


async def get_group(db: AsyncSession, group_id: int) -> StrategyGroup:
    g = await db.get(StrategyGroup, group_id)
    if not g:
        raise GroupNotFound(f"组合不存在: id={group_id}", detail={"id": group_id})
    return g


async def create_group(db: AsyncSession, payload: dict[str, Any]) -> StrategyGroup:
    allocations = [
        a if isinstance(a, dict) else a.model_dump() for a in payload["allocations"]
    ]
    _validate_weights(allocations)
    g = StrategyGroup(
        name=payload["name"],
        description=payload.get("description"),
        allocations=allocations,
    )
    db.add(g)
    await db.flush()
    return g


async def update_group(
    db: AsyncSession, group_id: int, payload: dict[str, Any]
) -> StrategyGroup:
    g = await get_group(db, group_id)
    if payload.get("name") is not None:
        g.name = payload["name"]
    if "description" in payload:
        g.description = payload["description"]
    if payload.get("allocations") is not None:
        allocations = [
            a if isinstance(a, dict) else a.model_dump() for a in payload["allocations"]
        ]
        _validate_weights(allocations)
        g.allocations = allocations
    await db.flush()
    return g


async def delete_group(db: AsyncSession, group_id: int) -> None:
    g = await get_group(db, group_id)
    await db.delete(g)
    await db.flush()
