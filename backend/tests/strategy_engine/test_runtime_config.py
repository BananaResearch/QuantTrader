"""RuntimeConfigService 单元测试（strategy-engine-params-redesign）。

覆盖 runtime-config-template spec 中的业务逻辑：
- CRUD 操作（list_templates / create_template / update_template / delete_template）
- 系统预设保护（is_default 模板禁止修改/删除）
- resolve_config 合并逻辑（override 白名单、backtest 日期校验）
- 临时覆盖字段白名单
"""

import pytest
from datetime import date

from strategy_engine.schemas import (
    DataFrequency,
    RuntimeConfigTemplateCreate,
    RuntimeConfigTemplateUpdate,
    RuntimeMode,
)
from strategy_engine.service import RuntimeConfigService
from strategy_engine.exceptions import (
    InvalidOverrideField,
    RuntimeConfigDateInvalid,
    RuntimeConfigDateRequired,
    RuntimeConfigDefaultForbidden,
    RuntimeConfigNameDuplicated,
    RuntimeConfigNotFound,
)


@pytest.fixture
def svc(test_db):
    """RuntimeConfigService fixture。"""
    return RuntimeConfigService(test_db)


# ============================================================
# CRUD 操作
# ============================================================

class TestRuntimeConfigCRUD:
    """RuntimeConfigTemplate CRUD 测试。"""

    @pytest.mark.asyncio
    async def test_list_templates_default(self, svc):
        """list_templates() 默认返回所有模板。"""
        templates = await svc.list_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 4  # 至少 4 个种子模板

    @pytest.mark.asyncio
    async def test_list_templates_filter_by_mode(self, svc):
        """list_templates(mode='backtest') 只返回回测模板。"""
        templates = await svc.list_templates(mode="backtest")
        for t in templates:
            assert t.mode == "backtest"

    @pytest.mark.asyncio
    async def test_get_template_success(self, svc):
        """get_template(id) 返回模板。"""
        template = await svc.get_template(1)
        assert template.id == 1
        assert template.name is not None

    @pytest.mark.asyncio
    async def test_get_template_not_found(self, svc):
        """get_template(id) 不存在抛出 RuntimeConfigNotFound。"""
        with pytest.raises(RuntimeConfigNotFound):
            await svc.get_template(99999)

    @pytest.mark.asyncio
    async def test_create_template_success(self, svc):
        """create_template() 成功创建。"""
        data = RuntimeConfigTemplateCreate(
            name="测试模板",
            description="单元测试创建",
            mode=RuntimeMode.BACKTEST,
            universe=["000001.SZ"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            initial_capital=500000,
            frequency=DataFrequency.DAILY,
        )
        template = await svc.create_template(data)
        assert template.id is not None
        assert template.name == "测试模板"
        assert template.is_default is False

        # 清理
        await svc.delete_template(template.id)

    @pytest.mark.asyncio
    async def test_create_template_duplicate_name(self, svc):
        """create_template() 名称重复抛出 RuntimeConfigNameDuplicated。"""
        data = RuntimeConfigTemplateCreate(
            name="测试重复名称",
            mode=RuntimeMode.BACKTEST,
            universe=["000001.SZ"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        t1 = await svc.create_template(data)
        try:
            with pytest.raises(RuntimeConfigNameDuplicated):
                await svc.create_template(data)
        finally:
            await svc.delete_template(t1.id)

    @pytest.mark.asyncio
    async def test_update_template_success(self, svc):
        """update_template() 成功更新。"""
        data = RuntimeConfigTemplateCreate(
            name="更新测试",
            mode=RuntimeMode.BACKTEST,
            universe=["000001.SZ"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        t = await svc.create_template(data)

        update = RuntimeConfigTemplateUpdate(name="更新后名称")
        updated = await svc.update_template(t.id, update)
        assert updated.name == "更新后名称"

        # 清理
        await svc.delete_template(t.id)

    @pytest.mark.asyncio
    async def test_update_template_duplicate_name(self, svc):
        """update_template() 名称重复抛出 RuntimeConfigNameDuplicated。"""
        data1 = RuntimeConfigTemplateCreate(
            name="唯一名称A",
            mode=RuntimeMode.BACKTEST,
            universe=["000001.SZ"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        data2 = RuntimeConfigTemplateCreate(
            name="唯一名称B",
            mode=RuntimeMode.BACKTEST,
            universe=["000001.SZ"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        t1 = await svc.create_template(data1)
        t2 = await svc.create_template(data2)

        try:
            with pytest.raises(RuntimeConfigNameDuplicated):
                await svc.update_template(t1.id, RuntimeConfigTemplateUpdate(name="唯一名称B"))
        finally:
            await svc.delete_template(t1.id)
            await svc.delete_template(t2.id)

    @pytest.mark.asyncio
    async def test_delete_template_success(self, svc):
        """delete_template() 成功删除。"""
        data = RuntimeConfigTemplateCreate(
            name="删除测试",
            mode=RuntimeMode.BACKTEST,
            universe=["000001.SZ"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
        )
        t = await svc.create_template(data)
        tid = t.id
        await svc.delete_template(tid)

        with pytest.raises(RuntimeConfigNotFound):
            await svc.get_template(tid)


# ============================================================
# 系统预设保护
# ============================================================

class TestRuntimeConfigDefaultProtection:
    """is_default=True 的系统预设模板禁止修改/删除。"""

    @pytest.mark.asyncio
    async def test_update_default_template_forbidden(self, svc):
        """update_template() 修改系统预设抛出 RuntimeConfigDefaultForbidden。

        模板 1 是系统预设。
        """
        with pytest.raises(RuntimeConfigDefaultForbidden):
            await svc.update_template(1, RuntimeConfigTemplateUpdate(name="新名称"))

    @pytest.mark.asyncio
    async def test_delete_default_template_forbidden(self, svc):
        """delete_template() 删除系统预设抛出 RuntimeConfigDefaultForbidden。"""
        with pytest.raises(RuntimeConfigDefaultForbidden):
            await svc.delete_template(1)


# ============================================================
# resolve_config 合并逻辑
# ============================================================

class TestResolveConfig:
    """RuntimeConfigService.resolve_config() 测试。"""

    @pytest.mark.asyncio
    async def test_resolve_config_no_override(self, svc):
        """无 override 时返回模板原始配置。"""
        template = await svc.get_template(1)  # backtest 模板，有日期
        config = svc.resolve_config(template, None)

        assert config["mode"] == template.mode
        assert config["frequency"] == template.frequency
        assert config["initial_capital"] == float(template.initial_capital)
        assert "timeframe" in config  # _freq_to_timeframe 映射
        assert isinstance(config["universe"], list)

    @pytest.mark.asyncio
    async def test_resolve_config_with_override(self, svc):
        """有 override 时合并覆盖字段。"""
        template = await svc.get_template(1)
        override = {
            "universe": ["600519.SH"],
            "start_date": "2025-06-01",
            "end_date": "2025-06-30",
            "initial_capital": 2000000.0,
        }
        config = svc.resolve_config(template, override)

        assert config["universe"] == ["600519.SH"]
        assert config["start_date"] == "2025-06-01"
        assert config["end_date"] == "2025-06-30"
        assert config["initial_capital"] == 2000000.0

    @pytest.mark.asyncio
    async def test_resolve_config_invalid_override_field(self, svc):
        """override 包含白名单外字段抛出 InvalidOverrideField。"""
        template = await svc.get_template(1)
        override = {"invalid_field": "value"}
        with pytest.raises(InvalidOverrideField) as exc_info:
            svc.resolve_config(template, override)
        assert "不允许" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_resolve_config_backtest_missing_dates(self, svc, test_db):
        """backtest 模式无日期抛出 RuntimeConfigDateRequired。

        注：RuntimeConfigTemplateCreate schema 已拒绝 backtest 无日期的创建请求。
        此处通过 Repository 直接写入 DB（绕过 Schema 校验）来构造测试数据。
        """
        from strategy_engine.models import RuntimeConfigTemplate
        import time

        # 直接写入 DB，绕过 Schema 校验
        t = RuntimeConfigTemplate(
            name=f"无日期模板_{int(time.time())}",
            mode="backtest",
            universe=["000001.SZ"],
            start_date=None,
            end_date=None,
            initial_capital=1000000,
            frequency="daily",
            slippage=0.0003,
            commission=0.0001,
            is_default=False,
        )
        test_db.add(t)
        await test_db.flush()
        tid = t.id

        try:
            # get_template 通过 Repository 加载
            template = await svc.get_template(tid)
            with pytest.raises(RuntimeConfigDateRequired):
                svc.resolve_config(template, None)
        finally:
            await test_db.delete(t)
            await test_db.flush()

    @pytest.mark.asyncio
    async def test_resolve_config_backtest_invalid_date_order(self, svc, test_db):
        """backtest 模式 start_date >= end_date 抛出 RuntimeConfigDateInvalid。

        同上，通过 Repository 直接构造数据。
        """
        from strategy_engine.models import RuntimeConfigTemplate
        import time

        t = RuntimeConfigTemplate(
            name=f"无效日期顺序_{int(time.time())}",
            mode="backtest",
            universe=["000001.SZ"],
            start_date=date(2025, 12, 31),
            end_date=date(2025, 1, 1),
            initial_capital=1000000,
            frequency="daily",
            slippage=0.0003,
            commission=0.0001,
            is_default=False,
        )
        test_db.add(t)
        await test_db.flush()
        tid = t.id

        try:
            template = await svc.get_template(tid)
            with pytest.raises(RuntimeConfigDateInvalid):
                svc.resolve_config(template, None)
        finally:
            await test_db.delete(t)
            await test_db.flush()

    @pytest.mark.asyncio
    async def test_resolve_config_live_mode_no_dates_required(self, svc):
        """live 模式无需日期约束。"""
        template = await svc.get_template(3)  # 保守实盘模板，live 模式
        config = svc.resolve_config(template, None)
        assert config["mode"] == "live"

    @pytest.mark.asyncio
    async def test_resolve_config_frequency_maps_to_timeframe(self, svc):
        """frequency='daily' 映射到 timeframe='1d'。"""
        template = await svc.get_template(1)
        config = svc.resolve_config(template, None)
        assert config["timeframe"] == "1d"

    @pytest.mark.asyncio
    async def test_resolve_config_override_frequency_syncs_timeframe(self, svc):
        """override frequency=daily 时同步更新 timeframe（BUG-STR-005：仅支持 daily）。"""
        template = await svc.get_template(1)
        config = svc.resolve_config(template, {"frequency": "daily"})
        assert config["frequency"] == "daily"
        assert config["timeframe"] == "1d"

    @pytest.mark.asyncio
    async def test_resolve_config_override_frequency_rejects_non_daily(self, svc):
        """BUG-STR-005：override frequency=1min 应被拒绝。"""
        from strategy_engine.exceptions import InvalidOverrideField
        template = await svc.get_template(1)
        with pytest.raises(InvalidOverrideField):
            svc.resolve_config(template, {"frequency": "1min"})

    @pytest.mark.asyncio
    async def test_resolve_config_universe_empty_list(self, svc, test_db):
        """universe 为空时返回空列表。

        注：RuntimeConfigTemplateCreate 要求 universe 至少 1 项。
        此处通过 Repository 直接写入空 universe。
        """
        from strategy_engine.models import RuntimeConfigTemplate
        import time

        t = RuntimeConfigTemplate(
            name=f"空universe模板_{int(time.time())}",
            mode="live",
            universe=[],
            initial_capital=1000000,
            frequency="daily",
            slippage=0.0003,
            commission=0.0001,
            is_default=False,
        )
        test_db.add(t)
        await test_db.flush()
        tid = t.id

        try:
            template = await svc.get_template(tid)
            config = svc.resolve_config(template, None)
            assert config["universe"] == []
        finally:
            await test_db.delete(t)
            await test_db.flush()
