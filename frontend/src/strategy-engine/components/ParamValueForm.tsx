/**
 * ParamValueForm — 基于 ParamSchema 自动渲染参数值表单。
 *
 * 渲染规则（strategy-param-schema spec）：
 * - int / float → number input
 * - string → text input
 * - bool → switch
 * - select → 下拉选择（来自 options）
 * - stock_code → 带搜索的标的输入（含格式警告）
 * - list → 数组编辑器（按 item_type 渲染元素控件）
 */

import { useCallback } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import type { ParamField, ParamSchema } from '../types/strategy'

// 中国 A 股代码格式（深市 .SZ / 沪市 .SH / 北交所 .BJ / 港股 .HK / 上交所 .SS 兼容）
const STOCK_CODE_REGEX = /^(\d{6}|[A-Z]{1,6})\.(SZ|SH|BJ|SS|HK)$/

interface ParamValueFormProps {
  schema: ParamSchema | undefined | null
  value: Record<string, unknown> | undefined | null
  onChange?: (values: Record<string, unknown>) => void
  errors?: Record<string, string>  // key → error message
  disabled?: boolean
}

export function ParamValueForm({
  schema,
  value = {},
  onChange,
  errors = {},
  disabled = false,
}: ParamValueFormProps) {
  const fields = schema?.fields ?? []

  const setValue = useCallback(
    (key: string, v: unknown) => {
      if (!onChange) return
      onChange({ ...value, [key]: v })
    },
    [value, onChange],
  )

  if (fields.length === 0) {
    return (
      <div className="text-xs text-on-surface-variant py-3 text-center border border-dashed border-outline-variant/30 rounded-md">
        该策略暂无参数 Schema，无需配置
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {fields.map((field) => (
        <FieldInput
          key={field.key}
          field={field}
          value={value?.[field.key] ?? field.default}
          onChange={(v) => setValue(field.key, v)}
          error={errors[field.key]}
          disabled={disabled}
        />
      ))}
    </div>
  )
}

interface FieldInputProps {
  field: ParamField
  value: unknown
  onChange: (v: unknown) => void
  error?: string
  disabled: boolean
}

function FieldInput({ field, value, onChange, error, disabled }: FieldInputProps) {
  const inputClass =
    'w-full h-9 px-3 rounded-md border bg-surface text-sm text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50'

  // stock_code 格式校验（仅警告，不阻止保存）
  const isStockCodeInvalid =
    field.type === 'stock_code' && typeof value === 'string' && value.length > 0 && !STOCK_CODE_REGEX.test(value)

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-xs text-on-surface-variant">
          {field.label}
          {field.required && <span className="text-error/60 ml-0.5">*</span>}
          {field.type === 'stock_code' && (
            <span className="ml-1 text-on-surface-variant/60">（格式：000001.SZ）</span>
          )}
        </label>
        {error && <span className="text-xs text-error">{error}</span>}
      </div>

      {field.type === 'int' && (
        <input
          type="number"
          value={value as number ?? ''}
          min={field.min}
          max={field.max}
          step={1}
          onChange={(e) => onChange(e.target.value === '' ? undefined : Number(e.target.value))}
          disabled={disabled}
          className={`${inputClass} ${error ? 'border-error/50' : 'border-outline-variant/30'}`}
          placeholder={`${field.min ?? ''} ~ ${field.max ?? ''}`}
        />
      )}

      {field.type === 'float' && (
        <input
          type="number"
          value={value as number ?? ''}
          min={field.min}
          max={field.max}
          step="any"
          onChange={(e) => onChange(e.target.value === '' ? undefined : Number(e.target.value))}
          disabled={disabled}
          className={`${inputClass} ${error ? 'border-error/50' : 'border-outline-variant/30'}`}
          placeholder={`${field.min ?? ''} ~ ${field.max ?? ''}`}
        />
      )}

      {field.type === 'string' && (
        <input
          type="text"
          value={(value as string) ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={`${inputClass} ${error ? 'border-error/50' : 'border-outline-variant/30'}`}
        />
      )}

      {field.type === 'bool' && (
        <button
          type="button"
          onClick={() => onChange(!value)}
          disabled={disabled}
          className={`h-9 px-4 rounded-md border text-sm font-medium transition-colors disabled:opacity-50 ${
            value
              ? 'bg-primary/20 border-primary/30 text-primary'
              : 'bg-surface border-outline-variant/30 text-on-surface-variant'
          }`}
        >
          {value ? '是' : '否'}
        </button>
      )}

      {field.type === 'select' && (
        <select
          value={(value as string | number) ?? ''}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className={`${inputClass} ${error ? 'border-error/50' : 'border-outline-variant/30'}`}
        >
          <option value="">请选择</option>
          {(field.options ?? []).map((opt) => (
            <option key={String(opt.value)} value={String(opt.value)}>
              {opt.label}
            </option>
          ))}
        </select>
      )}

      {field.type === 'stock_code' && (
        <input
          type="text"
          value={(value as string) ?? ''}
          onChange={(e) => onChange(e.target.value.toUpperCase())}
          disabled={disabled}
          placeholder="000001.SZ"
          aria-label={field.label}
          className={`${inputClass} font-mono ${
            isStockCodeInvalid ? 'border-warning/60' : error ? 'border-error/50' : 'border-outline-variant/30'
          }`}
        />
      )}
      {isStockCodeInvalid && (
        <p className="text-xs text-warning">代码格式不规范，应为 000001.SZ / 600519.SH / 830799.BJ 等</p>
      )}

      {field.type === 'list' && (
        <ListEditor
          field={field}
          value={(value as unknown[]) ?? []}
          onChange={onChange}
          error={error}
          disabled={disabled}
        />
      )}

      {field.description && (
        <p className="text-xs text-on-surface-variant/60">{field.description}</p>
      )}
    </div>
  )
}

interface ListEditorProps {
  field: ParamField
  value: unknown[]
  onChange: (v: unknown[]) => void
  error?: string
  disabled: boolean
}

function ListEditor({ field, value, onChange, disabled }: ListEditorProps) {
  const itemType = field.item_type ?? 'string'

  const addItem = () => onChange([...value, createDefault(itemType)])
  const removeItem = (index: number) =>
    onChange(value.filter((_, i) => i !== index))
  const updateItem = (index: number, v: unknown) => {
    const updated = [...value]
    updated[index] = v
    onChange(updated)
  }

  return (
    <div className="space-y-1.5">
      {(value.length === 0 ? [createDefault(itemType)] : value).map((item, i) => (
        <div key={i} className="flex items-center gap-1.5">
          <div className="flex-1">
            {itemType === 'int' && (
              <input
                type="number"
                value={item as number ?? ''}
                onChange={(e) =>
                  updateItem(i, e.target.value === '' ? undefined : Number(e.target.value))
                }
                disabled={disabled}
                className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
              />
            )}
            {itemType === 'float' && (
              <input
                type="number"
                value={item as number ?? ''}
                step="any"
                onChange={(e) =>
                  updateItem(i, e.target.value === '' ? undefined : Number(e.target.value))
                }
                disabled={disabled}
                className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
              />
            )}
            {(itemType === 'string' || itemType === 'stock_code') && (
              <input
                type="text"
                value={(item as string) ?? ''}
                onChange={(e) => updateItem(i, itemType === 'stock_code' ? e.target.value.toUpperCase() : e.target.value)}
                disabled={disabled}
                placeholder={itemType === 'stock_code' ? '000001.SZ' : '字符串'}
                className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50 font-mono"
              />
            )}
          </div>
          {!disabled && (
            <button
              type="button"
              onClick={() => removeItem(i)}
              className="p-1 text-error/60 hover:text-error transition-colors"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      ))}
      {!disabled && (
        <button
          type="button"
          onClick={addItem}
          className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          添加元素
        </button>
      )}
    </div>
  )
}

function createDefault(type: string): unknown {
  if (type === 'int') return undefined
  if (type === 'float') return undefined
  if (type === 'stock_code') return ''
  return ''
}
