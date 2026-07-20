/**
 * StrategyTemplatePicker — 新建策略时的模板选择器弹窗。
 *
 * 特性：
 * - 弹窗展示内置策略模板（double_ma / bollinger / macd / rsi）+ 空白模板
 * - 选择后自动填充 code / name / code_content / param_schema / parameters
 */

import { useEffect, useState } from 'react'
import { X, FileCode2, Plus } from 'lucide-react'
import { listStrategyTemplates } from '../api/strategy'
import type { StrategyTemplateItem } from '../types/strategy'

interface StrategyTemplatePickerProps {
  onPick: (template: StrategyTemplateItem) => void
  onClose: () => void
}

export function StrategyTemplatePicker({ onPick, onClose }: StrategyTemplatePickerProps) {
  const [templates, setTemplates] = useState<StrategyTemplateItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void listStrategyTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-surface-container-high rounded-lg border border-outline-variant/30 w-full max-w-2xl shadow-float flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-outline-variant/20 shrink-0">
          <div>
            <h2 className="text-base font-semibold text-on-surface">选择策略模板</h2>
            <p className="text-xs text-on-surface-variant mt-0.5">
              选择一个内置模板开始，或从空白开始
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-surface-container text-on-surface-variant hover:text-on-surface transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto flex-1">
          {loading ? (
            <div className="text-center py-12 text-on-surface-variant text-sm">加载中...</div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {templates.map((tpl) => (
                <TemplateCard key={tpl.code} template={tpl} onPick={onPick} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function TemplateCard({
  template,
  onPick,
}: {
  template: StrategyTemplateItem
  onPick: (t: StrategyTemplateItem) => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className={`rounded-lg border transition-colors cursor-pointer ${
        template.is_blank
          ? 'border-outline-variant/30 bg-surface-container-lowest hover:border-primary/40 hover:bg-surface-container'
          : 'border-outline-variant/30 bg-surface-container-lowest hover:border-primary/40 hover:bg-surface-container'
      }`}
    >
      <button
        type="button"
        className="w-full text-left p-4"
        onClick={() => onPick(template)}
      >
        <div className="flex items-start gap-3">
          <div
            className={`w-9 h-9 rounded-lg shrink-0 flex items-center justify-center ${
              template.is_blank
                ? 'bg-surface-container text-on-surface-variant'
                : 'bg-primary/20 text-primary'
            }`}
          >
            {template.is_blank ? (
              <Plus className="w-4 h-4" />
            ) : (
              <FileCode2 className="w-4 h-4" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm text-on-surface truncate">
              {template.name}
            </div>
            <div className="text-xs text-on-surface-variant mt-0.5 line-clamp-2">
              {template.description}
            </div>
          </div>
        </div>
      </button>

      {/* 展开查看详情 */}
      {!template.is_blank && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            setExpanded((prev) => !prev)
          }}
          className="w-full px-4 py-2 text-xs text-on-surface-variant hover:text-on-surface border-t border-outline-variant/10 transition-colors"
        >
          {expanded ? '收起详情' : '查看参数定义'}
        </button>
      )}

      {expanded && !template.is_blank && template.param_schema && (
        <div className="px-4 pb-3 space-y-1.5">
          {template.param_schema.fields.map((f) => (
            <div key={f.key} className="flex items-center gap-2 text-xs">
              <span className="font-mono text-primary bg-primary/10 px-1.5 py-0.5 rounded">
                {f.key}
              </span>
              <span className="text-on-surface-variant">
                {f.type}
                {f.default !== undefined ? ` = ${f.default}` : ''}
              </span>
              {f.min !== undefined && f.max !== undefined && (
                <span className="text-on-surface-variant/60">
                  [{f.min} ~ {f.max}]
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
