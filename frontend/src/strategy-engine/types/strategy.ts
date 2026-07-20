/**
 * strategy-engine 模块私有类型定义。
 *
 * 字段与后端 strategy_engine/schemas.py 严格对齐。
 *
 * 变更说明（strategy-engine-params-redesign）：
 * - 删除 StrategyType（strategy_type 字段已移除）
 * - 新增 ParamFieldType / ParamField / ParamSchema（参数 Schema）
 * - 新增 RuntimeMode / DataFrequency / RuntimeConfigTemplate（运行配置模板）
 * - Strategy / StrategyCreateInput / StrategyUpdateInput 新增字段、删除 strategy_type
 * - DryRunRequestInput 签名变更（template_id + override）
 */

// ============================================================
// 策略状态
// ============================================================

/** 策略状态机：草稿 → 启用 → 归档 */
export type StrategyStatus = 'draft' | 'active' | 'archived'

// ============================================================
// 参数 Schema（strategy-param-schema spec）
// ============================================================

/** 参数字段类型 */
export type ParamFieldType =
  | 'int'
  | 'float'
  | 'string'
  | 'bool'
  | 'select'
  | 'stock_code'
  | 'list'

/** 单个参数字段定义 */
export interface ParamField {
  key: string
  type: ParamFieldType
  label: string
  description?: string
  default?: unknown
  min?: number
  max?: number
  /** select 类型选项 */
  options?: { label: string; value: string | number }[]
  /** list 类型元素类型 */
  item_type?: ParamFieldType
  /** 分组名称（UI 折叠） */
  group?: string
  required?: boolean
}

/** 参数 Schema 容器 */
export interface ParamSchema {
  fields: ParamField[]
}

// ============================================================
// 运行配置模板（runtime-config-template spec）
// ============================================================

/** 运行配置模式 */
export type RuntimeMode = 'backtest' | 'paper' | 'live'

/** 数据频率 */
export type DataFrequency = 'daily' | '1min' | '5min' | '15min' | '30min' | '60min'

/** 运行配置模板 */
export interface RuntimeConfigTemplate {
  id: number
  name: string
  description?: string | null
  mode: RuntimeMode
  universe: string[]
  start_date?: string | null  // YYYY-MM-DD
  end_date?: string | null
  initial_capital: string  // Decimal 序列化为字符串
  frequency: DataFrequency
  slippage: string
  commission: string
  is_default: boolean
  created_at: string
  updated_at: string
}

/** 创建/更新运行配置模板请求 */
export interface RuntimeConfigTemplateCreate {
  name: string
  description?: string
  mode: RuntimeMode
  universe: string[]
  start_date?: string
  end_date?: string
  initial_capital?: number
  frequency?: DataFrequency
  slippage?: number
  commission?: number
}

// ============================================================
// 策略主档
// ============================================================

/**
 * 策略主档（与后端 StrategyResponse 对齐）
 *
 * 变更：删除 strategy_type，新增 param_schema / account_id
 */
export interface Strategy {
  id: number
  code: string
  name: string
  description?: string | null
  status: StrategyStatus
  version: string
  /** 当前生效的 Python 策略代码 */
  code_content?: string | null
  /** 参数 Schema 定义 */
  param_schema?: ParamSchema | null
  /** 基于 Schema 的参数值 */
  parameters?: Record<string, unknown> | null
  /** 实盘账户 ID（可空，弱引用） */
  account_id?: number | null
  tags?: string[] | null
  author?: string | null
  is_default: boolean
  created_at: string
  updated_at: string
}

/** 创建策略请求体（strategy_type 已删除） */
export interface StrategyCreateInput {
  code: string
  name: string
  description?: string
  status?: StrategyStatus
  version?: string
  code_content?: string | null
  param_schema?: ParamSchema | null
  parameters?: Record<string, unknown> | null
  account_id?: number | null
  tags?: string[]
  author?: string
  is_default?: boolean
}

/** 更新策略请求体（所有字段可选，strategy_type 已删除） */
export interface StrategyUpdateInput {
  name?: string
  description?: string
  status?: StrategyStatus
  version?: string
  code_content?: string | null
  param_schema?: ParamSchema | null
  parameters?: Record<string, unknown> | null
  account_id?: number | null
  tags?: string[]
  author?: string
  is_default?: boolean
}

/** 策略简化项（strategy_type 已从响应中删除） */
export interface StrategyOption {
  id: number
  name: string
  description?: string | null
}

/** 策略列表响应 */
export interface StrategyListResponse {
  items: Strategy[]
  total: number
}

// ============================================================
// 策略版本（strategy-version-compare spec）
// ============================================================

/** 策略版本（strategy_version 表） */
export interface StrategyVersion {
  id: number
  strategy_id: number
  version: string
  change_log?: string | null
  code_content?: string | null
  /** Schema 快照 */
  param_schema?: ParamSchema | null
  parameters?: Record<string, unknown> | null
  /** 运行配置快照（仅复现参考） */
  runtime_config_snapshot?: Record<string, unknown> | null
  status: string
  backtest_result?: Record<string, unknown> | null
  created_at: string
}

// ============================================================
// 校验与试运行
// ============================================================

export type ValidationSeverity = 'error' | 'warning'

export interface ValidationIssue {
  line?: number | null
  column?: number | null
  severity: ValidationSeverity
  /** 错误码：SYNTAX_ERROR / FORBIDDEN_IMPORT / MISSING_HOOK / LOAD_ERROR / RUNTIME_ERROR 等 */
  code: string
  message: string
}

export interface StrategyValidateResult {
  valid: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
}

export interface StrategyValidateRequest {
  code_content: string
  parameters?: Record<string, unknown> | null
}

/** dry-run 单 bar 简要 */
export interface DryRunBarSummary {
  time: string
  close: number
  total_assets: number
  signal: 'buy' | 'sell' | null
  orders_count: number
}

/** dry-run 响应 */
export interface DryRunResult {
  session_id: string
  total_bars: number
  time_elapsed: number
  final_capital: number
  total_return_pct: number
  bars: DryRunBarSummary[]
}

/**
 * dry-run 请求体（签名变更：template_id + override 替代硬编码字段）
 */
export interface DryRunRequestInput {
  template_id: number
  /** 临时覆盖字段（仅允许 universe/start_date/end_date/initial_capital/frequency/slippage/commission） */
  override?: Partial<RuntimeConfigTemplate> | null
  max_bars?: number
  /** 临时覆盖策略参数值 */
  parameters?: Record<string, unknown> | null
  /** 是否保存运行配置快照 */
  save_snapshot?: boolean
}

// ============================================================
// 策略模板（用于新建策略选择器）
// ============================================================

/** 内置策略模板项 */
export interface StrategyTemplateItem {
  code: string
  name: string
  description: string
  code_content: string
  param_schema?: ParamSchema | null
  parameters?: Record<string, unknown> | null
  /** 是否为空白模板 */
  is_blank: boolean
}

// ============================================================
// 统一响应
// ============================================================

export interface ApiResponse<T = unknown> {
  success: boolean
  data: T
  message?: string
  total?: number
}
