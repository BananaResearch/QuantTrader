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
    """
    搜索股票（模糊匹配代码/名称/拼音）

    为什么有这个方法：
        - 业务角度：用户在回测配置栏输入股票时，需要快速找到目标股票。
          A股有数千只，不可能手动输入完整代码，必须提供搜索能力。
          支持拼音首字母搜索是中文场景下的刚需（如输入"GZMT"找到"贵州茅台"）。
        - 技术角度：前端 StockSearchInput 组件在用户输入时（300ms 防抖）
          调用此接口获取候选列表，渲染为可点击的下拉选项。当前为 stub，
          正式实现时需要对接股票基础数据库或行情数据源，并考虑缓存和索引优化。

    参数：
        keyword (str):
            - 技术含义：用户输入的搜索关键词字符串，会转为小写后与候选数据的
              code/name/pinyin 字段做子串包含匹配。
            - 业务含义：用户可能输入的任意片段，例如股票代码片段"000001"、
              股票名称片段"茅台"、或拼音首字母片段"GZMT"。
        limit (int, 默认10):
            - 技术含义：返回结果的最大数量，用于防止前端渲染过多选项导致卡顿。
            - 业务含义：下拉框最多展示的候选条数，10 条足够用户快速定位目标。

    返回值：
        list[StockOption]:
            - 技术含义：StockOption 模型的列表，每项包含 code（股票代码）、
              name（股票名称）、pinyin（拼音首字母）三个字段。
            - 业务含义：模糊匹配命中的股票候选列表，前端渲染为搜索下拉选项，
              用户点击某项后，该股票代码被填入回测配置。
    """
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
    """
    获取可用策略列表

    为什么有这个方法：
        - 业务角度：回测的核心是"用历史数据验证策略"，用户必须选择一个策略才能启动回测。
          策略列表让用户看到系统中有哪些可用的量化策略及其简要描述，辅助决策。
        - 技术角度：前端配置栏的策略下拉框在组件挂载时调用此接口填充选项。
          策略数据来源于策略引擎模块（strategy_engine），正式实现时需要跨模块调用
          策略引擎的接口或直接查询策略表。当前 stub 返回 4 个典型策略的 mock 数据。

    参数：无
        策略列表是全局的，不需要过滤参数。未来可扩展 category 等筛选条件。

    返回值：
        list[StrategyOption]:
            - 技术含义：StrategyOption 模型的列表，每项包含 id（策略唯一标识）、
              name（策略名称）、description（策略描述，可选）。
            - 业务含义：系统中所有可用于回测的量化策略。用户选择某项后，
              strategy_id 会被传入 start_replay 接口，回测引擎据此加载对应策略逻辑。
    """
    return [
        StrategyOption(id=1, name="双均线交叉", description="短期均线上穿长期均线买入"),
        StrategyOption(id=2, name="RSI超买超卖", description="RSI低于30买入，高于70卖出"),
        StrategyOption(id=3, name="布林带突破", description="价格突破布林带上下轨"),
        StrategyOption(id=4, name="MACD金叉死叉", description="MACD金叉买入，死叉卖出"),
    ]


async def list_virtual_accounts() -> list[VirtualAccountOption]:
    """
    获取虚拟账户列表

    为什么有这个方法：
        - 业务角度：回测不使用真实资金，而是在虚拟账户中模拟交易。不同虚拟账户可以
          配置不同的初始资金、手续费率等参数，模拟不同资金规模下的策略表现。
          例如"激进账户"资金少、仓位重，"保守账户"资金多、仓位轻。
        - 技术角度：前端配置栏的虚拟账户下拉框在组件挂载时调用此接口。
          正式实现时需要对接账户管理模块或查询虚拟账户表，返回账户 ID、名称和初始资金。
          账户的完整配置（手续费率、滑点等）在 start_replay 时通过 account_id 关联获取。

    参数：无
        虚拟账户列表属于当前用户，后续可通过 user_id 过滤。

    返回值：
        list[VirtualAccountOption]:
            - 技术含义：VirtualAccountOption 模型的列表，每项包含 id（账户唯一标识）、
              name（账户名称）、initial_capital（初始资金，浮点数）。
            - 业务含义：用户可选择的虚拟交易账户。选择后 account_id 传入 start_replay，
              回测引擎会在该账户的初始资金基础上模拟所有交易操作（买入扣款、卖出回款、
              扣手续费、计算持仓和盈亏）。
    """
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
    """
    启动回测会话

    为什么有这个方法：
        - 业务角度：这是整个历史回放模块的核心入口。用户配置好股票、策略、账户、
          时间范围后，点击"开始回测"触发此方法。回测引擎会在指定的时间范围内，
          按照指定的时间间隔，用历史行情数据逐根驱动策略运算，产生交易信号，
          在虚拟账户中模拟执行，最终生成完整的回测结果。
        - 技术角度：此方法创建一个 ReplaySession 实体，持久化回测配置和状态，
          返回 session_id 供后续所有数据查询接口使用。正式实现时需要：
          1) 向 api_data 模块请求历史 K 线数据；
          2) 向 strategy_engine 模块加载策略逻辑；
          3) 初始化虚拟账户状态；
          4) 启动异步回测引擎（可能用 Celery 等任务队列）；
          5) 通过 WebSocket 推送回测进度。

    参数：
        stock_code (str):
            - 技术含义：股票代码字符串，如 "000001.SZ"，用于向行情数据模块
              请求该股票的历史 K 线数据。
            - 业务含义：回测的目标标的，即"用哪只股票的历史数据来验证策略"。
        strategy_id (int):
            - 技术含义：策略的唯一主键 ID，用于向策略引擎模块查询策略定义
              和加载策略执行逻辑。
            - 业务含义：用户选择要回测的量化策略，如"双均线交叉"策略。
        account_id (int):
            - 技术含义：虚拟账户的唯一主键 ID，用于加载账户配置（初始资金、
              手续费率、滑点设置等）。
            - 业务含义：回测使用的虚拟交易账户，决定了模拟交易的初始资金和成本模型。
        timeframe (str):
            - 技术含义：K 线周期字符串，取值为 "1m"/"5m"/"15m"/"30m"/"1h"/"4h"/"1d"，
              同时决定了拉取 K 线的周期和策略每轮计算的触发频率。
            - 业务含义：回测的时间颗粒度。例如 "1d" 表示每天一根 K 线，策略每天
              计算一次信号；"5m" 表示每 5 分钟一根 K 线，策略每 5 分钟计算一次。
              颗粒度越细，回测精度越高，但计算量和数据量也越大。
        start_date (str):
            - 技术含义：回测起始日期，格式 "YYYY-MM-DD"，用于限定 K 线数据查询的
              时间范围下界。
            - 业务含义：回测的起始时间，即"从哪个时间点开始用历史数据驱动策略"。
        end_date (str):
            - 技术含义：回测结束日期，格式 "YYYY-MM-DD"，用于限定 K 线数据查询的
              时间范围上界。
            - 业务含义：回测的结束时间，即"到哪个时间点停止回测"。

    返回值：
        ReplaySession:
            - 技术含义：ReplaySession 模型实例，包含 session_id（会话唯一标识）、
              所有传入的配置参数、status（会话当前状态枚举）、current_index（当前
              已处理到的 K 线索引）、total_bars（K 线总根数）。
            - 业务含义：回测会话对象，session_id 是后续查询 K 线、信号、交易记录、
              指标、资金曲线等所有数据的唯一凭证。status 告知前端回测当前处于
              运行中/已暂停/已完成/异常等状态，用于控制播放器的 UI 展示。
    """
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
    """
    获取回测会话状态

    为什么有这个方法：
        - 业务角度：用户可能离开回测页面后再回来，需要恢复之前的回测状态。
          或者在回测运行过程中，前端需要轮询获取最新进度（当前处理到第几根 K 线）。
          也用于页面初始化时判断是否有正在进行的回测会话。
        - 技术角度：通过 session_id 查询回测会话实体的当前状态，包括运行状态和
          进度信息。正式实现时从数据库或缓存中读取。前端可在以下场景调用：
          1) 页面加载时恢复会话；
          2) 定时轮询更新进度条；
          3) WebSocket 断连后降级为轮询。

    参数：
        session_id (int):
            - 技术含义：回测会话的唯一主键 ID，由 start_replay 创建时生成。
            - 业务含义：要查询的回测会话标识，对应一次具体的回测运行实例。

    返回值：
        ReplaySession:
            - 技术含义：完整的 ReplaySession 模型实例，包含会话配置和实时状态。
            - 业务含义：该回测会话的最新状态快照。前端据此更新播放控制条
              （播放/暂停按钮、进度条位置、状态标签）。
    """
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
    """
    控制回测执行（暂停/继续/停止）

    为什么有这个方法：
        - 业务角度：回测可能持续很长时间（尤其是分钟级 K 线），用户需要随时
          暂停观察当前状态、继续执行、或提前终止不满意的回测。这类似于视频播放器
          的暂停/播放/停止控制，是回放交互体验的核心。
        - 技术角度：通过 action 参数控制回测引擎的状态机转换：
          running → paused（暂停）、paused → running（继续）、
          running/paused → completed（停止）。正式实现时需要向回测引擎进程
          发送控制信号（如通过 Redis 发布/订阅或任务队列），并更新数据库中的
          会话状态。

    参数：
        session_id (int):
            - 技术含义：要控制的回测会话唯一 ID。
            - 业务含义：对哪次回测执行控制操作。
        action (str):
            - 技术含义：控制动作字符串，取值为 "pause"（暂停）、"resume"（继续）、
              "stop"（停止）。对应 ReplayStatus 枚举的状态转换。
            - 业务含义：
              - pause：暂停回测，K 线停止推进，保留当前进度，可随时继续；
              - resume：从暂停处继续回测，K 线恢复推进；
              - stop：终止回测，标记为已完成，不再可继续，保留已产生的所有数据。

    返回值：
        ReplaySession:
            - 技术含义：更新后的 ReplaySession 模型实例，status 字段反映控制操作
              后的最新状态。
            - 业务含义：控制操作后的会话状态，前端据此更新播放控制条的 UI
              （按钮启用/禁用、状态标签文字）。
    """
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
    """
    设置回测播放速度

    为什么有这个方法：
        - 业务角度：回测默认 1x 速度（每秒推进一根 K 线），对于日线级别 240 根 K 线
          需要等 4 分钟。用户可能希望加速浏览（4x 只需 1 分钟），或对关键区间
          减速仔细观察。速度控制是回放体验的重要交互功能。
        - 技术角度：speed 参数影响回测引擎向 WebSocket 推送 K 线数据的频率。
          1x = 每秒 1 根，2x = 每秒 2 根，以此类推。正式实现时需要通知回测引擎
          进程调整推送频率。

    参数：
        session_id (int):
            - 技术含义：要调速的回测会话唯一 ID。
            - 业务含义：对哪次回测调整播放速度。
        speed (int):
            - 技术含义：速度倍率整数，取值为 1/2/4/8，表示每秒推进的 K 线根数。
            - 业务含义：回测播放速度倍率。1x 为正常速度，8x 为 8 倍速快进。

    返回值：
        ReplayProgress:
            - 技术含义：ReplayProgress 模型实例，包含 current_index（当前进度索引）、
              total_bars（K 线总根数）、speed（确认后的速度倍率）、status（会话状态）。
            - 业务含义：调速后的回测进度快照。前端据此更新速度按钮的高亮状态和
              进度条位置。
    """
    return ReplayProgress(
        current_index=120,
        total_bars=240,
        speed=speed,
        status=ReplayStatus.RUNNING,
    )


async def get_kline_data(session_id: int) -> list[KlineBar]:
    """
    获取回测K线数据

    为什么有这个方法：
        - 业务角度：K 线图是回测页面的核心可视化，用户通过 K 线图观察历史价格走势
          和策略的买卖信号位置（标记在 K 线上）。没有 K 线数据，回测就失去了
          最直观的图形化验证手段。
        - 技术角度：前端 ReplayChart 组件使用 lightweight-charts 渲染 K 线图，
          需要标准 OHLCV 格式的数据。当前 stub 用随机数生成 240 根模拟 K 线
          （含确定性种子保证可复现），正式实现时从 api_data 模块获取真实历史数据，
          或从本模块数据库读取回测时已缓存的数据。

    参数：
        session_id (int):
            - 技术含义：回测会话唯一 ID，用于关联查询该会话对应的股票和时间范围的
              K 线数据。
            - 业务含义：获取哪次回测的 K 线数据，隐含了股票代码、时间范围、
              K 线周期等上下文。

    返回值：
        list[KlineBar]:
            - 技术含义：KlineBar 模型的列表，每项包含 time（时间戳字符串）、
              open/high/low/close（OHLC 价格，浮点数）、volume（成交量，浮点数）。
              数据按时间升序排列，与 lightweight-charts 的 setData 接口要求一致。
            - 业务含义：回测时间范围内的完整 K 线序列，前端据此渲染 K 线图。
              买卖信号标记的时间字段会与 K 线的 time 字段对齐，精确定位在对应的
              K 线上方/下方。
    """
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
    """
    获取交易信号

    为什么有这个方法：
        - 业务角度：交易信号是策略引擎在回测过程中产生的买卖决策，是"策略怎么想"
          的记录。与交易记录不同，信号是策略的原始输出（可能包含未执行的信号），
          用于在 K 线图上标记买卖点位，让用户直观看到策略在哪些时刻发出了什么信号。
        - 技术角度：前端 ReplayChart 组件使用 lightweight-charts 的 markers 功能
          在 K 线图上渲染买入箭头（红色向上）和卖出箭头（绿色向下），需要
          time/side/price/signal 字段。当前 stub 返回 6 个跨不同策略类型的模拟信号，
          正式实现时由回测引擎在运行过程中生成并存储。

    参数：
        session_id (int):
            - 技术含义：回测会话唯一 ID，用于关联查询该回测产生的交易信号。
            - 业务含义：获取哪次回测的策略信号记录。

    返回值：
        list[TradeSignal]:
            - 技术含义：TradeSignal 模型的列表，每项包含 time（信号时间，与 K 线
              time 对齐）、side（方向枚举 buy/sell）、price（信号价格）、
              quantity（信号数量）、signal（信号描述字符串，如"均线金叉"）。
            - 业务含义：策略在回测期间产生的所有买卖信号。前端将每条信号渲染为
              K 线图上的标记点，买入信号显示为红色向上箭头（K 线下方），
              卖出信号显示为绿色向下箭头（K 线上方），附带信号名称文字。
    """
    return [
        TradeSignal(time="2024-02-15", side=TradeSide.BUY, price=16.20, quantity=1000, signal="均线金叉"),
        TradeSignal(time="2024-04-10", side=TradeSide.SELL, price=17.80, quantity=1000, signal="均线死叉"),
        TradeSignal(time="2024-06-05", side=TradeSide.BUY, price=15.90, quantity=1500, signal="RSI超卖"),
        TradeSignal(time="2024-08-20", side=TradeSide.SELL, price=18.50, quantity=1500, signal="RSI超买"),
        TradeSignal(time="2024-10-12", side=TradeSide.BUY, price=16.80, quantity=1200, signal="布林带下轨"),
        TradeSignal(time="2024-11-28", side=TradeSide.SELL, price=19.10, quantity=1200, signal="布林带上轨"),
    ]


async def get_trade_records(session_id: int) -> list[TradeRecord]:
    """
    获取交易记录

    为什么有这个方法：
        - 业务角度：交易记录是回测的核心产出之一，记录了虚拟账户在回测期间的
          每一笔实际成交。与交易信号不同，交易记录包含了完整的成交信息（金额、
          盈亏、手续费），是评估策略表现的基础数据。用户通过交易记录表逐笔
          审查策略的每笔交易是否合理。
        - 技术角度：前端 TradeLog 组件渲染为 9 列数据表格，需要 id/time/side/
          stock_code/price/quantity/amount/pnl/commission/signal 字段。
          当前 stub 返回 6 笔配对交易（3 组买入→卖出），正式实现时由回测引擎
          在模拟执行过程中生成，包含完整的资金计算逻辑。

    参数：
        session_id (int):
            - 技术含义：回测会话唯一 ID，用于关联查询该回测的交易记录。
            - 业务含义：获取哪次回测的成交明细。

    返回值：
        list[TradeRecord]:
            - 技术含义：TradeRecord 模型的列表，每项包含 id（记录唯一 ID）、
              time（成交时间）、side（方向枚举 buy/sell）、stock_code（股票代码）、
              price（成交价格）、quantity（成交数量）、amount（成交金额 = price × quantity）、
              pnl（该笔交易盈亏，买入时为 0，卖出时计算卖出金额 - 对应买入金额 - 手续费）、
              commission（手续费）、signal（触发信号描述）。
            - 业务含义：虚拟账户在回测期间的完整成交流水。前端以此渲染交易记录表，
              每行的盈亏列用红色/绿色标注正负值（中国惯例红涨绿跌），
              方向列用标签标注买入/卖出。
    """
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
    """
    获取回测指标

    为什么有这个方法：
        - 业务角度：回测指标是量化策略评估的核心依据，回答"这个策略好不好"的问题。
          8 个指标从不同维度评估策略表现：
          - 总收益率/年化收益：衡量盈利能力；
          - 最大回撤：衡量风险控制能力（最坏情况下亏多少）；
          - 夏普比率：衡量风险调整后收益（每承担 1 单位风险能获得多少超额回报）；
          - 胜率/盈亏比：衡量交易的胜面和赔率；
          - 交易次数/总盈亏：衡量策略活跃度和绝对盈亏金额。
        - 技术角度：前端 MetricsPanel 组件渲染为 8 项指标面板，每项用涨跌色
          （红/绿）标注正负值。当前 stub 返回一组典型正收益的指标数据，
          正式实现时由回测引擎在运行结束后根据交易记录和资金曲线统计计算。

    参数：
        session_id (int):
            - 技术含义：回测会话唯一 ID，用于关联查询该回测的统计指标。
            - 业务含义：获取哪次回测的策略评估指标。

    返回值：
        ReplayMetrics:
            - 技术含义：ReplayMetrics 模型实例，包含 8 个浮点数字段：
              total_return（总收益率%）、annual_return（年化收益率%）、
              max_drawdown（最大回撤%，负值）、sharpe_ratio（夏普比率）、
              win_rate（胜率%）、profit_loss_ratio（盈亏比）、
              trade_count（交易次数）、total_pnl（总盈亏金额）。
            - 业务含义：策略回测的完整评估指标。前端据此判断策略好坏：
              收益率为正显示红色（涨），为负显示绿色（跌）；
              夏普比率 > 1 标注"优秀"，0.5~1 标注"良好"；
              胜率 > 50% 显示红色，< 50% 显示绿色。
    """
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
    """
    获取资金曲线

    为什么有这个方法：
        - 业务角度：资金曲线是回测结果最直观的可视化，展示账户净值随时间的变化趋势。
          与单纯的收益率数字相比，曲线能暴露策略的波动特征——平稳增长还是大起大落、
          回撤持续了多久、恢复速度如何。回撤子图（红色区域）帮助用户识别策略的
          风险时段，是风控评估的重要依据。
        - 技术角度：前端 EquityCurve 组件使用 ECharts 渲染双轴折线图：
          左轴为净值曲线（蓝色面积图），右轴为回撤百分比（红色面积图）。
          当前 stub 用确定性随机数生成 240 个数据点（模拟一年日频数据），
          正式实现时由回测引擎逐根 K 线推进时计算并记录。

    参数：
        session_id (int):
            - 技术含义：回测会话唯一 ID，用于关联查询该回测的资金曲线数据。
            - 业务含义：获取哪次回测的净值变化序列。

    返回值：
        list[EquityPoint]:
            - 技术含义：EquityPoint 模型的列表，每项包含 time（时间，与 K 线对齐）、
              equity（账户净值，浮点数）、drawdown（当前回撤百分比，负值）。
              数据按时间升序排列，与 ECharts 的 xAxis.category + series.line 对应。
            - 业务含义：回测期间账户净值和回撤的时间序列。净值曲线从初始资金开始，
              随每笔交易盈亏波动；回撤曲线记录每个时点相对历史最高净值的回退幅度，
              其最小值即为"最大回撤"。
    """
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
