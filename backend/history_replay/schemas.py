"""历史回放模块 - Pydantic 请求/响应模型"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


# === 枚举 ===

class TimeFrame(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class ReplayStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


# === 请求模型 ===

class ReplayStartRequest(BaseModel):
    """启动回测请求"""
    stock_code: str = Field(..., description="股票代码")
    strategy_id: int = Field(..., description="策略ID")
    account_id: int = Field(..., description="虚拟账户ID")
    timeframe: TimeFrame = Field(..., description="时间间隔")
    start_date: str = Field(..., description="起始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")


class ReplayControlRequest(BaseModel):
    """回测控制请求（暂停/继续/停止）"""
    session_id: int = Field(..., description="回测会话ID")
    action: str = Field(..., description="操作: pause / resume / stop")


class ReplaySpeedRequest(BaseModel):
    """回测速度控制"""
    session_id: int = Field(..., description="回测会话ID")
    speed: int = Field(..., description="速度倍率: 1 / 2 / 4 / 8")


class StockSearchRequest(BaseModel):
    """股票搜索请求"""
    keyword: str = Field(..., description="搜索关键词（代码/名称/拼音）")
    limit: int = Field(default=10, description="返回数量上限")


# === 响应模型 ===

class StockOption(BaseModel):
    code: str
    name: str
    pinyin: str


class StrategyOption(BaseModel):
    id: int
    name: str
    description: Optional[str] = None


class VirtualAccountOption(BaseModel):
    id: int
    name: str
    initial_capital: float


class KlineBar(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class TradeSignal(BaseModel):
    time: str
    side: TradeSide
    price: float
    quantity: float
    signal: str


class TradeRecord(BaseModel):
    id: int
    time: str
    side: TradeSide
    stock_code: str
    price: float
    quantity: float
    amount: float
    pnl: float
    commission: float
    signal: str


class ReplayMetrics(BaseModel):
    total_return: float = Field(..., description="总收益率(%)")
    annual_return: float = Field(..., description="年化收益率(%)")
    max_drawdown: float = Field(..., description="最大回撤(%)")
    sharpe_ratio: float = Field(..., description="夏普比率")
    win_rate: float = Field(..., description="胜率(%)")
    profit_loss_ratio: float = Field(..., description="盈亏比")
    trade_count: int = Field(..., description="交易次数")
    total_pnl: float = Field(..., description="总盈亏")


class EquityPoint(BaseModel):
    time: str
    equity: float
    drawdown: float


class ReplaySession(BaseModel):
    session_id: int
    stock_code: str
    strategy_id: int
    account_id: int
    timeframe: TimeFrame
    start_date: str
    end_date: str
    status: ReplayStatus
    current_index: int = 0
    total_bars: int = 0


class ReplayProgress(BaseModel):
    current_index: int
    total_bars: int
    speed: int = 1
    status: ReplayStatus
