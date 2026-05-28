"""策略版本快照 service：发布、查询、求值适配。

发布流程（publish）核心步骤：
  1. 加载所有 factor_bindings 引用的 Factor，构造 alias->Factor 映射
  2. 编译 buy / sell 表达式（已知衍生因子 = bindings 中所有 alias）
  3. 生成 compiled_meta：
     - buy / sell 各自的 depends_on_fields / depends_on_factors / max_history_window
     - required_data：聚合 ohlcv / fundamental / account / crosssection
  4. version_no = max(version_no) + 1，写入 strategy_versions
  5. 更新 strategy.current_version_id, status='active'
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..engine.compiler import compile_expression
from ..engine.errors import StrategyVersionNotFound
from ..engine.evaluator import evaluate_strategy
from ..engine.factors.registry import BUILTIN_NAMES_OHLCV
from ..models import Factor, Strategy, StrategyVersion
from .strategy_service import get_strategy

OHLCV_FIELDS = set(BUILTIN_NAMES_OHLCV)


# ---------------------------------------------------------------------------
# required_data 聚合
# ---------------------------------------------------------------------------
def _empty_required_data() -> dict[str, Any]:
    return {
        "ohlcv": {"fields": [], "history_window": 0},
        "fundamental": {"fields": []},
        "account": {"fields": []},
        "crosssection": [],
    }


def _merge_into_required_data(
    required: dict[str, Any],
    factor: Factor,
    history_window: int,
) -> None:
    ds = factor.data_source or {}
    t = ds.get("type")

    if t == "ohlcv":
        field = ds.get("field") or factor.name
        symbol_ref = ds.get("symbol_ref")
        if symbol_ref:
            # 跨品种因子归到 crosssection
            existing = next(
                (
                    item
                    for item in required["crosssection"]
                    if item["symbol_ref"] == symbol_ref
                ),
                None,
            )
            if existing is None:
                required["crosssection"].append(
                    {
                        "symbol_ref": symbol_ref,
                        "fields": [field],
                        "history_window": history_window,
                    }
                )
            else:
                if field not in existing["fields"]:
                    existing["fields"].append(field)
                existing["history_window"] = max(
                    existing.get("history_window", 0), history_window
                )
        else:
            if field not in required["ohlcv"]["fields"]:
                required["ohlcv"]["fields"].append(field)
            required["ohlcv"]["history_window"] = max(
                required["ohlcv"]["history_window"], history_window
            )
    elif t == "fundamental":
        field = ds.get("field") or factor.name
        if field not in required["fundamental"]["fields"]:
            required["fundamental"]["fields"].append(field)
    elif t == "account":
        field = ds.get("field") or factor.name
        if field not in required["account"]["fields"]:
            required["account"]["fields"].append(field)
    elif t == "crosssection":
        symbol_ref = ds.get("symbol_ref", "")
        field = ds.get("field") or factor.name
        existing = next(
            (
                item
                for item in required["crosssection"]
                if item["symbol_ref"] == symbol_ref
            ),
            None,
        )
        if existing is None:
            required["crosssection"].append(
                {
                    "symbol_ref": symbol_ref,
                    "fields": [field],
                    "history_window": history_window,
                }
            )
        else:
            if field not in existing["fields"]:
                existing["fields"].append(field)
    elif t == "derived":
        # derived 因子的依赖叶子已在 _expand_to_leaves 中递归处理
        pass


async def _expand_to_leaves(
    db: AsyncSession,
    alias_to_factor: dict[str, Factor],
    history_window: int,
    required: dict[str, Any],
    visited: set[str] | None = None,
) -> None:
    """递归把衍生因子展开到叶子，并把叶子写入 required_data。"""
    visited = visited or set()
    for alias, factor in list(alias_to_factor.items()):
        if alias in visited:
            continue
        visited.add(alias)
        ds = factor.data_source or {}
        if ds.get("type") == "derived":
            # 找出依赖（按 name）的 Factor，递归
            deps = ds.get("depends_on") or []
            sub_map: dict[str, Factor] = {}
            for dep_name in deps:
                if dep_name in OHLCV_FIELDS:
                    # 直接当作 OHLCV 字段
                    if dep_name not in required["ohlcv"]["fields"]:
                        required["ohlcv"]["fields"].append(dep_name)
                    required["ohlcv"]["history_window"] = max(
                        required["ohlcv"]["history_window"], history_window
                    )
                    continue
                dep_factor = await db.scalar(
                    select(Factor).where(Factor.name == dep_name)
                )
                if dep_factor is not None:
                    sub_map[dep_name] = dep_factor
            await _expand_to_leaves(db, sub_map, history_window, required, visited)
        else:
            _merge_into_required_data(required, factor, history_window)


# ---------------------------------------------------------------------------
# 发布
# ---------------------------------------------------------------------------
async def publish_version(
    db: AsyncSession,
    strategy_id: int,
    payload: dict[str, Any],
) -> StrategyVersion:
    strategy = await get_strategy(db, strategy_id)

    factor_bindings: list[dict[str, Any]] = [
        b if isinstance(b, dict) else b.model_dump()
        for b in payload.get("factor_bindings") or []
    ]
    params_schema: list[dict[str, Any]] = [
        s if isinstance(s, dict) else s.model_dump()
        for s in payload.get("params_schema") or []
    ]
    params_default: dict[str, Any] = payload.get("params_default") or {}

    # 加载 binding 涉及的 Factor
    factor_ids = [b["factor_id"] for b in factor_bindings]
    factor_rows: list[Factor] = []
    if factor_ids:
        factor_rows = list(
            (await db.scalars(select(Factor).where(Factor.id.in_(factor_ids)))).all()
        )
    factor_by_id = {f.id: f for f in factor_rows}

    # alias -> Factor / expression
    alias_to_factor: dict[str, Factor] = {}
    factor_definitions: dict[str, dict[str, Any]] = {}
    known_factor_aliases: set[str] = set()
    for b in factor_bindings:
        f = factor_by_id.get(b["factor_id"])
        if not f:
            continue
        alias = b["alias"]
        alias_to_factor[alias] = f
        known_factor_aliases.add(alias)
        if f.category == "derived" and f.expression:
            factor_definitions[alias] = {
                "expression": f.expression,
                "depends_on_factors": (f.data_source or {}).get("depends_on", []),
            }

    param_names = {item["name"] for item in params_schema}

    # 编译 buy / sell
    buy_compiled = compile_expression(
        payload["buy_expression"],
        ohlcv_fields=OHLCV_FIELDS,
        known_factors=known_factor_aliases,
        param_names=param_names,
    )
    sell_compiled = compile_expression(
        payload["sell_expression"],
        ohlcv_fields=OHLCV_FIELDS,
        known_factors=known_factor_aliases,
        param_names=param_names,
    )

    # 可选：编译 position_expression
    position_expression: str | None = payload.get("position_expression")
    position_meta: dict[str, Any] | None = None
    if position_expression:
        pos_compiled = compile_expression(
            position_expression,
            ohlcv_fields=OHLCV_FIELDS,
            known_factors=known_factor_aliases,
            param_names=param_names,
        )
        position_meta = pos_compiled.to_meta()

    max_window = max(
        buy_compiled.info.max_history_window,
        sell_compiled.info.max_history_window,
    )

    # 聚合 required_data
    required = _empty_required_data()
    # 1. buy/sell 直接引用的 OHLCV 字段
    for f in buy_compiled.info.depends_on_fields | sell_compiled.info.depends_on_fields:
        if f not in required["ohlcv"]["fields"]:
            required["ohlcv"]["fields"].append(f)
    if (
        buy_compiled.info.depends_on_fields | sell_compiled.info.depends_on_fields
    ) and max_window > 0:
        required["ohlcv"]["history_window"] = max(
            required["ohlcv"]["history_window"], max_window
        )
    # 2. binding 的衍生因子递归展开
    await _expand_to_leaves(db, alias_to_factor, max_window, required)

    compiled_meta = {
        "buy": buy_compiled.to_meta(),
        "sell": sell_compiled.to_meta(),
        "position": position_meta,
        "required_data": required,
        "warnings": [],
    }

    # 计算下一个 version_no
    last_version_no = (
        await db.scalar(
            select(sa_func.max(StrategyVersion.version_no)).where(
                StrategyVersion.strategy_id == strategy_id
            )
        )
        or 0
    )
    next_version_no = int(last_version_no) + 1

    version = StrategyVersion(
        strategy_id=strategy_id,
        version_no=next_version_no,
        buy_expression=payload["buy_expression"],
        sell_expression=payload["sell_expression"],
        position_expression=position_expression,
        factor_bindings=factor_bindings,
        params_schema=params_schema,
        params_default=params_default,
        compiled_meta=compiled_meta,
    )
    db.add(version)
    await db.flush()

    strategy.current_version_id = version.id
    strategy.status = "active"
    await db.flush()
    return version


# ---------------------------------------------------------------------------
# 查询
# ---------------------------------------------------------------------------
async def list_versions(
    db: AsyncSession,
    strategy_id: int,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[StrategyVersion], int]:
    base = select(StrategyVersion).where(StrategyVersion.strategy_id == strategy_id)
    count = (
        await db.scalar(
            select(sa_func.count())
            .select_from(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
        )
        or 0
    )
    stmt = (
        base.order_by(StrategyVersion.version_no.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list((await db.scalars(stmt)).all())
    return items, int(count)


async def get_version(
    db: AsyncSession,
    strategy_id: int,
    version_no: int,
) -> StrategyVersion:
    v = await db.scalar(
        select(StrategyVersion).where(
            (StrategyVersion.strategy_id == strategy_id)
            & (StrategyVersion.version_no == version_no)
        )
    )
    if not v:
        raise StrategyVersionNotFound(
            f"版本不存在: strategy_id={strategy_id}, version_no={version_no}",
            detail={"strategy_id": strategy_id, "version_no": version_no},
        )
    return v


async def get_version_by_id(db: AsyncSession, version_id: int) -> StrategyVersion:
    v = await db.get(StrategyVersion, version_id)
    if not v:
        raise StrategyVersionNotFound(
            f"版本不存在: version_id={version_id}",
            detail={"version_id": version_id},
        )
    return v


# ---------------------------------------------------------------------------
# 求值
# ---------------------------------------------------------------------------
async def evaluate(
    db: AsyncSession,
    strategy_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    strategy = await get_strategy(db, strategy_id)
    version_id = payload.get("version_id") or strategy.current_version_id
    if version_id is None:
        raise StrategyVersionNotFound(
            f"策略尚未发布任何版本: strategy_id={strategy_id}",
            detail={"strategy_id": strategy_id},
        )
    version = await get_version_by_id(db, version_id)

    # 加载 binding 的 derived 因子定义（alias -> {expression, depends_on_factors}）
    factor_definitions: dict[str, dict[str, Any]] = {}
    bindings = version.factor_bindings or []
    factor_ids = [b["factor_id"] for b in bindings]
    if factor_ids:
        rows = list(
            (await db.scalars(select(Factor).where(Factor.id.in_(factor_ids)))).all()
        )
        by_id = {f.id: f for f in rows}
        for b in bindings:
            f = by_id.get(b["factor_id"])
            if f and f.category == "derived" and f.expression:
                factor_definitions[b["alias"]] = {
                    "expression": f.expression,
                    "depends_on_factors": (f.data_source or {}).get("depends_on", []),
                }

    snapshot = {
        "buy_expression": version.buy_expression,
        "sell_expression": version.sell_expression,
        "position_expression": version.position_expression,
        "factor_bindings": bindings,
        "params_schema": version.params_schema,
        "params_default": version.params_default,
        "compiled_meta": version.compiled_meta,
    }

    result = evaluate_strategy(
        snapshot,
        context=payload["context"],
        params=payload.get("params") or {},
        factor_definitions=factor_definitions,
        debug=bool(payload.get("debug")),
    )
    result.update(
        {
            "strategy_id": strategy_id,
            "version_id": version.id,
            "version_no": version.version_no,
        }
    )
    return result
