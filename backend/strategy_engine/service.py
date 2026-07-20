"""strategy_engine 业务编排层。

变更说明（strategy-engine-params-redesign）：
- 新增 StrategyService.validate_param_values()（strategy-param-schema spec）
- 新增 RuntimeConfigService（runtime-config-template spec）
- dry_run() 签名变更：template_id + override 替代硬编码 stock_code/date
- load_strategy() 注入 RuntimeConfig（TODO：待 account_trading 事件总线就绪后完善）
"""

from __future__ import annotations

import os
import re
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from strategy_engine.exceptions import (
    DryRunError,
    InvalidParamValue,
    InvalidStrategyError,
    InvalidOverrideField,
    RuntimeConfigDateInvalid,
    RuntimeConfigDateRequired,
    RuntimeConfigDefaultForbidden,
    RuntimeConfigNotFound,
    RuntimeConfigNameDuplicated,
    StrategyNotActive,
    StrategyNotFound,
)
from strategy_engine.models import Strategy, RuntimeConfigTemplate
from strategy_engine.repository import (
    RuntimeConfigRepository,
    StrategyRepository,
    StrategyVersionRepository,
)
from strategy_engine.runtime.engine import BacktestEngine
from strategy_engine.runtime.mock_data import (
    MockAccountFetcher,
    MockBenchmarkFetcher,
    MockKLineFetcher,
)
from strategy_engine.runtime.real_data import (
    RealAccountFetcher,
    RealKLineFetcher,
)
from strategy_engine.runtime.types import BacktestResult
from strategy_engine.schemas import (
    DataFrequency,
    DryRunRequest,
    DryRunResponse,
    ParamFieldType,
    ParamSchema,
    RuntimeConfigTemplateCreate,
    RuntimeConfigTemplateUpdate,
)


# ============================================================
# 参数值校验（strategy-param-schema spec）
# ============================================================

STOCK_CODE_PATTERN = re.compile(r"^\d{6}\.(SZ|SH|BJ)$")


class StrategyService:
    """策略相关业务逻辑。"""

    @staticmethod
    def validate_param_values(
        schema: ParamSchema,
        values: dict[str, Any],
    ) -> None:
        """基于 Schema 校验参数值，失败抛 InvalidParamValue。

        规则：
        - 必填字段（required=True）不允许缺失
        - int 字段值必须为整数
        - float 字段值必须为数值
        - min/max 范围校验
        - select 字段值必须在 options.value 列表中
        - list 字段值必须为数组，元素类型匹配 item_type
        - stock_code 字段值必须匹配 ^\\d{6}\\.(SZ|SH|BJ)$
        - 允许 values 含 Schema 未声明的额外字段（向前兼容）
        """
        field_map: dict[str, Any] = {f.key: f for f in schema.fields}

        # 1. 必填检查
        for field in schema.fields:
            if field.required and field.key not in values:
                raise InvalidParamValue(f"参数 {field.key} 必填")

        # 2. 类型与范围检查
        for key, value in values.items():
            field = field_map.get(key)
            if not field:
                # 允许额外字段（向前兼容）
                continue

            # int
            if field.type == ParamFieldType.INT:
                if not isinstance(value, int) or isinstance(value, bool):
                    raise InvalidParamValue(f"参数 {key} 必须为整数")

            # float
            if field.type == ParamFieldType.FLOAT:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    raise InvalidParamValue(f"参数 {key} 必须为数值")

            # 数值范围
            if field.type in (ParamFieldType.INT, ParamFieldType.FLOAT):
                if field.min is not None and float(value) < field.min:
                    raise InvalidParamValue(f"参数 {key} 小于最小值 {field.min}")
                if field.max is not None and float(value) > field.max:
                    raise InvalidParamValue(f"参数 {key} 大于最大值 {field.max}")

            # select
            if field.type == ParamFieldType.SELECT:
                valid_values = [opt.get("value") for opt in (field.options or [])]
                if value not in valid_values:
                    raise InvalidParamValue(f"参数 {key} 不在允许选项中")

            # stock_code
            if field.type == ParamFieldType.STOCK_CODE:
                if not isinstance(value, str) or not STOCK_CODE_PATTERN.match(value):
                    raise InvalidParamValue(
                        f"参数 {key} 必须匹配 ^\\d{{6}}\\.(SZ|SH|BJ)$"
                    )

            # list
            if field.type == ParamFieldType.LIST:
                if not isinstance(value, list):
                    raise InvalidParamValue(f"参数 {key} 必须为数组")
                item_type = field.item_type
                for i, item in enumerate(value):
                    if item_type == ParamFieldType.STOCK_CODE:
                        if not isinstance(item, str) or not STOCK_CODE_PATTERN.match(item):
                            raise InvalidParamValue(
                                f"参数 {key} 第 {i+1} 项格式错误"
                            )
                    elif item_type == ParamFieldType.INT:
                        if not isinstance(item, int) or isinstance(item, bool):
                            raise InvalidParamValue(
                                f"参数 {key} 第 {i+1} 项必须为整数"
                            )
                    elif item_type == ParamFieldType.FLOAT:
                        if not isinstance(item, (int, float)) or isinstance(item, bool):
                            raise InvalidParamValue(
                                f"参数 {key} 第 {i+1} 项必须为数值"
                            )


# ============================================================
# RuntimeConfigService（runtime-config-template spec）
# ============================================================

# 允许覆盖的字段白名单
OVERRIDE_ALLOWED_FIELDS = frozenset({
    "universe",
    "start_date",
    "end_date",
    "initial_capital",
    "frequency",
    "slippage",
    "commission",
})


class RuntimeConfigService:
    """运行配置模板业务逻辑。"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = RuntimeConfigRepository(session)

    async def list_templates(
        self,
        mode: str | None = None,
    ) -> list[RuntimeConfigTemplate]:
        return await self.repo.list_all(mode=mode)

    async def get_template(self, template_id: int) -> RuntimeConfigTemplate:
        template = await self.repo.get_by_id(template_id)
        if not template:
            raise RuntimeConfigNotFound(f"运行配置模板 {template_id} 不存在")
        return template

    async def create_template(
        self,
        data: RuntimeConfigTemplateCreate,
    ) -> RuntimeConfigTemplate:
        # 名称唯一性
        existing = await self.repo.get_by_name(data.name)
        if existing:
            raise RuntimeConfigNameDuplicated(f"模板名称 {data.name} 已存在")

        return await self.repo.create(data.model_dump())

    async def update_template(
        self,
        template_id: int,
        data: RuntimeConfigTemplateUpdate,
    ) -> RuntimeConfigTemplate:
        # 系统预设禁止修改
        template = await self.get_template(template_id)
        if template.is_default:
            raise RuntimeConfigDefaultForbidden("系统预设模板不可修改")

        # 名称唯一性（排除自己）
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            existing = await self.repo.get_by_name(update_data["name"])
            if existing and existing.id != template_id:
                raise RuntimeConfigNameDuplicated(
                    f"模板名称 {update_data['name']} 已存在"
                )

        return await self.repo.update(template_id, update_data)

    async def delete_template(self, template_id: int) -> None:
        """删除模板，系统预设禁止。"""
        template = await self.get_template(template_id)
        if template.is_default:
            raise RuntimeConfigDefaultForbidden("系统预设模板不可删除")
        await self.repo.delete(template_id)

    def resolve_config(
        self,
        template: RuntimeConfigTemplate,
        override: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """合并模板与临时覆盖，返回运行时配置 dict。

        规则：
        - override 仅允许 OVERRIDE_ALLOWED_FIELDS 中的字段
        - 合并后重新校验 backtest 日期约束
        """
        # 构建基础配置
        config: dict[str, Any] = {
            "mode": template.mode,
            "universe": list(template.universe) if template.universe else [],
            "start_date": str(template.start_date) if template.start_date else None,
            "end_date": str(template.end_date) if template.end_date else None,
            "initial_capital": float(template.initial_capital),
            "frequency": template.frequency,
            "timeframe": _freq_to_timeframe(template.frequency),  # 引擎使用 '1d' 格式
            "slippage": float(template.slippage),
            "commission": float(template.commission),
        }

        if not override:
            # 合并后仍需校验
            self._validate_backtest_dates(config)
            return config

        # 字段白名单检查
        for key in override:
            if key not in OVERRIDE_ALLOWED_FIELDS:
                raise InvalidOverrideField(f"覆盖字段 {key} 不允许")

        # 合并
        for key, value in override.items():
            if value is not None:
                config[key] = value
                # 覆盖 frequency 时同步更新 engine 期望的 timeframe 格式
                if key == "frequency":
                    config["timeframe"] = _freq_to_timeframe(value)

        # 合并后校验
        self._validate_backtest_dates(config)
        return config

    def _validate_backtest_dates(self, config: dict[str, Any]) -> None:
        if config.get("mode") == "backtest":
            start = config.get("start_date")
            end = config.get("end_date")
            if not start or not end:
                raise RuntimeConfigDateRequired(
                    "backtest 模式必须提供 start_date/end_date"
                )
            if start >= end:
                raise RuntimeConfigDateInvalid("start_date 必须早于 end_date")


# ============================================================
# 辅助函数
# ============================================================

def _freq_to_timeframe(freq: str) -> str:
    """将 frequency 字符串映射为 engine 期望的 timeframe 格式。引擎目前仅支持 '1d'。"""
    mapping = {
        "daily": "1d",
        "1min": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "60min": "60m",
    }
    return mapping.get(freq, "1d")


# ============================================================
# dry-run 入口（签名变更）
# ============================================================

async def dry_run(
    db: AsyncSession,
    strategy_id: int,
    payload: DryRunRequest,
) -> DryRunResponse:
    """基于 mock 数据的试运行（signature 变更后）。

    业务流程：
      1. 查 DB 拿策略（不存在 → 404；status != active → 400）
      2. 加载 RuntimeConfigTemplate 并合并 override
      3. 可选校验 param_schema 与 parameters
      4. 用 mock fetchers 构造 BacktestEngine
      5. 调 engine.run，限定 max_bars
      6. 可选保存 runtime_config_snapshot 到最新版本

    Args:
        db: 异步 DB 会话
        strategy_id: 策略 ID
        payload: DryRunRequest（template_id + override + max_bars + parameters + save_snapshot）

    Returns:
        DryRunResponse

    Raises:
        StrategyNotFound
        StrategyNotActive
        RuntimeConfigNotFound
        InvalidParamValue
        DryRunError
    """
    # 1. 查策略
    strategy_repo = StrategyRepository(db)
    strategy: Optional[Strategy] = await strategy_repo.get_by_id(strategy_id)
    if not strategy:
        raise StrategyNotFound(f"策略 {strategy_id} 不存在")
    if strategy.status != "active":
        raise StrategyNotActive(
            f"策略 {strategy_id} 状态非 active，当前 status={strategy.status}"
        )
    if not strategy.code_content:
        raise InvalidStrategyError("策略代码为空，无法试运行")

    # 2. 加载并合并运行配置
    config_svc = RuntimeConfigService(db)
    template = await config_svc.get_template(payload.template_id)
    runtime_config = config_svc.resolve_config(template, payload.override)

    # 3. 校验参数（如果策略有 Schema）
    strategy_params = strategy.parameters or {}
    if payload.parameters:
        strategy_params = dict(strategy_params)
        strategy_params.update(payload.parameters)

    if strategy.param_schema:
        schema = ParamSchema.model_validate(strategy.param_schema)
        StrategyService.validate_param_values(schema, strategy_params)

    # 4. 用 mock fetchers 构造引擎
    engine = BacktestEngine(
        kline_fetcher=MockKLineFetcher(max_bars=payload.max_bars),
        benchmark_fetcher=MockBenchmarkFetcher(),
        account_fetcher=MockAccountFetcher(),
    )

    # 5. 构造临时 strategy-like 对象（避免修改 ORM 实例）
    class _Tmp:
        pass
    tmp = _Tmp()
    tmp.id = strategy.id
    tmp.name = strategy.name
    tmp.status = strategy.status
    tmp.code_content = strategy.code_content
    tmp.parameters = strategy_params

    # 6. 执行（universe 取 runtime_config）
    stock_codes = runtime_config.get("universe", [])
    primary_stock = stock_codes[0] if stock_codes else "000001.SZ"

    try:
        result: BacktestResult = await engine.run(
            strategy=tmp,
            stock_code=primary_stock,
            account_id=0,  # mock 账户
            timeframe=runtime_config.get("timeframe", "1d"),
            start_date=str(runtime_config.get("start_date") or ""),
            end_date=str(runtime_config.get("end_date") or ""),
            session_id=f"dryrun_{strategy_id}_{primary_stock}",
        )
    except Exception as e:
        raise DryRunError(f"试运行失败：{e}") from e

    # 7. 可选保存运行配置快照
    if payload.save_snapshot:
        version_repo = StrategyVersionRepository(db)
        latest_version = await version_repo.get_latest(strategy_id)
        if latest_version:
            snapshot = {
                "template_id": payload.template_id,
                "override": payload.override,
                "runtime_config": runtime_config,
            }
            await version_repo.update_snapshot(latest_version.id, snapshot)

    return _to_dry_run_response(result)


def _to_dry_run_response(result: BacktestResult) -> DryRunResponse:
    """BacktestResult → DryRunResponse"""
    from strategy_engine.schemas import DryRunBarSummary

    initial = result.bars[0].total_assets if result.bars else 0.0
    final = result.bars[-1].total_assets if result.bars else 0.0
    if initial > 0:
        return_pct = round((final / initial - 1.0) * 100, 2)
    else:
        return_pct = 0.0

    bars_summary = [
        DryRunBarSummary(
            time=b.time,
            close=b.close,
            total_assets=b.total_assets,
            signal=b.signal,
            orders_count=len(b.orders),
        )
        for b in result.bars
    ]

    return DryRunResponse(
        session_id=result.session_id,
        total_bars=result.total_bars,
        time_elapsed=result.time_elapsed,
        final_capital=final,
        total_return_pct=return_pct,
        bars=bars_summary,
    )


# ============================================================
# 真实回测入口（保持不变，与 P3 change 无冲突）
# ============================================================

async def run_backtest(
    db: AsyncSession,
    stock_code: str,
    strategy_id: int,
    account_id: int,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> BacktestResult:
    """真实回测入口（与 history_replay 期望对齐）。"""
    repo = StrategyRepository(db)
    strategy: Optional[Strategy] = await repo.get_by_id(strategy_id)
    if not strategy:
        raise StrategyNotFound(f"策略 {strategy_id} 不存在")
    if strategy.status != "active":
        raise StrategyNotActive(
            f"策略 {strategy_id} 状态非 active，当前 status={strategy.status}"
        )
    if not strategy.code_content:
        raise InvalidStrategyError("策略代码为空，无法回测")

    use_real_data = os.environ.get("USE_REAL_DATA", "false").lower() in ("true", "1", "yes")

    if use_real_data:
        kline_fetcher = RealKLineFetcher(db)
        account_fetcher = RealAccountFetcher(db)
    else:
        kline_fetcher = MockKLineFetcher(max_bars=250)
        account_fetcher = MockAccountFetcher()

    engine = BacktestEngine(
        kline_fetcher=kline_fetcher,
        benchmark_fetcher=MockBenchmarkFetcher(),
        account_fetcher=account_fetcher,
    )

    return await engine.run(
        strategy=strategy,
        stock_code=stock_code,
        account_id=account_id,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        session_id=f"backtest_{strategy_id}_{stock_code}",
    )


# ============================================================
# 实盘对接：load_strategy（保持不变，RuntimeConfig 注入 TODO）
# ============================================================

async def load_strategy(
    db: AsyncSession,
    strategy_id: int,
) -> "StrategyInstance":
    """加载策略实例。

    TODO（strategy-engine-params-redesign change）：
    - 当前仅拉取策略代码和参数
    - RuntimeConfig 注入（从策略的 account_id 拉取账户快照）待 account_trading 事件总线就绪后完善
    """
    from strategy_engine.runtime.registry import get_global_registry
    from strategy_engine.runtime.loader import StrategyLoader, StrategyInstance

    registry = get_global_registry()

    async def loader_func(sid: int) -> StrategyInstance:
        repo = StrategyRepository(db)
        strategy = await repo.get_by_id(sid)

        if not strategy:
            raise StrategyNotFound(f"策略 {sid} 不存在")
        if strategy.status != "active":
            raise StrategyNotActive(f"策略 {sid} 未启用（status={strategy.status}）")
        if not strategy.code_content:
            raise InvalidStrategyError(f"策略 {sid} 代码为空")

        loader = StrategyLoader()
        instance = loader.load(
            code_content=strategy.code_content,
            parameters=strategy.parameters or {},
        )
        return instance

    instance = await registry.get(strategy_id, loader_func)
    if instance is None:
        raise StrategyNotFound(f"策略 {strategy_id} 加载失败")
    return instance


# ============================================================
# P3: 并发回测（保持不变）
# ============================================================

async def batch_backtest(
    db: AsyncSession,
    strategy_ids: list[int],
    stock_code: str,
    start_date: str,
    end_date: str,
    timeframe: str = "1d",
) -> list[BacktestResult]:
    """并发执行多个策略回测。"""
    if len(strategy_ids) > 10:
        raise InvalidStrategyError("并发回测最多支持 10 个策略")

    import asyncio

    async def _run_one(sid: int) -> BacktestResult:
        return await run_backtest(
            db=db,
            stock_code=stock_code,
            strategy_id=sid,
            account_id=0,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

    tasks = [_run_one(sid) for sid in strategy_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output: list[BacktestResult] = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            from strategy_engine.runtime.types import BacktestResult as BR

            output.append(BR(
                session_id=f"error_{strategy_ids[i]}",
                stock_code=stock_code,
                strategy_id=strategy_ids[i],
                strategy_name=f"error: {r}",
                account_id=0,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date,
                total_bars=0,
                time_elapsed=0.0,
                bars=[],
            ))
        else:
            output.append(r)

    return output


__all__ = [
    "batch_backtest",
    "dry_run",
    "load_strategy",
    "run_backtest",
    "StrategyService",
    "RuntimeConfigService",
]
