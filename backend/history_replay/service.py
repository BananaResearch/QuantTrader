"""历史回放模块 - 业务逻辑层（stub，返回 mock 数据）"""

from .schemas import (
    StockOption,
    StrategyOption,
    VirtualAccountOption,
    KlineBar,
    TradeSignal,
    TradeRecord,
    ReplayMetrics,
    EquityPoint,
    ReplaySession,
    ReplayProgress,
    ReplayStatus,
    TradeSide,
)


async def search_stocks(keyword: str, limit: int = 10) -> list[StockOption]:
    """搜索股票 - stub"""
    mock_data = [
        StockOption(code="000001.SZ", name="平安银行", pinyin="PAYH"),
        StockOption(code="000002.SZ", name="万科A", pinyin="WKA"),
        StockOption(code="600519.SH", name="贵州茅台", pinyin="GZMT"),
        StockOption(code="601318.SH", name="中国平安", pinyin="ZGPA"),
        StockOption(code="000858.SZ", name="五粮液", pinyin="WLY"),
        StockOption(code="600036.SH", name="招商银行", pinyin="ZSYH"),
        StockOption(code="000333.SZ", name="美的集团", pinyin="MDJT"),
        StockOption(code="600276.SH", name="恒瑞医药", pinyin="HRYY"),
        StockOption(code="601166.SH", name="兴业银行", pinyin="XYYH"),
        StockOption(code="000651.SZ", name="格力电器", pinyin="GLDQ"),
    ]
    keyword_lower = keyword.lower()
    results = [
        s for s in mock_data
        if keyword_lower in s.code.lower()
        or keyword_lower in s.name
        or keyword_lower in s.pinyin.lower()
    ]
    return results[:limit]


async def list_strategies() -> list[StrategyOption]:
    """获取策略列表 - stub"""
    return [
        StrategyOption(id=1, name="双均线交叉", description="短期均线上穿长期均线买入"),
        StrategyOption(id=2, name="RSI超买超卖", description="RSI低于30买入，高于70卖出"),
        StrategyOption(id=3, name="布林带突破", description="价格突破布林带上下轨"),
        StrategyOption(id=4, name="MACD金叉死叉", description="MACD金叉买入，死叉卖出"),
    ]


async def list_virtual_accounts() -> list[VirtualAccountOption]:
    """获取虚拟账户列表 - stub"""
    return [
        VirtualAccountOption(id=1, name="默认账户", initial_capital=1000000.00),
        VirtualAccountOption(id=2, name="激进账户", initial_capital=500000.00),
        VirtualAccountOption(id=3, name="保守账户", initial_capital=2000000.00),
    ]


async def start_replay(
    stock_code: str,
    strategy_id: int,
    account_id: int,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> ReplaySession:
    """启动回测 - stub"""
    return ReplaySession(
        session_id=1,
        stock_code=stock_code,
        strategy_id=strategy_id,
        account_id=account_id,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        status=ReplayStatus.RUNNING,
        current_index=0,
        total_bars=240,
    )


async def get_session(session_id: int) -> ReplaySession:
    """获取回测会话 - stub"""
    return ReplaySession(
        session_id=session_id,
        stock_code="000001.SZ",
        strategy_id=1,
        account_id=1,
        timeframe="1d",
        start_date="2024-01-01",
        end_date="2024-12-31",
        status=ReplayStatus.RUNNING,
        current_index=120,
        total_bars=240,
    )


async def control_replay(session_id: int, action: str) -> ReplaySession:
    """控制回测（暂停/继续/停止）- stub"""
    status_map = {
        "pause": ReplayStatus.PAUSED,
        "resume": ReplayStatus.RUNNING,
        "stop": ReplayStatus.COMPLETED,
    }
    return ReplaySession(
        session_id=session_id,
        stock_code="000001.SZ",
        strategy_id=1,
        account_id=1,
        timeframe="1d",
        start_date="2024-01-01",
        end_date="2024-12-31",
        status=status_map.get(action, ReplayStatus.RUNNING),
        current_index=120,
        total_bars=240,
    )


async def set_replay_speed(session_id: int, speed: int) -> ReplayProgress:
    """设置回测速度 - stub"""
    return ReplayProgress(
        current_index=120,
        total_bars=240,
        speed=speed,
        status=ReplayStatus.RUNNING,
    )


async def get_kline_data(session_id: int) -> list[KlineBar]:
    """获取回测K线数据 - stub"""
    import random
    random.seed(42)
    base_price = 15.50
    bars = []
    for i in range(240):
        change = random.uniform(-0.3, 0.3)
        open_ = base_price
        close = base_price + change
        high = max(open_, close) + random.uniform(0, 0.2)
        low = min(open_, close) - random.uniform(0, 0.2)
        volume = round(random.uniform(50000, 200000), 0)
        bars.append(KlineBar(
            time=f"2024-{(i // 20) + 1:02d}-{(i % 20) + 1:02d}",
            open=round(open_, 2),
            high=round(high, 2),
            low=round(low, 2),
            close=round(close, 2),
            volume=volume,
        ))
        base_price = close
    return bars


async def get_trade_signals(session_id: int) -> list[TradeSignal]:
    """获取交易信号 - stub"""
    return [
        TradeSignal(time="2024-02-15", side=TradeSide.BUY, price=16.20, quantity=1000, signal="均线金叉"),
        TradeSignal(time="2024-04-10", side=TradeSide.SELL, price=17.80, quantity=1000, signal="均线死叉"),
        TradeSignal(time="2024-06-05", side=TradeSide.BUY, price=15.90, quantity=1500, signal="RSI超卖"),
        TradeSignal(time="2024-08-20", side=TradeSide.SELL, price=18.50, quantity=1500, signal="RSI超买"),
        TradeSignal(time="2024-10-12", side=TradeSide.BUY, price=16.80, quantity=1200, signal="布林带下轨"),
        TradeSignal(time="2024-11-28", side=TradeSide.SELL, price=19.10, quantity=1200, signal="布林带上轨"),
    ]


async def get_trade_records(session_id: int) -> list[TradeRecord]:
    """获取交易记录 - stub"""
    return [
        TradeRecord(
            id=1, time="2024-02-15", side=TradeSide.BUY,
            stock_code="000001.SZ", price=16.20, quantity=1000,
            amount=16200.00, pnl=0, commission=24.30,
            signal="均线金叉",
        ),
        TradeRecord(
            id=2, time="2024-04-10", side=TradeSide.SELL,
            stock_code="000001.SZ", price=17.80, quantity=1000,
            amount=17800.00, pnl=1600.00, commission=26.70,
            signal="均线死叉",
        ),
        TradeRecord(
            id=3, time="2024-06-05", side=TradeSide.BUY,
            stock_code="000001.SZ", price=15.90, quantity=1500,
            amount=23850.00, pnl=0, commission=35.78,
            signal="RSI超卖",
        ),
        TradeRecord(
            id=4, time="2024-08-20", side=TradeSide.SELL,
            stock_code="000001.SZ", price=18.50, quantity=1500,
            amount=27750.00, pnl=3900.00, commission=41.63,
            signal="RSI超买",
        ),
        TradeRecord(
            id=5, time="2024-10-12", side=TradeSide.BUY,
            stock_code="000001.SZ", price=16.80, quantity=1200,
            amount=20160.00, pnl=0, commission=30.24,
            signal="布林带下轨",
        ),
        TradeRecord(
            id=6, time="2024-11-28", side=TradeSide.SELL,
            stock_code="000001.SZ", price=19.10, quantity=1200,
            amount=22920.00, pnl=2760.00, commission=34.38,
            signal="布林带上轨",
        ),
    ]


async def get_metrics(session_id: int) -> ReplayMetrics:
    """获取回测指标 - stub"""
    return ReplayMetrics(
        total_return=32.5,
        annual_return=18.2,
        max_drawdown=-12.3,
        sharpe_ratio=1.85,
        win_rate=62.3,
        profit_loss_ratio=2.1,
        trade_count=6,
        total_pnl=8260.00,
    )


async def get_equity_curve(session_id: int) -> list[EquityPoint]:
    """获取资金曲线 - stub"""
    import random
    random.seed(42)
    points = []
    equity = 1000000.00
    peak = equity
    for i in range(240):
        change = random.uniform(-0.02, 0.025)
        equity = equity * (1 + change)
        peak = max(peak, equity)
        drawdown = (equity - peak) / peak * 100
        points.append(EquityPoint(
            time=f"2024-{(i // 20) + 1:02d}-{(i % 20) + 1:02d}",
            equity=round(equity, 2),
            drawdown=round(drawdown, 2),
        ))
    return points
