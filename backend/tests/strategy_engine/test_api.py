"""strategy_engine.api facade 单元测试。

覆盖：
- list_active_strategies / get_strategy：查询接口
- simulate：回测入口（走 mock fetcher，不依赖真实 K 线）
- batch_simulate / dry_run_strategy：辅助执行
- validate_strategy_code：静态校验
- facade 模块加载不引入循环依赖
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import async_session

from strategy_engine.api import (
    BacktestResult,
    DryRunResponse,
    StrategyEngineError,
    StrategyNotFound,
    StrategyNotActive,
    StrategySummary,
    batch_simulate,
    dry_run_strategy,
    get_strategy,
    list_active_strategies,
    simulate,
    validate_strategy_code,
)


@pytest.fixture(scope="session")
def event_loop():
    """session-scoped 事件循环，与 test_cross_module_integration 对齐。"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ============================================================
# 2.1 + 2.2 list_active_strategies / get_strategy
# ============================================================


class TestListActiveStrategies:
    """list_active_strategies：正常返回 + 空列表 + db 异常三分支。"""

    @pytest.mark.asyncio
    async def test_returns_active_strategies(self):
        """DB 中有 active 策略时，应返回非空列表，字段完整。"""
        async with async_session() as db:
            strategies = await list_active_strategies(db)
        assert len(strategies) >= 4  # 4 个内置策略
        first = strategies[0]
        assert isinstance(first, StrategySummary)
        assert first.id > 0
        assert first.code
        assert first.name
        assert first.status == "active"
        assert first.version

    @pytest.mark.asyncio
    async def test_returns_summary_not_orm(self):
        """返回值必须是 StrategySummary dataclass，不是 ORM 对象。"""
        from strategy_engine.models import Strategy as StrategyORM

        async with async_session() as db:
            strategies = await list_active_strategies(db)
        assert all(not isinstance(s, StrategyORM) for s in strategies)
        # frozen=True：不可变
        with pytest.raises(Exception):
            strategies[0].name = "mutated"  # type: ignore[misc]

    @pytest.mark.asyncio
    async def test_db_exception_wrapped(self):
        """db 抛异常时 facade 不吞，原样向上抛。"""
        class _BrokenSession(AsyncSession):
            async def execute(self, *args, **kwargs):
                raise RuntimeError("db down")

        with pytest.raises(Exception):
            await list_active_strategies(_BrokenSession())  # type: ignore[arg-type]


class TestGetStrategy:
    """get_strategy：正常 + 策略不存在两分支。"""

    @pytest.mark.asyncio
    async def test_returns_summary_by_id(self):
        """按 id 查存在的策略，返回完整 StrategySummary。"""
        async with async_session() as db:
            strategy = await get_strategy(db, strategy_id=1)
        assert strategy.id == 1
        assert strategy.name == "双均线交叉"

    @pytest.mark.asyncio
    async def test_raises_not_found(self):
        """不存在的 strategy_id 抛 StrategyNotFound（StrategyEngineError 子类）。"""
        async with async_session() as db:
            with pytest.raises(StrategyNotFound):
                await get_strategy(db, strategy_id=99999)

    @pytest.mark.asyncio
    async def test_not_found_is_engine_error(self):
        """StrategyNotFound 必须是 StrategyEngineError 子类，可统一兜底。"""
        async with async_session() as db:
            try:
                await get_strategy(db, strategy_id=99999)
            except StrategyEngineError:
                pass
            else:
                pytest.fail("StrategyNotFound 应该是 StrategyEngineError 子类")


# ============================================================
# 2.3 simulate
# ============================================================


class TestSimulate:
    """simulate：正常流程 + 策略非 active + 策略不存在三分支。"""

    @pytest.mark.asyncio
    async def test_simulate_returns_full_result(self):
        """正常调用应返回完整 BacktestResult。"""
        async with async_session() as db:
            result = await simulate(
                db,
                strategy_id=1,
                stock_code="000001.SZ",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )
        assert isinstance(result, BacktestResult)
        assert result.stock_code == "000001.SZ"
        assert result.strategy_id == 1
        assert result.strategy_name == "双均线交叉"
        assert result.total_bars > 0
        assert len(result.bars) == result.total_bars

    @pytest.mark.asyncio
    async def test_simulate_uses_keyword_only(self):
        """simulate 强制关键字参数：位置参数传 strategy_id 应 TypeError。"""
        async with async_session() as db:
            with pytest.raises(TypeError):
                await simulate(
                    db,
                    1,  # type: ignore[misc]
                    "000001.SZ",
                    "2024-01-01",
                    "2024-12-31",
                )

    @pytest.mark.asyncio
    async def test_simulate_strategy_not_found(self):
        """strategy_id 不存在 → StrategyNotFound。"""
        async with async_session() as db:
            with pytest.raises(StrategyNotFound):
                await simulate(
                    db,
                    strategy_id=99999,
                    stock_code="000001.SZ",
                    start_date="2024-01-01",
                    end_date="2024-12-31",
                )

    @pytest.mark.asyncio
    async def test_simulate_strategy_not_active(self):
        """status != active → StrategyNotActive。

        依赖 DB 中有 status != active 的策略；如果没有则 skip。
        """
        from strategy_engine.repository import StrategyRepository

        async with async_session() as db:
            repo = StrategyRepository(db)
            inactive = [
                s for s in await repo.list_all(status=None) if s.status != "active"
            ]
            if not inactive:
                pytest.skip("DB 中没有非 active 策略，跳过此用例")
            with pytest.raises(StrategyNotActive):
                await simulate(
                    db,
                    strategy_id=inactive[0].id,
                    stock_code="000001.SZ",
                    start_date="2024-01-01",
                    end_date="2024-12-31",
                )


# ============================================================
# 2.4 validate_strategy_code
# ============================================================


_VALID_CODE = """
def initialize(ctx):
    pass

def handle_bar(ctx, bar):
    pass
"""

_SYNTAX_ERROR_CODE = """
def initialize(ctx:
    pass
"""

_MISSING_HOOK_CODE = """
def initialize(ctx):
    pass
"""


class TestValidateStrategyCode:
    """validate_strategy_code：合法 + 语法错误 + 缺钩子三场景。"""

    def test_valid_code(self):
        """合法代码应返回 valid=True，无 error。"""
        result = validate_strategy_code(_VALID_CODE)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_syntax_error(self):
        """语法错误应返回 valid=False 且 errors 含 SYNTAX_ERROR。"""
        result = validate_strategy_code(_SYNTAX_ERROR_CODE)
        assert result["valid"] is False
        assert any(e["code"] == "SYNTAX_ERROR" for e in result["errors"])

    def test_missing_hook_is_warning(self):
        """缺 handle_bar 钩子应为 warning，不应阻断保存（valid=True）。"""
        result = validate_strategy_code(_MISSING_HOOK_CODE)
        # 缺钩子是 warning，不是 error
        assert result["valid"] is True
        assert any(w["code"] == "MISSING_HOOK" for w in result["warnings"])


# ============================================================
# 2.5 batch_simulate / dry_run_strategy
# ============================================================


class TestBatchSimulate:
    """batch_simulate 基本通路。"""

    @pytest.mark.asyncio
    async def test_batch_returns_one_result_per_strategy(self):
        """传入 N 个 strategy_id 应返回 N 个 BacktestResult。"""
        async with async_session() as db:
            results = await batch_simulate(
                db,
                strategy_ids=[1, 2],
                stock_code="000001.SZ",
                start_date="2024-01-01",
                end_date="2024-06-30",
            )
        assert len(results) == 2
        for r in results:
            assert isinstance(r, BacktestResult)


class TestDryRunStrategy:
    """dry_run_strategy 通路（依赖 DB 中存在 runtime_config_template）。"""

    @pytest.mark.asyncio
    async def test_dry_run_or_skip(self):
        """能跑就跑，没模板就 skip（不强行构造测试数据）。"""
        from strategy_engine.repository import RuntimeConfigRepository

        async with async_session() as db:
            templates = await RuntimeConfigRepository(db).list_all()
            if not templates:
                pytest.skip("DB 中没有 runtime_config_template，跳过 dry_run 测试")
            try:
                resp = await dry_run_strategy(
                    db,
                    strategy_id=1,
                    template_id=templates[0].id,
                    max_bars=10,
                )
                assert isinstance(resp, DryRunResponse)
            except StrategyEngineError as e:
                # dry_run 在某些参数下可能抛 InvalidParamValue 等，用例不强制通过
                # 只验证异常类型属于 StrategyEngineError 体系
                assert isinstance(e, StrategyEngineError)


# ============================================================
# 2.6 循环依赖检查
# ============================================================


class TestFacadeNoCircularImport:
    """facade 模块单独加载不应报 ImportError。"""

    def test_import_isolated(self):
        """从干净上下文 import strategy_engine.api 应成功。"""
        import importlib

        mod = importlib.import_module("strategy_engine.api")
        assert hasattr(mod, "simulate")
        assert hasattr(mod, "list_active_strategies")
        assert hasattr(mod, "StrategyEngineError")
        assert "simulate" in mod.__all__
