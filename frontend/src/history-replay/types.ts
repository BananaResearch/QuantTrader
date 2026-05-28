/** === 回测配置相关 === */

/** 股票搜索候选 */
export interface StockOption {
  code: string
  name: string
  pinyin: string
}

/** 策略选项 */
export interface StrategyOption {
  id: number
  name: string
  description?: string
}

/** 虚拟账户选项 */
export interface VirtualAccountOption {
  id: number
  name: string
  initial_capital: number
}

/** 时间间隔 */
export type TimeFrame = '1m' | '5m' | '15m' | '30m' | '1h' | '4h' | '1d'

/** 回测启动请求参数 */
export interface ReplayStartParams {
  stock_code: string
  strategy_id: number
  account_id: number
  timeframe: TimeFrame
  start_date: string
  end_date: string
}

/** === 回测运行时状态 === */

export type ReplayStatus = 'idle' | 'running' | 'paused' | 'completed' | 'error'

/** 回测会话 */
export interface ReplaySession {
  session_id: number
  stock_code: string
  strategy_id: number
  account_id: number
  timeframe: TimeFrame
  start_date: string
  end_date: string
  status: ReplayStatus
  current_index: number
  total_bars: number
}

/** === K线 & 行情数据 === */

export interface KlineBar {
  time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

/** === 交易信号 & 记录 === */

export type TradeSide = 'buy' | 'sell'

export interface TradeSignal {
  time: string
  side: TradeSide
  price: number
  quantity: number
  signal: string
}

export interface TradeRecord {
  id: number
  time: string
  side: TradeSide
  stock_code: string
  price: number
  quantity: number
  amount: number
  pnl: number
  commission: number
  signal: string
}

/** === 回测指标 === */

export interface ReplayMetrics {
  total_return: number
  annual_return: number
  max_drawdown: number
  sharpe_ratio: number
  win_rate: number
  profit_loss_ratio: number
  trade_count: number
  total_pnl: number
  /** 报告视图扩展指标 */
  benchmark_return?: number
  alpha?: number
  beta?: number
  sortino_ratio?: number
  information_ratio?: number
  strategy_volatility?: number
  benchmark_volatility?: number
}

/** === 资金曲线数据点 === */

export interface EquityPoint {
  time: string
  equity: number
  drawdown: number
}

/** === 报告视图：基准收益数据点 === */

export interface BenchmarkPoint {
  time: string
  /** 基准累计收益率（百分比） */
  return_pct: number
}

/** === 报告视图：策略收益数据点 === */

export interface StrategyReturnPoint {
  time: string
  /** 策略累计收益率（百分比） */
  return_pct: number
}

/** === 报告视图：每日盈亏数据点 === */

export interface DailyPnlPoint {
  time: string
  /** 当日盈亏金额 */
  pnl: number
  /** 当日买入金额 */
  buy_amount: number
  /** 当日卖出金额 */
  sell_amount: number
}

/** === 报告视图：每日持仓数据点 === */

export interface DailyPositionPoint {
  time: string
  /** 持仓数量 */
  quantity: number
  /** 持仓市值 */
  market_value: number
  /** 当日收益金额 */
  daily_pnl: number
  /** 当日收益率（百分比） */
  daily_return_pct: number
  /** 账户总资产 */
  total_equity: number
}

/** === 报告视图：日志条目 === */

export interface ReplayLogEntry {
  time: string
  level: 'info' | 'warn' | 'error'
  message: string
}

/** === 回测进度（播放控制用） === */

export interface ReplayProgress {
  current_index: number
  total_bars: number
  speed: 1 | 2 | 4 | 8
  status: ReplayStatus
}

/** === 报告视图 Tab === */

export type ReportTab =
  | 'overview'       // 收益概述
  | 'trades'         // 交易详情
  | 'daily_position' // 每日持仓&收益
  | 'logs'           // 日志输出
