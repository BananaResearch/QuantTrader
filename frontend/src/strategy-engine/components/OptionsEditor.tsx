/**
 * OptionsEditor — select 字段的键值对列表编辑器。
 *
 * 替代 ParamSchemaEditor 中 select 类型的 JSON 字符串编辑。
 *
 * 特性：
 * - 每行 label + value + 删除按钮
 * - 底部「+ 添加选项」
 * - value 重复时黄色边框警告（不阻止保存）
 * - 空列表时显示空状态
 *
 * 用法：
 *   <OptionsEditor
 *     value={field.options ?? []}
 *     onChange={(opts) => onChange({ options: opts })}
 *   />
 */

import { Plus, Trash2, AlertTriangle } from 'lucide-react'

interface OptionItem {
  label: string
  value: string | number
}

interface OptionsEditorProps {
  value: OptionItem[]
  onChange: (next: OptionItem[]) => void
  disabled?: boolean
}

export function OptionsEditor({ value = [], onChange, disabled = false }: OptionsEditorProps) {
  const update = (index: number, patch: Partial<OptionItem>) => {
    const next = value.map((it, i) => (i === index ? { ...it, ...patch } : it))
    onChange(next)
  }

  const remove = (index: number) => {
    onChange(value.filter((_, i) => i !== index))
  }

  const add = () => {
    onChange([...value, { label: '', value: '' }])
  }

  // value 重复检测（仅警告，不阻止）
  const duplicateValueSet = new Set<string>()
  const duplicates = new Set<number>()
  value.forEach((it, i) => {
    const key = String(it.value)
    if (duplicateValueSet.has(key)) {
      duplicates.add(i)
    } else {
      duplicateValueSet.add(key)
    }
  })

  if (value.length === 0) {
    return (
      <div className="space-y-2">
        <div className="text-xs text-on-surface-variant py-3 text-center border border-dashed border-outline-variant/30 rounded-md">
          暂无选项，点击下方按钮添加
        </div>
        {!disabled && (
          <button
            type="button"
            onClick={add}
            className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            添加选项
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      {value.map((it, i) => {
        const isDup = duplicates.has(i)
        return (
          <div key={i} className="flex items-center gap-1.5">
            <input
              type="text"
              value={it.label ?? ''}
              onChange={(e) => update(i, { label: e.target.value })}
              placeholder="显示文本"
              disabled={disabled}
              className="flex-1 h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
              aria-label={`选项 ${i + 1} 显示文本`}
            />
            <input
              type="text"
              value={String(it.value ?? '')}
              onChange={(e) => update(i, { value: e.target.value })}
              placeholder="值"
              disabled={disabled}
              className={`flex-1 h-8 px-2 rounded border bg-surface text-xs font-mono text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50 ${
                isDup ? 'border-warning/60' : 'border-outline-variant/30'
              }`}
              aria-label={`选项 ${i + 1} 值`}
            />
            {isDup && (
              <AlertTriangle
                className="w-3.5 h-3.5 text-warning shrink-0"
                aria-label="值重复"
              />
            )}
            {!disabled && (
              <button
                type="button"
                onClick={() => remove(i)}
                className="p-1 text-error/60 hover:text-error transition-colors shrink-0"
                aria-label={`删除选项 ${i + 1}`}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        )
      })}
      {!disabled && (
        <button
          type="button"
          onClick={add}
          className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          添加选项
        </button>
      )}
    </div>
  )
}
