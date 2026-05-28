"""因子 CRUD + 表达式校验 service。"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..engine.compiler import compile_expression
from ..engine.errors import (
    EngineError,
    ExpressionCircularRef,
    ExpressionError,
    FactorBuiltinProtected,
    FactorInUse,
    FactorNameConflict,
    FactorNotFound,
)
from ..engine.factors.registry import (
    BUILTIN_FACTOR_SEEDS,
    BUILTIN_NAMES_OHLCV,
)
from ..models import Factor, StrategyVersion

NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")
OHLCV_FIELDS = set(BUILTIN_NAMES_OHLCV)


# ---------------------------------------------------------------------------
# 内置因子 seed
# ---------------------------------------------------------------------------
async def seed_builtin_factors(db: AsyncSession) -> int:
    """启动时调用：把内置因子写入 factors 表（已存在则跳过）。"""
    inserted = 0
    for spec in BUILTIN_FACTOR_SEEDS:
        existing = await db.scalar(select(Factor).where(Factor.name == spec["name"]))
        if existing is not None:
            continue
        f = Factor(**spec)
        db.add(f)
        inserted += 1
    if inserted:
        await db.flush()
    return inserted


# ---------------------------------------------------------------------------
# 列表 / 详情
# ---------------------------------------------------------------------------
async def list_factors(
    db: AsyncSession,
    *,
    category: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Factor], int]:
    from sqlalchemy import func as sa_func

    stmt = select(Factor)
    count_stmt = select(sa_func.count()).select_from(Factor)
    if category:
        stmt = stmt.where(Factor.category == category)
        count_stmt = count_stmt.where(Factor.category == category)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where((Factor.name.like(like)) | (Factor.description.like(like)))
        count_stmt = count_stmt.where(
            (Factor.name.like(like)) | (Factor.description.like(like))
        )
    stmt = stmt.order_by(Factor.id.asc()).offset((page - 1) * page_size).limit(page_size)

    items = list((await db.scalars(stmt)).all())
    total = int(await db.scalar(count_stmt) or 0)
    return items, total


async def get_factor(db: AsyncSession, factor_id: int) -> Factor:
    f = await db.get(Factor, factor_id)
    if not f:
        raise FactorNotFound(f"因子不存在: id={factor_id}", detail={"id": factor_id})
    return f


async def _name_exists(db: AsyncSession, name: str, exclude_id: int | None = None) -> bool:
    stmt = select(Factor.id).where(Factor.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Factor.id != exclude_id)
    return (await db.scalar(stmt)) is not None


async def _known_factor_names(db: AsyncSession) -> set[str]:
    rows = (await db.scalars(select(Factor.name))).all()
    return set(rows)


# ---------------------------------------------------------------------------
# 创建 / 修改 / 删除
# ---------------------------------------------------------------------------
async def create_factor(db: AsyncSession, payload: dict[str, Any]) -> Factor:
    name = payload["name"]
    if not NAME_PATTERN.match(name):
        raise ExpressionError(
            "因子名必须匹配 ^[a-zA-Z_][a-zA-Z0-9_]{0,63}$",
            detail={"name": name},
        )
    if name in OHLCV_FIELDS:
        raise FactorNameConflict(
            f"因子名与内置 OHLCV 字段冲突: {name}", detail={"name": name}
        )
    if await _name_exists(db, name):
        raise FactorNameConflict(f"因子名已存在: {name}", detail={"name": name})

    category = payload["category"]
    expression = payload.get("expression")
    data_source = payload.get("data_source")

    if category == "derived":
        if not expression:
            raise ExpressionError("derived 因子必须提供 expression", detail={})
        # 编译校验 + 循环依赖检查
        known = await _known_factor_names(db) - {name}
        cexpr = compile_expression(
            expression,
            ohlcv_fields=OHLCV_FIELDS,
            known_factors=known,
            param_names=set(),
        )
        if name in cexpr.info.depends_on_factors:
            raise ExpressionCircularRef(
                f"因子 {name} 引用了自身", detail={"name": name}
            )
        if data_source is None:
            data_source = {
                "type": "derived",
                "depends_on": sorted(
                    set(cexpr.info.depends_on_fields) | set(cexpr.info.depends_on_factors)
                ),
            }
    else:  # user
        if data_source is None:
            data_source = {"type": "ohlcv", "field": name}

    f = Factor(
        name=name,
        category=category,
        expression=expression,
        data_type=payload.get("data_type", "number"),
        data_source=data_source,
        description=payload.get("description"),
        is_builtin=False,
    )
    db.add(f)
    await db.flush()
    return f


async def update_factor(db: AsyncSession, factor_id: int, payload: dict[str, Any]) -> Factor:
    f = await get_factor(db, factor_id)
    if f.is_builtin:
        raise FactorBuiltinProtected(
            f"内置因子不可修改: {f.name}", detail={"id": factor_id}
        )

    new_name = payload.get("name")
    if new_name and new_name != f.name:
        if not NAME_PATTERN.match(new_name):
            raise ExpressionError("因子名格式非法", detail={"name": new_name})
        if await _name_exists(db, new_name, exclude_id=factor_id):
            raise FactorNameConflict(
                f"因子名已存在: {new_name}", detail={"name": new_name}
            )
        f.name = new_name

    if "expression" in payload and f.category == "derived":
        expression = payload["expression"]
        known = await _known_factor_names(db) - {f.name}
        cexpr = compile_expression(
            expression,
            ohlcv_fields=OHLCV_FIELDS,
            known_factors=known,
            param_names=set(),
        )
        if f.name in cexpr.info.depends_on_factors:
            raise ExpressionCircularRef(
                f"因子 {f.name} 引用了自身", detail={"name": f.name}
            )
        f.expression = expression

    if payload.get("data_type") is not None:
        f.data_type = payload["data_type"]
    if payload.get("data_source") is not None:
        f.data_source = payload["data_source"]
    if "description" in payload:
        f.description = payload["description"]

    await db.flush()
    return f


async def delete_factor(db: AsyncSession, factor_id: int) -> None:
    f = await get_factor(db, factor_id)
    if f.is_builtin:
        raise FactorBuiltinProtected(
            f"内置因子不可删除: {f.name}", detail={"id": factor_id}
        )
    # 检查是否被任何策略版本引用：拉取所有 bindings 在 Python 侧比对，
    # 避免不同方言对 JSON 列表元素匹配的差异。
    rows = (
        await db.execute(
            select(StrategyVersion.id, StrategyVersion.factor_bindings)
        )
    ).all()
    for vid, bindings in rows:
        for b in bindings or []:
            if isinstance(b, dict) and b.get("factor_id") == factor_id:
                raise FactorInUse(
                    f"因子 {f.name} 仍被策略版本 #{vid} 引用，无法删除",
                    detail={"id": factor_id, "version_id": vid},
                )
    await db.delete(f)
    await db.flush()


# ---------------------------------------------------------------------------
# 表达式校验（前端编辑器实时调用）
# ---------------------------------------------------------------------------
async def validate_expression(
    db: AsyncSession,
    expression: str,
    *,
    context_fields: list[str] | None = None,
    available_factors: list[str] | None = None,
) -> dict[str, Any]:
    fields = set(context_fields) if context_fields else set(OHLCV_FIELDS)
    factors = set(available_factors) if available_factors else await _known_factor_names(db)
    # 排除内置 OHLCV 因子（避免双重计入）
    factors -= fields

    try:
        cexpr = compile_expression(
            expression,
            ohlcv_fields=fields,
            known_factors=factors,
            param_names=set(),
        )
    except EngineError as e:
        return {
            "valid": False,
            "depends_on_fields": [],
            "depends_on_factors": [],
            "max_history_window": 0,
            "warnings": [],
            "error_code": e.error_code,
            "error_message": e.message,
        }

    return {
        "valid": True,
        "depends_on_fields": sorted(cexpr.info.depends_on_fields),
        "depends_on_factors": sorted(cexpr.info.depends_on_factors),
        "max_history_window": cexpr.info.max_history_window,
        "warnings": list(cexpr.info.warnings),
        "error_code": None,
        "error_message": None,
    }

