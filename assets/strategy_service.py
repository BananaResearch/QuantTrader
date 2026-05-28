"""策略主表 CRUD 与状态流转。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..engine.errors import StrategyInUse, StrategyNotFound
from ..models import Strategy, StrategyVersion


async def list_strategies(
    db: AsyncSession,
    *,
    status: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    stmt = select(Strategy)
    count_stmt = select(sa_func.count()).select_from(Strategy)
    if status:
        stmt = stmt.where(Strategy.status == status)
        count_stmt = count_stmt.where(Strategy.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where((Strategy.name.like(like)) | (Strategy.description.like(like)))
        count_stmt = count_stmt.where(
            (Strategy.name.like(like)) | (Strategy.description.like(like))
        )
    stmt = stmt.order_by(Strategy.id.desc()).offset((page - 1) * page_size).limit(page_size)

    items = list((await db.scalars(stmt)).all())
    total = int(await db.scalar(count_stmt) or 0)

    # 附加 current_version_no
    enriched = [await _to_dict(db, s) for s in items]
    return enriched, total


async def get_strategy(db: AsyncSession, strategy_id: int) -> Strategy:
    s = await db.get(Strategy, strategy_id)
    if not s:
        raise StrategyNotFound(
            f"策略不存在: id={strategy_id}", detail={"id": strategy_id}
        )
    return s


async def get_strategy_dict(db: AsyncSession, strategy_id: int) -> dict[str, Any]:
    s = await get_strategy(db, strategy_id)
    return await _to_dict(db, s)


async def _to_dict(db: AsyncSession, s: Strategy) -> dict[str, Any]:
    version_no: int | None = None
    if s.current_version_id:
        v = await db.get(StrategyVersion, s.current_version_id)
        version_no = v.version_no if v else None
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "status": s.status,
        "timeframe": s.timeframe,
        "current_version_id": s.current_version_id,
        "current_version_no": version_no,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


async def create_strategy(db: AsyncSession, payload: dict[str, Any]) -> Strategy:
    s = Strategy(
        name=payload["name"],
        description=payload.get("description"),
        timeframe=payload["timeframe"],
        status="draft",
    )
    db.add(s)
    await db.flush()
    return s


async def update_strategy(
    db: AsyncSession, strategy_id: int, payload: dict[str, Any]
) -> Strategy:
    s = await get_strategy(db, strategy_id)
    if payload.get("name") is not None:
        s.name = payload["name"]
    if "description" in payload:
        s.description = payload["description"]
    if payload.get("timeframe") is not None and s.status == "draft":
        s.timeframe = payload["timeframe"]
    await db.flush()
    return s


async def delete_strategy(db: AsyncSession, strategy_id: int) -> None:
    s = await get_strategy(db, strategy_id)
    if s.status == "active":
        raise StrategyInUse(
            f"策略 {s.name} 仍处于 active，无法删除（请先 archive）",
            detail={"id": strategy_id, "status": s.status},
        )
    await db.delete(s)
    await db.flush()


async def archive_strategy(db: AsyncSession, strategy_id: int) -> Strategy:
    s = await get_strategy(db, strategy_id)
    s.status = "archived"
    await db.flush()
    return s
