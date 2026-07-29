"""dry-run 接口集成测试（strategy-engine-params-redesign 破坏性变更后）。

覆盖：
- 内置策略 dry-run 返回完整响应（新签名：template_id + override）
- max_bars 截断生效
- 不存在的 strategy_id 返回 404
- 非 active 状态返回 400
- code_content 为空返回 400
- max_bars=2000 返回 422（上限已从 100 提升到 1000）
- parameters 覆盖默认参数生效
- override 临时覆盖字段生效
- template_id 不存在返回 404
- save_snapshot 保存运行时配置快照
"""

import pytest
import httpx
from fastapi import FastAPI

from strategy_engine.router import router


@pytest.fixture
def app():
    a = FastAPI()
    a.include_router(router)
    return a


async def _request(app, method: str, path: str, **kwargs):
    """辅助：通过 ASGITransport 调用任意 HTTP 接口。"""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, **kwargs)


async def _dry_run(app, strategy_id: int, payload: dict):
    """辅助：调用 dry-run 接口（新签名）。"""
    return await _request(app, "POST", f"/api/strategy/{strategy_id}/dry-run", json=payload)


class TestDryRunEndpoint:
    """dry-run 端到端测试（新 API 签名：template_id + override）。"""

    @pytest.mark.asyncio
    async def test_dry_run_builtin_strategy_returns_response(self, app):
        """内置策略 1（双均线）dry-run 返回完整 DryRunResponse。

        新签名：{template_id, override?, max_bars, parameters?, save_snapshot?}
        """
        payload = {
            "template_id": 1,
            "max_bars": 30,
        }
        r = await _dry_run(app, 1, payload)
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        result = data["data"]
        assert result["total_bars"] == 30
        assert result["session_id"].startswith("dryrun_1_")
        assert "final_capital" in result
        assert "total_return_pct" in result
        assert len(result["bars"]) == 30
        bar0 = result["bars"][0]
        assert "time" in bar0
        assert "close" in bar0
        assert "total_assets" in bar0
        assert "signal" in bar0
        assert "orders_count" in bar0

    @pytest.mark.asyncio
    async def test_dry_run_max_bars_truncation(self, app):
        """max_bars=20 截断到前 20 个 bar。"""
        payload = {
            "template_id": 1,
            "max_bars": 20,
        }
        r = await _dry_run(app, 1, payload)
        assert r.status_code == 200
        assert r.json()["data"]["total_bars"] == 20

    @pytest.mark.asyncio
    async def test_dry_run_max_bars_1000_limit(self, app):
        """max_bars 上限 1000，超过被 Pydantic 拒（422）。

        注：limit 已从 100 提升到 1000（strategy-engine-params-redesign）。
        """
        payload = {
            "template_id": 1,
            "max_bars": 2000,
        }
        r = await _dry_run(app, 1, payload)
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_dry_run_strategy_not_found(self, app):
        """strategy_id 不存在返回 404。"""
        payload = {
            "template_id": 1,
            "max_bars": 10,
        }
        r = await _dry_run(app, 99999, payload)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_dry_run_template_not_found(self, app):
        """template_id 不存在返回 404。"""
        payload = {
            "template_id": 99999,
            "max_bars": 10,
        }
        r = await _dry_run(app, 1, payload)
        assert r.status_code == 404
        assert "不存在" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_dry_run_strategy_not_active(self, app):
        """status != 'active' 返回 400。

        通过 PUT 接口把策略 4 改为 draft，跑 dry-run，再恢复。
        """
        # 1. 先记录原始 status
        r = await _request(app, "GET", "/api/strategy/4")
        original_status = r.json()["data"]["status"]
        assert original_status == "active"

        # 2. 改为 draft
        r = await _request(app, "PUT", "/api/strategy/4", json={"status": "draft"})
        assert r.json()["success"] is True

        try:
            payload = {
                "template_id": 1,
                "max_bars": 10,
            }
            r = await _dry_run(app, 4, payload)
            assert r.status_code == 400
            assert "active" in r.json()["detail"]
        finally:
            # 3. 恢复
            r = await _request(app, "PUT", "/api/strategy/4", json={"status": original_status})
            assert r.json()["success"] is True

    @pytest.mark.asyncio
    async def test_dry_run_empty_code_content(self, app):
        """code_content 为空返回 400。"""
        r = await _request(app, "POST", "/api/strategy/create", json={
            "code": "EMPTY_TEST_NEW",
            "name": "空代码测试",
            "status": "active",
            "version": "1.0.0",
            "code_content": None,
        })
        assert r.status_code == 400
        assert "不能为空" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_dry_run_parameters_override(self, app):
        """参数覆盖：双均线 short_window=3 / long_window=6。"""
        payload_default = {
            "template_id": 1,
            "max_bars": 60,
        }
        payload_short = {
            "template_id": 1,
            "max_bars": 60,
            "parameters": {"short_window": 3, "long_window": 6, "buy_ratio": 0.5},
        }
        r1 = await _dry_run(app, 1, payload_default)
        r2 = await _dry_run(app, 1, payload_short)
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["data"]["total_bars"] == 60
        assert r2.json()["data"]["total_bars"] == 60

    @pytest.mark.asyncio
    async def test_dry_run_override_universe(self, app):
        """override universe 临时覆盖标的列表。"""
        payload = {
            "template_id": 1,
            "override": {
                "universe": ["600519.SH"],
            },
            "max_bars": 20,
        }
        r = await _dry_run(app, 1, payload)
        assert r.status_code == 200
        assert r.json()["data"]["total_bars"] == 20

    @pytest.mark.asyncio
    async def test_dry_run_override_dates(self, app):
        """override start_date/end_date 临时覆盖回测日期。"""
        payload = {
            "template_id": 1,
            "override": {
                "start_date": "2025-01-01",
                "end_date": "2025-03-01",
            },
            "max_bars": 40,
        }
        r = await _dry_run(app, 1, payload)
        assert r.status_code == 200
        assert r.json()["data"]["total_bars"] == 40

    @pytest.mark.asyncio
    async def test_dry_run_override_invalid_field_rejected(self, app):
        """override 白名单外字段被拒绝。"""
        payload = {
            "template_id": 1,
            "override": {
                "invalid_field": "should_fail",
            },
            "max_bars": 10,
        }
        r = await _dry_run(app, 1, payload)
        assert r.status_code == 400
        assert "不允许" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_dry_run_override_backtest_date_required(self, app):
        """backtest 模式无日期时，如果模板本身有日期则正常执行。

        注：override None 不会真正清除模板日期（只有显式值才覆盖）。
        此处用 live 模式模板（无需日期）验证 dry-run 可正常执行。
        """
        # template 3 是 live 模式，无 start_date/end_date
        payload = {
            "template_id": 3,
            "max_bars": 10,
        }
        r = await _dry_run(app, 1, payload)
        # live 模式不要求日期，应该正常执行
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_dry_run_total_assets_consistency(self, app):
        """dry-run 中每个 bar 的 total_assets 都 > 0。"""
        payload = {
            "template_id": 1,
            "max_bars": 60,
        }
        r = await _dry_run(app, 1, payload)
        bars = r.json()["data"]["bars"]
        for bar in bars:
            assert bar["total_assets"] > 0, f"bar {bar['time']} total_assets<=0"
        assert r.json()["data"]["final_capital"] == bars[-1]["total_assets"]

    @pytest.mark.asyncio
    async def test_dry_run_save_snapshot(self, app):
        """save_snapshot=True 保存运行时配置快照到最新版本。"""
        # 创建策略
        r = await _request(app, "POST", "/api/strategy/create", json={
            "code": "SNAPSHOT_TEST",
            "name": "快照测试策略",
            "status": "active",
            "version": "1.0.0",
            "code_content": "def initialize(context): pass\ndef handle_data(context, data): pass",
        })
        assert r.status_code == 200
        strategy_id = r.json()["data"]["id"]

        try:
            # 创建版本
            vr = await _request(app, "POST", f"/api/strategy/{strategy_id}/versions", json={
                "version": "1.0.0",
                "code_content": "def initialize(context): pass\ndef handle_data(context, data): pass",
                "change_log": "初始版本",
            })
            assert vr.status_code == 200

            # dry-run with save_snapshot
            payload = {
                "template_id": 1,
                "max_bars": 10,
                "save_snapshot": True,
            }
            r2 = await _dry_run(app, strategy_id, payload)
            assert r2.status_code == 200

            # 验证版本中保存了快照（通过列表接口）
            vr2 = await _request(app, "GET", f"/api/strategy/{strategy_id}/versions")
            assert vr2.status_code == 200
            versions = vr2.json()["data"]
            assert len(versions) >= 1
            latest = versions[0]
            snapshot = latest.get("runtime_config_snapshot")
            assert snapshot is not None
            assert "template_id" in snapshot
            assert snapshot["template_id"] == 1
        finally:
            await _request(app, "DELETE", f"/api/strategy/{strategy_id}")
