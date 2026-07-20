/**
 * RuntimeConfigSelector — 运行配置选择器（模板 + 临时覆盖弹窗）。
 *
 * 特性：
 * - 下拉选择已有模板
 * - 「自定义」按钮触发临时覆盖弹窗
 * - 弹窗内可覆盖 universe / 日期 / 资金 / 费率
 * - 白名单外字段不可编辑
 */

import { useCallback, useEffect, useState } from 'react'
import { Settings2, X } from 'lucide-react'
import { listRuntimeConfigs } from '../api/strategy'
import { useToaster } from './Toaster'
import type { RuntimeConfigTemplate } from '../types/strategy'

interface RuntimeConfigSelectorProps {
  templateId?: number | null
  override?: Partial<RuntimeConfigTemplate> | null
  onChange?: (templateId: number, override?: Partial<RuntimeConfigTemplate> | null) => void
  disabled?: boolean
}

const OVERRIDE_LABELS: Record<string, string> = {
  universe: '标的列表',
  start_date: '开始日期',
  end_date: '结束日期',
  initial_capital: '初始资金（¥）',
  frequency: '数据频率',
  slippage: '滑点（万分比，0.0001 = 万一）',
  commission: '佣金（万分比，0.0001 = 万一）',
}

export function RuntimeConfigSelector({
  templateId,
  override,
  onChange,
  disabled = false,
}: RuntimeConfigSelectorProps) {
  const { toast } = useToaster()
  const [templates, setTemplates] = useState<RuntimeConfigTemplate[]>([])
  const [loading, setLoading] = useState(true)
  const [showOverride, setShowOverride] = useState(false)
  const [localOverride, setLocalOverride] = useState<Partial<RuntimeConfigTemplate> | null>(
    override ?? null,
  )

  useEffect(() => {
    void listRuntimeConfigs()
      .then((data) => {
        setTemplates(data)
        if (templateId == null && data.length > 0) {
          onChange?.(data[0].id, undefined)
        }
      })
      .catch((err) => {
        const msg = err instanceof Error ? err.message : '加载运行配置模板失败'
        toast('error', msg)
      })
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const selectedTemplate = templates.find((t) => t.id === templateId)

  const handleTemplateChange = useCallback(
    (id: number) => {
      onChange?.(id, localOverride ?? undefined)
    },
    [localOverride, onChange],
  )

  const handleOverrideChange = useCallback(
    (patch: Partial<RuntimeConfigTemplate>) => {
      const updated = { ...localOverride, ...patch }
      setLocalOverride(updated)
      if (templateId != null) {
        onChange?.(templateId, updated)
      }
    },
    [localOverride, templateId, onChange],
  )

  const hasOverride = !!localOverride && Object.keys(localOverride).length > 0

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <select
          value={templateId ?? ''}
          onChange={(e) => e.target.value && handleTemplateChange(Number(e.target.value))}
          disabled={disabled || loading}
          aria-label="运行配置模板"
          className="flex-1 h-9 px-3 rounded-md border border-outline-variant/30 bg-surface text-sm text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
        >
          <option value="">选择运行配置模板</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
              {t.is_default ? ' ⭐' : ''}
            </option>
          ))}
        </select>

        <button
          type="button"
          onClick={() => setShowOverride(true)}
          disabled={disabled || templateId == null}
          className="flex items-center gap-1.5 h-9 px-3 rounded-md border border-outline bg-surface-container hover:bg-surface-container-highest text-on-surface text-xs transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="自定义运行配置"
          aria-label="自定义运行配置"
        >
          <Settings2 className="w-3.5 h-3.5" />
          自定义
        </button>
      </div>

      {/* 当前模板摘要 */}
      {selectedTemplate && (
        <div className="text-xs text-on-surface-variant bg-surface-container-lowest rounded px-3 py-2 space-y-0.5">
          <div>
            标的：{selectedTemplate.universe.length > 0 ? selectedTemplate.universe.join(', ') : '空'}
            {hasOverride && localOverride?.universe && (
              <span className="text-primary ml-1">→ {localOverride.universe.join(', ')}</span>
            )}
          </div>
          {selectedTemplate.mode === 'backtest' && (
            <div>
              日期：{selectedTemplate.start_date} ~ {selectedTemplate.end_date}
              {hasOverride && (localOverride?.start_date || localOverride?.end_date) && (
                <span className="text-primary ml-1">
                  → {localOverride.start_date ?? selectedTemplate.start_date} ~{' '}
                  {localOverride.end_date ?? selectedTemplate.end_date}
                </span>
              )}
            </div>
          )}
          <div>
            资金：¥{Number(selectedTemplate.initial_capital).toLocaleString()}
            {hasOverride && localOverride?.initial_capital && (
              <span className="text-primary ml-1">→ ¥{Number(localOverride.initial_capital).toLocaleString()}</span>
            )}
          </div>
        </div>
      )}

      {/* 临时覆盖弹窗 */}
      {showOverride && selectedTemplate && (
        <OverrideModal
          template={selectedTemplate}
          override={localOverride}
          onChange={handleOverrideChange}
          onClose={() => setShowOverride(false)}
          onClear={() => {
            setLocalOverride(null)
            if (templateId != null) onChange?.(templateId, undefined)
          }}
        />
      )}
    </div>
  )
}

interface OverrideModalProps {
  template: RuntimeConfigTemplate
  override: Partial<RuntimeConfigTemplate> | null
  onChange: (patch: Partial<RuntimeConfigTemplate>) => void
  onClose: () => void
  onClear: () => void
}

function OverrideModal({ template, override, onChange, onClose, onClear }: OverrideModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-surface-container-high rounded-lg border border-outline-variant/30 w-full max-w-md shadow-float">
        <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant/20">
          <h3 className="text-sm font-semibold text-on-surface">自定义运行配置</h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-surface-container text-on-surface-variant"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-3 max-h-[60vh] overflow-y-auto">
          {/* universe */}
          <OverrideField label={OVERRIDE_LABELS['universe']} original={template.universe} override={override?.universe}>
            <textarea
              value={(override?.universe ?? template.universe).join('\n')}
              onChange={(e) => {
                const lines = e.target.value.split('\n').filter((l) => l.trim())
                onChange({ universe: lines as string[] })
              }}
              rows={3}
              placeholder="每行一个股票代码，如 000001.SZ"
              className="w-full h-16 px-2 py-1.5 rounded border border-outline-variant/30 bg-surface text-xs font-mono text-on-surface outline-none focus:border-primary transition-colors resize-y"
            />
            <p className="text-xs text-on-surface-variant/60">每行一个标的</p>
          </OverrideField>

          {/* 日期范围（仅 backtest） */}
          {template.mode === 'backtest' && (
            <>
              <OverrideField
                label={OVERRIDE_LABELS['start_date']}
                original={template.start_date ?? ''}
                override={override?.start_date ?? template.start_date ?? ''}
              >
                <input
                  type="date"
                  value={(override?.start_date ?? template.start_date) ?? ''}
                  onChange={(e) => onChange({ start_date: e.target.value || undefined })}
                  className="w-full h-9 px-3 rounded border border-outline-variant/30 bg-surface text-sm text-on-surface outline-none focus:border-primary transition-colors"
                />
              </OverrideField>

              <OverrideField
                label={OVERRIDE_LABELS['end_date']}
                original={template.end_date ?? ''}
                override={override?.end_date ?? template.end_date ?? ''}
              >
                <input
                  type="date"
                  value={(override?.end_date ?? template.end_date) ?? ''}
                  onChange={(e) => onChange({ end_date: e.target.value || undefined })}
                  className="w-full h-9 px-3 rounded border border-outline-variant/30 bg-surface text-sm text-on-surface outline-none focus:border-primary transition-colors"
                />
              </OverrideField>
            </>
          )}

          {/* initial_capital */}
          <OverrideField
            label={OVERRIDE_LABELS['initial_capital']}
            original={template.initial_capital}
            override={override?.initial_capital ?? template.initial_capital}
          >
            <input
              type="number"
              value={Number(override?.initial_capital ?? template.initial_capital)}
              min={1}
              onChange={(e) => onChange({ initial_capital: Number(e.target.value) })}
              className="w-full h-9 px-3 rounded border border-outline-variant/30 bg-surface text-sm text-on-surface outline-none focus:border-primary transition-colors"
            />
          </OverrideField>

          {/* slippage / commission */}
          <div className="grid grid-cols-2 gap-3">
            <OverrideField
              label={OVERRIDE_LABELS['slippage']}
              original={template.slippage}
              override={override?.slippage ?? template.slippage}
            >
              <input
                type="number"
                value={Number(override?.slippage ?? template.slippage)}
                min={0}
                max={1}
                step="0.0001"
                onChange={(e) => onChange({ slippage: Number(e.target.value) })}
                className="w-full h-9 px-3 rounded border border-outline-variant/30 bg-surface text-sm text-on-surface outline-none focus:border-primary transition-colors"
              />
            </OverrideField>

            <OverrideField
              label={OVERRIDE_LABELS['commission']}
              original={template.commission}
              override={override?.commission ?? template.commission}
            >
              <input
                type="number"
                value={Number(override?.commission ?? template.commission)}
                min={0}
                max={1}
                step="0.0001"
                onChange={(e) => onChange({ commission: Number(e.target.value) })}
                className="w-full h-9 px-3 rounded border border-outline-variant/30 bg-surface text-sm text-on-surface outline-none focus:border-primary transition-colors"
              />
            </OverrideField>
          </div>
        </div>

        <div className="flex items-center justify-between px-4 py-3 border-t border-outline-variant/20">
          <button
            type="button"
            onClick={onClear}
            className="text-xs text-error/80 hover:text-error transition-colors"
          >
            清除自定义
          </button>
          <button
            type="button"
            onClick={onClose}
            className="px-4 h-8 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  )
}

function OverrideField({
  label,
  original,
  override,
  children,
}: {
  label: string
  original: unknown
  override: unknown
  children: React.ReactNode
}) {
  const isOverridden = String(original) !== String(override)
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2">
        <label className="text-xs text-on-surface-variant">{label}</label>
        {isOverridden && (
          <span className="px-1.5 py-0.5 text-xs rounded bg-primary/20 text-primary border border-primary/30">
            已覆盖
          </span>
        )}
      </div>
      {children}
    </div>
  )
}
