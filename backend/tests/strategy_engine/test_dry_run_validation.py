"""dry-run 输入校验测试（BUG-STR-005 频率白名单 / BUG-STR-009 同日日期）。

聚焦 RuntimeConfigService.resolve_config 的校验逻辑，避免依赖 DB。
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from strategy_engine.exceptions import (
    InvalidOverrideField,
    RuntimeConfigDateInvalid,
)
from strategy_engine.models import RuntimeConfigTemplate
from strategy_engine.schemas import RuntimeMode
from strategy_engine.service import RuntimeConfigService


def _make_template(
    mode: RuntimeMode = RuntimeMode.BACKTEST,
    start_date: str = "2024-01-01",
    end_date: str = "2024-06-30",
    frequency: str = "daily",
) -> RuntimeConfigTemplate:
    """构造内存中的 RuntimeConfigTemplate（不走 DB）。"""
    return RuntimeConfigTemplate(
        id=1,
        name="test-template",
        description=None,
        mode=mode.value,
        universe=["000001.SZ"],
        start_date=start_date,
        end_date=end_date,
        initial_capital=Decimal("1000000"),
        frequency=frequency,
        slippage=Decimal("0.0003"),
        commission=Decimal("0.0001"),
        is_default=False,
    )


class TestFrequencyValidation:
    """BUG-STR-005：dry-run 仅支持 daily 频率。"""

    @pytest.mark.asyncio
    async def test_dry_run_rejects_5m_frequency(self):
        """override frequency=5m → 抛 InvalidOverrideField"""
        svc = RuntimeConfigService(session=None)  # resolve_config 不使用 session
        template = _make_template()
        with pytest.raises(InvalidOverrideField) as exc_info:
            svc.resolve_config(template, {"frequency": "5m"})
        assert "daily" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_dry_run_rejects_1h_frequency(self):
        """override frequency=1h → 抛 InvalidOverrideField"""
        svc = RuntimeConfigService(session=None)
        template = _make_template()
        with pytest.raises(InvalidOverrideField):
            svc.resolve_config(template, {"frequency": "1h"})

    @pytest.mark.asyncio
    async def test_dry_run_accepts_daily_frequency(self):
        """override frequency=daily → 通过，timeframe 为 1d"""
        svc = RuntimeConfigService(session=None)
        template = _make_template()
        config = svc.resolve_config(template, {"frequency": "daily"})
        assert config["frequency"] == "daily"
        assert config["timeframe"] == "1d"


class TestSameDayDateRange:
    """BUG-STR-009：允许同日 dry-run（单日回测）。"""

    @pytest.mark.asyncio
    async def test_dry_run_accepts_same_day_range(self):
        """override start=end=2024-01-01 → resolve 通过"""
        svc = RuntimeConfigService(session=None)
        template = _make_template()
        config = svc.resolve_config(
            template,
            {"start_date": "2024-01-01", "end_date": "2024-01-01"},
        )
        assert config["start_date"] == "2024-01-01"
        assert config["end_date"] == "2024-01-01"

    @pytest.mark.asyncio
    async def test_dry_run_rejects_reverse_date_range(self):
        """override start > end → 抛 RuntimeConfigDateInvalid"""
        svc = RuntimeConfigService(session=None)
        template = _make_template()
        with pytest.raises(RuntimeConfigDateInvalid):
            svc.resolve_config(
                template,
                {"start_date": "2024-06-30", "end_date": "2024-01-01"},
            )

    @pytest.mark.asyncio
    async def test_template_default_dates_allow_same_day(self):
        """template 自身的 start==end 也应通过（BUG-STR-009 边界）"""
        svc = RuntimeConfigService(session=None)
        template = _make_template(start_date="2024-01-01", end_date="2024-01-01")
        # 不应抛异常
        config = svc.resolve_config(template, None)
        assert config["start_date"] == "2024-01-01"
        assert config["end_date"] == "2024-01-01"
