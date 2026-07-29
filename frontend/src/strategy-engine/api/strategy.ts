/**
 * strategy-engine 模块的 API 请求函数。
 *
 * 与后端 `backend/strategy_engine/router.py` 路由严格对齐。
 *
 * 变更说明（strategy-engine-params-redesign）：
 * - 删除 strategy_type 过滤参数
 * - dry-run 签名变更（DryRunRequestInput）
 * - 新增 RuntimeConfigTemplate CRUD
 * - 新增策略模板列表
 */

import request from '@/common/utils/request'
import type {
  DryRunRequestInput,
  DryRunResult,
  RuntimeConfigTemplate,
  RuntimeConfigTemplateCreate,
  Strategy,
  StrategyCreateInput,
  StrategyOption,
  StrategyTemplateItem,
  StrategyUpdateInput,
  StrategyValidateRequest,
  StrategyValidateResult,
  StrategyVersion,
} from '../types/strategy'

// ============================================================
// 列表过滤参数（删除 strategy_type）
// ============================================================

export interface StrategyListParams {
  status?: string
  limit?: number
  offset?: number
}

// ============================================================
// 策略 CRUD
// ============================================================

export function getStrategies(params?: StrategyListParams) {
  return request.get<Strategy[]>('/strategy/list', { params })
}

export function getStrategy(id: number) {
  return request.get<Strategy>(`/strategy/${id}`)
}

export function createStrategy(data: StrategyCreateInput) {
  return request.post<Strategy>('/strategy/create', data)
}

export function updateStrategy(id: number, data: StrategyUpdateInput) {
  return request.put<Strategy>(`/strategy/${id}`, data)
}

export function deleteStrategy(id: number) {
  return request.delete<{ deleted_versions: number }>(`/strategy/${id}`)
}

// ============================================================
// 策略版本
// ============================================================

export function getStrategyVersions(strategyId: number, status?: string) {
  return request.get<StrategyVersion[]>(`/strategy/${strategyId}/versions`, {
    params: { status },
  })
}

export function createStrategyVersion(
  strategyId: number,
  data: Omit<StrategyVersion, 'id' | 'created_at' | 'strategy_id'> & { strategy_id?: number },
) {
  return request.post<StrategyVersion>(`/strategy/${strategyId}/versions`, data)
}

// ============================================================
// 简化列表 / 校验 / 试运行
// ============================================================

export function getStrategyOptions(status: 'active' | 'all' = 'active') {
  return request.get<StrategyOption[]>('/strategy/options/all', {
    params: { status },
  })
}

export function validateStrategyCode(payload: StrategyValidateRequest) {
  return request.post<StrategyValidateResult>('/strategy/validate', payload)
}

/**
 * 策略试运行（签名变更）
 * - 使用 template_id + override 替代硬编码 stock_code/start_date/end_date
 */
export function dryRunStrategy(id: number, payload: DryRunRequestInput) {
  return request.post<DryRunResult>(`/strategy/${id}/dry-run`, payload)
}

// ============================================================
// RuntimeConfigTemplate CRUD
// ============================================================

export function listRuntimeConfigs(mode?: string) {
  return request.get<RuntimeConfigTemplate[]>('/strategy/runtime-configs', {
    params: mode ? { mode } : undefined,
  })
}

export function createRuntimeConfig(data: RuntimeConfigTemplateCreate) {
  return request.post<RuntimeConfigTemplate>('/strategy/runtime-configs', data)
}

export function getRuntimeConfig(id: number) {
  return request.get<RuntimeConfigTemplate>(`/strategy/runtime-configs/${id}`)
}

export function updateRuntimeConfig(
  id: number,
  data: Partial<RuntimeConfigTemplateCreate>,
) {
  return request.put<RuntimeConfigTemplate>(`/strategy/runtime-configs/${id}`, data)
}

export function deleteRuntimeConfig(id: number) {
  return request.delete(`/strategy/runtime-configs/${id}`)
}

// ============================================================
// 策略模板列表（新建策略选择器用）
// ============================================================

export function listStrategyTemplates() {
  return request.get<StrategyTemplateItem[]>('/strategy/templates')
}
