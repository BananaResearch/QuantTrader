"""历史回放模块 - 路由定义"""

from fastapi import APIRouter

from .schemas import (
    ReplayStartRequest,
    ReplayControlRequest,
    ReplaySpeedRequest,
    StockSearchRequest,
)
from .service import (
    search_stocks,
    list_strategies,
    list_virtual_accounts,
    start_replay,
    get_session,
    control_replay,
    set_replay_speed,
    get_kline_data,
    get_trade_signals,
    get_trade_records,
    get_metrics,
    get_equity_curve,
)

router = APIRouter(prefix="/api/replay", tags=["历史回放"])


# === 配置数据接口 ===

@router.post("/stocks/search")
async def search_stocks_api(req: StockSearchRequest):
    """搜索股票（代码/名称/拼音模糊匹配）"""
    data = await search_stocks(req.keyword, req.limit)
    return {"success": True, "data": [d.model_dump() for d in data]}


@router.get("/strategies")
async def list_strategies_api():
    """获取策略列表"""
    data = await list_strategies()
    return {"success": True, "data": [d.model_dump() for d in data]}


@router.get("/virtual-accounts")
async def list_virtual_accounts_api():
    """获取虚拟账户列表"""
    data = await list_virtual_accounts()
    return {"success": True, "data": [d.model_dump() for d in data]}


# === 回测控制接口 ===

@router.post("/start")
async def start_replay_api(req: ReplayStartRequest):
    """启动回测"""
    data = await start_replay(
        stock_code=req.stock_code,
        strategy_id=req.strategy_id,
        account_id=req.account_id,
        timeframe=req.timeframe,
        start_date=req.start_date,
        end_date=req.end_date,
    )
    return {"success": True, "data": data.model_dump()}


@router.get("/session/{session_id}")
async def get_session_api(session_id: int):
    """获取回测会话状态"""
    data = await get_session(session_id)
    return {"success": True, "data": data.model_dump()}


@router.post("/control")
async def control_replay_api(req: ReplayControlRequest):
    """控制回测（暂停/继续/停止）"""
    data = await control_replay(req.session_id, req.action)
    return {"success": True, "data": data.model_dump()}


@router.post("/speed")
async def set_replay_speed_api(req: ReplaySpeedRequest):
    """设置回测播放速度"""
    data = await set_replay_speed(req.session_id, req.speed)
    return {"success": True, "data": data.model_dump()}


# === 回测数据接口 ===

@router.get("/kline/{session_id}")
async def get_kline_data_api(session_id: int):
    """获取回测K线数据"""
    data = await get_kline_data(session_id)
    return {"success": True, "data": [d.model_dump() for d in data]}


@router.get("/signals/{session_id}")
async def get_trade_signals_api(session_id: int):
    """获取交易信号"""
    data = await get_trade_signals(session_id)
    return {"success": True, "data": [d.model_dump() for d in data]}


@router.get("/trades/{session_id}")
async def get_trade_records_api(session_id: int):
    """获取交易记录"""
    data = await get_trade_records(session_id)
    return {"success": True, "data": [d.model_dump() for d in data]}


@router.get("/metrics/{session_id}")
async def get_metrics_api(session_id: int):
    """获取回测指标"""
    data = await get_metrics(session_id)
    return {"success": True, "data": data.model_dump()}


@router.get("/equity/{session_id}")
async def get_equity_curve_api(session_id: int):
    """获取资金曲线"""
    data = await get_equity_curve(session_id)
    return {"success": True, "data": [d.model_dump() for d in data]}
