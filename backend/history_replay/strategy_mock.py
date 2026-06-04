"""
模拟策略模块的回测方法返回数据。

本文件模拟调用策略模块内部方法（非HTTP接口）的返回值。
当策略模块尚未开发完成时，用此 mock 数据提前开发和验证
我们的指标计算逻辑和报告渲染。

调用方式（未来替换为真实调用）：
    from strategy_engine.service import run_backtest
    result = await run_backtest(stock_code, strategy_id, account_id, timeframe, start_date, end_date)

当前 mock 调用方式：
    from history_replay.strategy_mock import run_backtest_mock
    result = await run_backtest_mock(stock_code, strategy_id, account_id, timeframe, start_date, end_date)
"""

import random
from datetime import date, timedelta
from typing import Optional


# ============================================================
# 数据结构定义
# 策略模块方法返回 BacktestResult，包含基础信息 + 逐bar明细
# 我们基于这些原始数据自行统计所有报告指标
# ============================================================

class OrderRecord:
    """
    单笔订单记录。
    
    业务含义：回测过程中发生的一次虚拟交易（买入或卖出）。
    策略信号触发后，策略模块内部执行模拟撮合产生的成交记录。
    
    用途：
    - 交易详情表的数据源（时间/方向/价格/数量/手续费/盈亏/信号）
    - 计算胜率：统计 pnl > 0 的卖出订单占比
    - 计算盈亏比：平均盈利金额 / 平均亏损金额
    - 计算交易次数：卖出订单数量（一买一卖算一笔完整交易）
    - 计算总盈亏：所有卖出订单的 pnl 之和
    """

    def __init__(
        self,
        time: str,           # 成交时间，格式 "YYYY-MM-DD"
                             # 业务含义：这笔交易发生在哪个交易日
                             # 用途：交易详情表的"时间"列

        side: str,           # 交易方向，"buy" 或 "sell"
                             # 业务含义：这笔是买入还是卖出
                             # 用途：交易详情表的"方向"列，买入显示红色、卖出显示绿色（中国惯例）

        price: float,        # 成交价格（每股）
                             # 业务含义：这笔交易以什么价格成交，回测中通常取当bar收盘价
                             # 用途：交易详情表的"价格"列

        quantity: int,       # 成交数量（股数）
                             # 业务含义：买了或卖了多少股，由策略模块内部的仓位管理决定
                             # 用途：交易详情表的"数量"列

        amount: float,       # 成交金额 = price × quantity
                             # 业务含义：这笔交易花了或收了多少钱
                             # 用途：交易详情表的"金额"列

        commission: float,   # 手续费
                             # 业务含义：券商佣金+印花税等交易成本
                             # 用途：交易详情表的"手续费"列，也影响盈亏计算的准确性

        pnl: float,          # 盈亏金额（卖出时为该笔卖出的已实现盈亏，买入时为0）
                             # 业务含义：这笔卖出相比对应买入赚了或亏了多少钱
                             # 计算方式：(卖出价 - 买入均价) × 数量 - 买入手续费 - 卖出手续费
                             # 用途：交易详情表的"盈亏"列，正数红色、负数绿色
                             #      计算胜率：pnl > 0 的卖出算"胜"
                             #      计算盈亏比：avg(盈利pnl) / |avg(亏损pnl)|
                             #      计算总盈亏：sum(所有卖出订单的pnl)

        signal: str,         # 触发信号名称，如 "均线金叉"、"RSI超卖"
                             # 业务含义：是哪个策略信号触发了这笔交易
                             # 用途：交易详情表的"触发信号"列，日志输出
    ):
        self.time = time
        self.side = side
        self.price = price
        self.quantity = quantity
        self.amount = amount
        self.commission = commission
        self.pnl = pnl
        self.signal = signal


class PositionRecord:
    """
    单个持仓记录。
    
    业务含义：某个交易日收盘时，账户中持有某只股票的详细信息。
    每个bar结束后，策略模块记录当前持仓状态。
    
    用途：
    - 每日持仓&收益表的数据源
    - 验证 total_assets = cash + sum(所有持仓的market_value)
    """

    def __init__(
        self,
        stock_code: str,     # 股票代码，如 "000001.SZ"
                             # 业务含义：持有的是哪只股票
                             # 用途：每日持仓表的"股票代码"列

        quantity: int,       # 持仓数量（股数）
                             # 业务含义：当前持有多少股
                             # 用途：每日持仓表的"持仓数量"列

        cost_price: float,   # 成本价（买入均价）
                             # 业务含义：这些股票平均每股花了多少钱买入
                             # 用途：每日持仓表的"成本价"列，计算浮盈的依据

        current_price: float,# 当前价格（当日收盘价）
                             # 业务含义：这只股票今天值多少钱
                             # 用途：计算市值和浮盈

        market_value: float, # 市值 = quantity × current_price
                             # 业务含义：这些股票目前总共值多少钱
                             # 用途：每日持仓表的"市值"列

        floating_pnl: float, # 浮盈 = market_value - (cost_price × quantity)
                             # 业务含义：这些股票目前赚了或亏了多少（未实现盈亏）
                             # 正数表示浮盈，负数表示浮亏
                             # 用途：每日持仓表的"浮盈"列，正数红色、负数绿色
    ):
        self.stock_code = stock_code
        self.quantity = quantity
        self.cost_price = cost_price
        self.current_price = current_price
        self.market_value = market_value
        self.floating_pnl = floating_pnl


class BarRecord:
    """
    单根K线bar的完整记录。
    
    业务含义：回测过程中一个时间点（一天/一小时/一分钟）的全部信息。
    包含行情数据、策略信号、交易记录、持仓状态、账户快照和日志。
    
    这是我们统计所有报告指标的核心数据源。
    """

    def __init__(
        self,
        # ── 行情数据 ──
        time: str,               # 交易日期/时间，格式 "YYYY-MM-DD"
                                 # 业务含义：这根bar对应哪个交易日
                                 # 用途：所有图表的X轴时间、交易详情/持仓表的日期列

        open: float,             # 开盘价
                                 # 业务含义：这个交易时段的第一笔成交价
                                 # 用途：K线图渲染（回放视图）

        high: float,             # 最高价
                                 # 业务含义：这个交易时段的最高成交价
                                 # 用途：K线图渲染

        low: float,              # 最低价
                                 # 业务含义：这个交易时段的最低成交价
                                 # 用途：K线图渲染

        close: float,            # 收盘价
                                 # 业务含义：这个交易时段的最后一笔成交价
                                 # 用途：K线图渲染、模拟撮合的成交价、计算收益率
                                 #      计算策略日收益率：(当日total_assets/前日total_assets) - 1

        volume: int,             # 成交量（股）
                                 # 业务含义：这个交易时段总共成交了多少股
                                 # 用途：K线图成交量柱

        amount: float,           # 成交额（元）
                                 # 业务含义：这个交易时段总共成交了多少钱
                                 # 用途：K线图辅助信息

        benchmark_close: float,  # 基准收盘价（如沪深300指数收盘价）
                                 # 业务含义：市场基准在这个交易时段的收盘价
                                 # 用途：计算基准收益率：(当日benchmark_close/前日benchmark_close) - 1
                                 #      计算Alpha：策略超额收益中无法被市场解释的部分
                                 #      计算Beta：策略收益对市场收益的敏感度
                                 #      计算信息率：策略超额收益的稳定性
                                 #      计算基准波动率：基准日收益率标准差 × √252
                                 #      策略vs基准收益对比图

        # ── 策略信号 ──
        signal: Optional[str],   # 触发的信号，"buy"/"sell"/None
                                 # 业务含义：策略引擎在这根bar上产生了什么交易信号
                                 # None表示无信号，策略建议持有不动
                                 # 用途：K线图上的买卖标记（红箭头买入/绿箭头卖出）

        signal_reason: Optional[str],  # 信号触发原因，如 "均线金叉"/"RSI超卖"
                                       # 业务含义：为什么策略触发了这个信号
                                       # 用途：交易详情表"触发信号"列、日志输出

        # ── 交易记录 ──
        orders: list,            # 当日订单列表 [OrderRecord]
                                 # 业务含义：这根bar上执行了哪些交易
                                 # 无信号无交易时为空列表
                                 # 用途：交易详情表的完整数据源
                                 #      计算胜率/盈亏比/交易次数/总盈亏

        # ── 持仓状态 ──
        positions: list,         # 当日持仓列表 [PositionRecord]
                                 # 业务含义：这根bar收盘时账户持有哪些股票
                                 # 空仓时为空列表
                                 # 用途：每日持仓&收益表的完整数据源

        # ── 账户快照 ──
        cash: float,             # 现金余额
                                 # 业务含义：账户中还有多少可用现金
                                 # 用途：验证 total_assets = cash + sum(持仓市值)
                                 #      日志记录"现金不足"时的判断依据

        total_assets: float,     # 总资产 = cash + sum(所有持仓的market_value)
                                 # ★ 最核心字段 ★
                                 # 业务含义：这个交易时段结束时账户总共值多少钱
                                 # 用途：计算策略总收益率：(期末total_assets / 期初total_assets) - 1
                                 #      计算策略日收益率：(当日total_assets / 前日total_assets) - 1
                                 #      计算最大回撤：max((峰值-谷值)/峰值)
                                 #      计算夏普比率：(日均收益-无风险) / 日收益标准差
                                 #      计算索提诺比率：(日均收益-无风险) / 下行标准差
                                 #      计算策略波动率：日收益率标准差 × √252
                                 #      生成资金曲线
                                 #      生成每日盈亏柱状图

        # ── 日志 ──
        log_entries: list,       # 当日日志条目 [str]
                                 # 业务含义：回测过程中产生的运行日志
                                 # 用途：日志输出面板
    ):
        self.time = time
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        self.amount = amount
        self.benchmark_close = benchmark_close
        self.signal = signal
        self.signal_reason = signal_reason
        self.orders = orders
        self.positions = positions
        self.cash = cash
        self.total_assets = total_assets
        self.log_entries = log_entries


class BacktestResult:
    """
    策略模块 run_backtest 方法的返回值。
    
    业务含义：一次完整回测的结果。包含基础信息 + 逐bar原始明细，
    不包含任何统计指标——指标由我们模块自行计算。
    
    设计原则：
    - 策略模块只负责"跑策略"和"记录原始数据"
    - 我们模块负责"统计指标"和"生成报告"
    - 职责分离，策略模块不需要理解报告需求
    """

    def __init__(
        self,
        # ── 基础信息 ──
        session_id: str,         # 回测会话ID
                                 # 业务含义：唯一标识一次回测运行
                                 # 用途：缓存key、报告页面路由参数

        stock_code: str,         # 股票代码
                                 # 业务含义：回测的是哪只股票
                                 # 用途：报告页面标题展示"回测标的：000001.SZ"

        strategy_id: int,        # 策略ID
                                 # 业务含义：用的是哪个策略
                                 # 用途：报告页面展示策略信息

        strategy_name: str,      # 策略名称
                                 # 业务含义：策略的人类可读名称
                                 # 用途：报告页面标题展示，用户认名字不认ID

        account_id: int,         # 虚拟账户ID
                                 # 业务含义：用的哪个虚拟账户
                                 # 用途：报告展示账户信息

        timeframe: str,          # 时间间隔
                                 # 业务含义：回测的K线周期
                                 # 用途：报告展示"回测频率：日线"

        start_date: str,         # 起始日期
                                 # 业务含义：回测从哪天开始
                                 # 用途：报告展示设置、图表时间轴起点

        end_date: str,           # 结束日期
                                 # 业务含义：回测到哪天结束
                                 # 用途：报告展示设置、图表时间轴终点

        total_bars: int,         # 总bar数
                                 # 业务含义：回测覆盖了多少个交易时段
                                 # 用途：报告展示"共261个交易日"

        time_elapsed: float,     # 回测耗时（秒）
                                 # 业务含义：策略跑了多久
                                 # 用途：报告展示"耗时 2.3s"

        # ── 逐bar明细 ──
        bars: list,              # 每根bar的完整记录 [BarRecord]
                                 # ★ 所有指标计算的原始数据源 ★
                                 # 业务含义：回测过程中每个时间点的完整快照
                                 # 用途：计算所有指标、生成所有图表、填充所有表格
    ):
        self.session_id = session_id
        self.stock_code = stock_code
        self.strategy_id = strategy_id
        self.strategy_name = strategy_name
        self.account_id = account_id
        self.timeframe = timeframe
        self.start_date = start_date
        self.end_date = end_date
        self.total_bars = total_bars
        self.time_elapsed = time_elapsed
        self.bars = bars


# ============================================================
# Mock 数据生成
# 模拟一次完整的回测运行，生成逻辑自洽的数据
# ============================================================

def _generate_trading_days(start: str, end: str) -> list[str]:
    """
    生成交易日期列表（跳过周末）。
    
    业务含义：A股市场只在周一到周五交易，回测只覆盖交易日。
    这是一个简化版，真实场景需考虑节假日。
    """
    start_dt = date.fromisoformat(start)
    end_dt = date.fromisoformat(end)
    days = []
    current = start_dt
    while current <= end_dt:
        # 0=Monday, 4=Friday, 跳过周末
        if current.weekday() <= 4:
            days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _generate_price_series(
    trading_days: list[str],
    start_price: float = 11.00,
) -> list[dict]:
    """
    生成模拟K线价格序列。
    
    业务含义：模拟000001.SZ平安银行2024年全年日线走势。
    通过预定义的关键价格节点插值生成，确保走势有趋势和波动，
    而不是纯随机——这样回测结果才有意义。
    
    价格走势设计：
    11.00(年初) → 9.80(2月底部) → 11.10(3月反弹) → 11.50(4月)
    → 10.80(6月回调) → 12.80(8月高点) → 11.40(9月回调) → 13.00(11月) → 12.60(年末)
    """
    # 关键价格节点：(月份索引, 目标价格)
    # 月份从0开始，0=1月，1=2月...
    key_points = [
        (0, 11.00),   # 年初
        (1.8, 9.80),  # 2月底部
        (2.8, 11.10), # 3月反弹
        (3.5, 11.50), # 4月
        (5.5, 10.80), # 6月回调
        (7.5, 12.80), # 8月高点
        (8.5, 11.40), # 9月回调
        (10.5, 13.00),# 11月新高
        (11.5, 12.60),# 年末
    ]

    total_days = len(trading_days)
    bars = []
    random.seed(42)

    for i, day in enumerate(trading_days):
        # 计算当前月份位置（0~11.99）
        month_pos = i / total_days * 12

        # 在关键节点之间线性插值得到基准价格
        base_price = start_price
        for j in range(len(key_points) - 1):
            m1, p1 = key_points[j]
            m2, p2 = key_points[j + 1]
            if m1 <= month_pos < m2:
                ratio = (month_pos - m1) / (m2 - m1)
                base_price = p1 + (p2 - p1) * ratio
                break
        else:
            base_price = key_points[-1][1]

        # 添加小幅随机波动，让K线更真实
        noise = random.gauss(0, 0.05)
        close = round(base_price + noise, 2)

        # 生成OHLC：基于收盘价上下波动
        change = random.gauss(0, 0.08)
        open_price = round(close - change, 2)
        high = round(max(open_price, close) + abs(random.gauss(0, 0.06)), 2)
        low = round(min(open_price, close) - abs(random.gauss(0, 0.06)), 2)
        volume = int(random.gauss(50000000, 10000000))
        amount = round(close * volume, 2)

        bars.append({
            "time": day,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": max(volume, 0),
            "amount": amount,
            "base_price": base_price,
        })

    return bars


def _generate_benchmark_series(
    trading_days: list[str],
    start_price: float = 3300.0,
) -> dict[str, float]:
    """
    生成基准指数（如沪深300）的收盘价序列。
    
    业务含义：模拟市场基准走势，用于和策略收益对比。
    基准走势比个股平缓，波动更小。
    
    用途：
    - 计算基准收益率
    - 计算Alpha、Beta、信息率
    - 策略vs基准收益对比图
    """
    random.seed(88)
    benchmark = {}
    price = start_price

    for day in trading_days:
        # 日涨幅在 -1.5% ~ +1.5% 之间，波动比个股小
        daily_return = random.gauss(0.0002, 0.008)
        price = round(price * (1 + daily_return), 2)
        benchmark[day] = price

    return benchmark


async def run_backtest_mock(
    stock_code: str,
    strategy_id: int,
    account_id: int,
    timeframe: str,
    start_date: str,
    end_date: str,
) -> BacktestResult:
    """
    模拟策略模块的 run_backtest 方法。

    业务含义：模拟一次完整的回测运行。按照策略逻辑在历史K线上逐bar求值，
    触发信号时执行模拟撮合，记录每根bar的完整状态。

    未来替换为真实调用：
        from strategy_engine.service import run_backtest
        result = await run_backtest(stock_code, strategy_id, account_id, timeframe, start_date, end_date)

    参数与配置栏一一对应，原样传入：
        stock_code:   用户选的股票代码，如 "000001.SZ"
        strategy_id:  用户选的策略ID
        account_id:   用户选的虚拟账户ID
        timeframe:    用户选的时间间隔，如 "1d"
        start_date:   用户选的起始日期
        end_date:     用户选的结束日期
    """
    # 生成交易日历
    trading_days = _generate_trading_days(start_date, end_date)
    if not trading_days:
        return BacktestResult(
            session_id="mock_0",
            stock_code=stock_code,
            strategy_id=strategy_id,
            strategy_name="模拟策略",
            account_id=account_id,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            total_bars=0,
            time_elapsed=0.0,
            bars=[],
        )

    # 生成K线行情
    kline_bars = _generate_price_series(trading_days)

    # 生成基准价格
    benchmark_prices = _generate_benchmark_series(trading_days)

    # 策略名称映射（模拟策略模块的策略配置）
    strategy_names = {
        1: "双均线交叉",
        2: "RSI超买超卖",
        3: "布林带突破",
        4: "MACD金叉死叉",
    }

    # 虚拟账户配置（模拟账户模块的账户信息）
    account_configs = {
        1: {"initial_capital": 1000000.0, "commission_rate": 0.001},
        2: {"initial_capital": 500000.0,  "commission_rate": 0.001},
        3: {"initial_capital": 2000000.0, "commission_rate": 0.0008},
    }
    account_config = account_configs.get(account_id, account_configs[1])
    initial_capital = account_config["initial_capital"]
    commission_rate = account_config["commission_rate"]

    # 定义买卖信号触发点（模拟策略求值结果）
    # (bar索引, "buy"/"sell", 触发原因)
    # 这些信号放在价格走势的关键拐点上，模拟真实策略行为
    signal_points = {}

    # 找到关键的局部低点作为买入点，局部高点作为卖出点
    # 简化处理：手动指定bar索引，确保逻辑自洽
    total_days = len(trading_days)
    buy_points = [
        int(total_days * 0.05),   # 2月初，价格底部区域
        int(total_days * 0.32),   # 4月中，回调后
        int(total_days * 0.48),   # 6月初，回调底部
        int(total_days * 0.72),   # 9月初，回调底部
        int(total_days * 0.83),   # 10月中，反弹启动
    ]
    sell_points = [
        int(total_days * 0.18),   # 3月中，反弹高点
        int(total_days * 0.40),   # 5月底，上涨乏力
        int(total_days * 0.65),   # 8月中，高点
        int(total_days * 0.77),   # 9月底，继续下跌
        int(total_days * 0.92),   # 11月底，高点
    ]

    signal_reasons_buy = ["均线金叉", "RSI超卖反弹", "布林带下轨支撑", "MACD金叉", "KDJ金叉"]
    signal_reasons_sell = ["均线死叉", "RSI超买回落", "布林带上轨突破", "MACD死叉", "KDJ超买"]

    for i, idx in enumerate(buy_points):
        if idx < total_days:
            signal_points[idx] = ("buy", signal_reasons_buy[i])
    for i, idx in enumerate(sell_points):
        if idx < total_days:
            signal_points[idx] = ("sell", signal_reasons_sell[i])

    # ── 逐bar模拟回测 ──
    cash = initial_capital       # 当前现金余额
    position_qty = 0             # 当前持仓数量（股）
    position_cost = 0.0          # 持仓成本价（买入均价）
    bars_result = []             # 逐bar记录
    log_entries_global = []      # 全局日志收集

    # 配对追踪：记录最近一次买入的价格和手续费，用于计算卖出时的盈亏
    last_buy_price = 0.0
    last_buy_commission = 0.0
    last_buy_qty = 0

    for i, kbar in enumerate(kline_bars):
        day_orders = []          # 当日订单
        day_logs = []            # 当日日志
        signal = None
        signal_reason = None

        # 检查是否有信号
        if i in signal_points:
            signal, signal_reason = signal_points[i]
            current_price = kbar["close"]

            if signal == "buy" and position_qty == 0:
                # 买入：用可用资金的30%买入（简化仓位管理）
                # 真实场景中由策略模块内部的仓位管理决定
                buy_amount = cash * 0.3
                commission = round(buy_amount * commission_rate, 2)

                if buy_amount > commission:
                    # 扣除手续费后计算可买股数（100股整数倍）
                    available = buy_amount - commission
                    qty = int(available / current_price / 100) * 100

                    if qty > 0:
                        actual_amount = round(qty * current_price, 2)
                        actual_commission = round(actual_amount * commission_rate, 2)

                        # 执行买入
                        cash -= (actual_amount + actual_commission)
                        position_qty = qty
                        position_cost = current_price

                        # 记录买入成本，用于后续卖出计算盈亏
                        last_buy_price = current_price
                        last_buy_commission = actual_commission
                        last_buy_qty = qty

                        order = OrderRecord(
                            time=kbar["time"],
                            side="buy",
                            price=current_price,
                            quantity=qty,
                            amount=actual_amount,
                            commission=actual_commission,
                            pnl=0.0,  # 买入时无盈亏
                            signal=signal_reason,
                        )
                        day_orders.append(order)
                        day_logs.append(f"[TRADE] 买入 {stock_code} {qty}股 @{current_price}，手续费{actual_commission}")

            elif signal == "sell" and position_qty > 0:
                # 卖出：全部卖出
                sell_amount = round(position_qty * current_price, 2)
                commission = round(sell_amount * commission_rate, 2)

                # 计算盈亏 = (卖出价 - 买入价) × 数量 - 买入手续费 - 卖出手续费
                pnl = round(
                    (current_price - last_buy_price) * position_qty
                    - last_buy_commission
                    - commission,
                    2
                )

                # 执行卖出
                cash += (sell_amount - commission)

                order = OrderRecord(
                    time=kbar["time"],
                    side="sell",
                    price=current_price,
                    quantity=position_qty,
                    amount=sell_amount,
                    commission=commission,
                    pnl=pnl,
                    signal=signal_reason,
                )
                day_orders.append(order)

                pnl_sign = "+" if pnl >= 0 else ""
                day_logs.append(f"[TRADE] 卖出 {stock_code} {position_qty}股 @{current_price}，盈亏{pnl_sign}{pnl}，手续费{commission}")

                position_qty = 0
                position_cost = 0.0

            elif signal == "buy" and position_qty > 0:
                day_logs.append(f"[WARN] 已持有仓位，忽略买入信号：{signal_reason}")
            elif signal == "sell" and position_qty == 0:
                day_logs.append(f"[WARN] 无持仓，忽略卖出信号：{signal_reason}")

        # 计算当日账户状态
        if position_qty > 0:
            market_value = round(position_qty * kbar["close"], 2)
            floating_pnl = round(market_value - (position_cost * position_qty), 2)
            positions = [PositionRecord(
                stock_code=stock_code,
                quantity=position_qty,
                cost_price=position_cost,
                current_price=kbar["close"],
                market_value=market_value,
                floating_pnl=floating_pnl,
            )]
        else:
            market_value = 0.0
            positions = []

        total_assets = round(cash + market_value, 2)

        # 第一天加启动日志
        if i == 0:
            day_logs.insert(0, f"[INFO] 回测启动，策略：{strategy_names.get(strategy_id, '未知')}，股票：{stock_code}，初始资金：¥{initial_capital:,.0f}")

        # 最后一天加结束日志
        if i == len(kline_bars) - 1:
            day_logs.append(f"[INFO] 回测结束，共{len(kline_bars)}个交易日")

        bar = BarRecord(
            time=kbar["time"],
            open=kbar["open"],
            high=kbar["high"],
            low=kbar["low"],
            close=kbar["close"],
            volume=kbar["volume"],
            amount=kbar["amount"],
            benchmark_close=benchmark_prices.get(kbar["time"], 0.0),
            signal=signal,
            signal_reason=signal_reason,
            orders=day_orders,
            positions=positions,
            cash=round(cash, 2),
            total_assets=total_assets,
            log_entries=day_logs,
        )
        bars_result.append(bar)

    return BacktestResult(
        session_id=f"mock_{strategy_id}_{stock_code}",
        stock_code=stock_code,
        strategy_id=strategy_id,
        strategy_name=strategy_names.get(strategy_id, "模拟策略"),
        account_id=account_id,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        total_bars=len(bars_result),
        time_elapsed=round(len(bars_result) * 0.01, 2),  # 模拟耗时
        bars=bars_result,
    )
