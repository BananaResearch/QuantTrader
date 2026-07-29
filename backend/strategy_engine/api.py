"""strategy_engine 对外契约（facade）。

其他业务模块（history_replay / review_analysis / strategy_execution 等）
**必须**从本模块 import strategy_engine 的能力，**禁止**直接 import
`strategy_engine.repository` / `strategy_engine.service` / `strategy_engine.runtime`。

## 唯一入口契约

- 本文件是 strategy_engine 对其他模块的稳定接口边界
- 函数签名长期向后兼容；内部分层（repository/service/runtime）的重构不影响调用方
- 新增对外能力时，MUST 在本文件新增函数 + 在 `__all__` 导出 + 更新映射表

## facade 函数 ↔ 内部分层 映射

| facade 函数 | 内部委托目标 | 用途 |
| --- | --- | --- |
| `list_active_strategies(db)` | `StrategyRepository(db).list_options(status="active")` | 查询 active 策略列表 |
| `get_strategy(db, strategy_id)` | `StrategyRepository(db).get_by_id(...)` | 查询单个策略 |
| `simulate(db, *, ...)` | `strategy_engine.service.run_backtest` | 跑策略回测（不落库） |
| `batch_simulate(db, *, ...)` | `strategy_engine.service.batch_backtest` | 并发跑多策略 |
| `dry_run_strategy(db, *, ...)` | `strategy_engine.service.dry_run` | 试运行（mock 数据） |
| `validate_strategy_code(code_content)` | `strategy_engine.runtime.loader.validate_code` | 静态校验策略代码 |

## 数据契约

- `BacktestResult` / `BarRecord` / `OrderRecord` / `PositionRecord` 源自
  `runtime/types.py`，facade re-export；消费方不得本地重新定义
- `StrategySummary` 是 facade 内定义的 frozen dataclass，不暴露 ORM 对象

## 异常契约

所有 facade 抛出的异常都继承 `strategy_engine.exceptions.BacktestError`，
在 facade 中 alias 为 `StrategyEngineError`。消费方可用单条
`except StrategyEngineError` 兜底。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

# ============================================================
# 段 1：类型 / 异常 / Schema re-export（跨模块契约）
# ============================================================

from strategy_engine.exceptions import (
    BacktestError as StrategyEngineError,
    DataUnavailableError,
    DryRunError,
    InvalidParamValue,
    InvalidStrategyError,
    StrategyLoadError,
    StrategyNotActive,
    StrategyNotFound,
    StrategyRuntimeError,
    StrategyTimeoutError,
)
from strategy_engine.runtime.types import (
    BacktestResult,
    BarRecord,
    OrderRecord,
    PositionRecord,
)
from strategy_engine.schemas import DryRunResponse


# ============================================================
# 段 2：对外 dataclass（不暴露 ORM）
# ============================================================


@dataclass(frozen=True)
class StrategySummary:
    """策略摘要（对外暴露，不含 code_content 等大字段）。

    frozen=True 保证不可变；字段命名与 strategy 表对齐，但独立演化。
    """

    id: int
    code: str
    name: str
    description: str
    status: str
    version: str


# ============================================================
# 段 3：策略查询
# ============================================================


async def list_active_strategies(db: AsyncSession) -> list[StrategySummary]:
    """查询所有 status='active' 的策略，按 id 升序返回。

    Args:
        db: 异步 DB 会话

    Returns:
        list[StrategySummary]；DB 中无 active 策略时返回空列表

    Raises:
        StrategyEngineError: DB 访问异常
    """
    from strategy_engine.repository import StrategyRepository

    repo = StrategyRepository(db)
    strategies = await repo.list_options(status="active")
    return [
        StrategySummary(
            id=s.id,
            code=s.code,
            name=s.name,
            description=s.description or "",
            status=s.status,
            version=s.version,
        )
        for s in strategies
    ]


async def get_strategy(db: AsyncSession, strategy_id: int) -> StrategySummary:
    """查询单个策略。

    Args:
        db: 异步 DB 会话
        strategy_id: 策略主键

    Returns:
        StrategySummary

    Raises:
        StrategyNotFound: strategy_id 在 DB 中不存在
    """
    from strategy_engine.repository import StrategyRepository

    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if strategy is None:
        raise StrategyNotFound(f"策略 {strategy_id} 不存在")
    return StrategySummary(
        id=strategy.id,
        code=strategy.code,
        name=strategy.name,
        description=strategy.description or "",
        status=strategy.status,
        version=strategy.version,
    )


# ============================================================
# 段 4：策略执行 + 校验
# ============================================================


async def simulate(
    db: AsyncSession,
    *,
    strategy_id: int,
    stock_code: str,
    start_date: str,
    end_date: str,
    account_id: int = 0,
    timeframe: str = "1d",
) -> BacktestResult:
    """跑策略回测（不落库）。

    Args:
        db: 异步 DB 会话
        strategy_id: 策略主键
        stock_code: 标的代码，如 "000001.SZ"
        start_date: 起始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD
        account_id: 账户 ID，默认 0（mock 账户）
        timeframe: K 线周期，默认 "1d"（P1 阶段仅支持 1d）

    Returns:
        BacktestResult（含逐 bar 明细）

    Raises:
        StrategyNotFound: 策略不存在
        StrategyNotActive: 策略状态非 active
        InvalidStrategyError: 策略代码为空
        BacktestError: 其他通用错误
    """
    from strategy_engine.service import run_backtest

    return await run_backtest(
        db=db,
        stock_code=stock_code,
        strategy_id=strategy_id,
        account_id=account_id,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
    )


async def batch_simulate(
    db: AsyncSession,
    *,
    strategy_ids: list[int],
    stock_code: str,
    start_date: str,
    end_date: str,
    timeframe: str = "1d",
) -> list[BacktestResult]:
    """并发跑多个策略的回测。

    Args:
        db: 异步 DB 会话
        strategy_ids: 策略 ID 列表，最多 10 个
        stock_code: 标的代码
        start_date: 起始日期
        end_date: 结束日期
        timeframe: K 线周期，默认 "1d"

    Returns:
        list[BacktestResult]，顺序与 strategy_ids 对齐；
        单个策略失败时对应位置返回错误占位 BacktestResult（不中断其他）

    Raises:
        InvalidStrategyError: strategy_ids 长度 > 10
    """
    from strategy_engine.service import batch_backtest

    return await batch_backtest(
        db=db,
        strategy_ids=strategy_ids,
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        timeframe=timeframe,
    )


async def dry_run_strategy(
    db: AsyncSession,
    *,
    strategy_id: int,
    template_id: int,
    override: dict[str, Any] | None = None,
    max_bars: int = 60,
    parameters: dict[str, Any] | None = None,
    save_snapshot: bool = False,
) -> DryRunResponse:
    """试运行（基于 mock 数据的短回测）。

    Args:
        db: 异步 DB 会话
        strategy_id: 策略 ID
        template_id: 运行配置模板 ID
        override: 临时覆盖字段（仅允许 universe/start_date/end_date/initial_capital/
                  frequency/slippage/commission）
        max_bars: 最大 bar 数，默认 60，范围 1-1000
        parameters: 临时覆盖策略参数值
        save_snapshot: 是否保存运行配置快照到最新版本

    Returns:
        DryRunResponse

    Raises:
        StrategyNotFound: 策略不存在
        StrategyNotActive: 策略状态非 active
        InvalidStrategyError: 策略代码为空
        RuntimeConfigNotFound: template_id 不存在
        InvalidOverrideField: override 字段不在白名单
        InvalidParamValue: 参数与 Schema 不匹配
        DryRunError: 试运行执行失败
    """
    from strategy_engine.schemas import DryRunRequest
    from strategy_engine.service import dry_run

    payload = DryRunRequest(
        template_id=template_id,
        override=override,
        max_bars=max_bars,
        parameters=parameters,
        save_snapshot=save_snapshot,
    )
    return await dry_run(db=db, strategy_id=strategy_id, payload=payload)


def validate_strategy_code(code_content: str) -> dict[str, Any]:
    """静态校验策略代码（语法 + 沙箱可加载性）。

    同步函数，不涉及 DB。

    Args:
        code_content: Python 源码字符串

    Returns:
        {"valid": bool, "errors": [...], "warnings": [...]}
    """
    from strategy_engine.runtime.loader import validate_code

    return validate_code(code_content)


__all__ = [
    # 类型契约
    "BacktestResult",
    "BarRecord",
    "OrderRecord",
    "PositionRecord",
    "StrategySummary",
    "DryRunResponse",
    # 异常体系
    "StrategyEngineError",
    "StrategyNotFound",
    "StrategyNotActive",
    "InvalidStrategyError",
    "StrategyLoadError",
    "DataUnavailableError",
    "StrategyRuntimeError",
    "StrategyTimeoutError",
    "InvalidParamValue",
    "DryRunError",
    # 策略查询
    "list_active_strategies",
    "get_strategy",
    # 策略执行
    "simulate",
    "batch_simulate",
    "dry_run_strategy",
    # 校验
    "validate_strategy_code",
]
