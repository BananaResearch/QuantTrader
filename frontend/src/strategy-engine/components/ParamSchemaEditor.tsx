/**
 * ParamSchemaEditor — 参数 Schema 结构化编辑器。
 *
 * 特性：
 * - 增/删参数字段
 * - 字段属性编辑（key/type/label/default/min/max/options/item_type/group/required）
 * - 按 group 分组折叠显示
 * - 切换 type 时自动清空不相关字段（min/max/options/item_type）
 */

import { useCallback, useState } from 'react'
import { Plus, Trash2, ChevronDown, ChevronRight } from 'lucide-react'
import type { ParamField, ParamFieldType, ParamSchema } from '../types/strategy'
import { OptionsEditor } from './OptionsEditor'

interface ParamSchemaEditorProps {
  value: ParamSchema | undefined | null
  onChange?: (schema: ParamSchema) => void
  disabled?: boolean
}

const PARAM_TYPES: { value: ParamFieldType; label: string }[] = [
  { value: 'int', label: '整数 (int)' },
  { value: 'float', label: '小数 (float)' },
  { value: 'string', label: '字符串 (string)' },
  { value: 'bool', label: '布尔 (bool)' },
  { value: 'select', label: '下拉选择 (select)' },
  { value: 'stock_code', label: '股票代码 (stock_code)' },
  { value: 'list', label: '数组 (list)' },
]

const LIST_ITEM_TYPES: { value: ParamFieldType; label: string }[] = [
  { value: 'int', label: '整数' },
  { value: 'float', label: '小数' },
  { value: 'string', label: '字符串' },
  { value: 'stock_code', label: '股票代码' },
]

function createDefaultField(): ParamField {
  return {
    key: '',
    type: 'int',
    label: '',
    default: undefined,
    required: false,
    group: '',
  }
}

function clearIrrelevantFields(field: ParamField): ParamField {
  const { type } = field
  const cleaned = { ...field }
  if (type !== 'int' && type !== 'float') {
    delete cleaned.min
    delete cleaned.max
  }
  if (type !== 'select') {
    delete cleaned.options
  }
  if (type !== 'list') {
    delete cleaned.item_type
  }
  return cleaned
}

export function ParamSchemaEditor({ value, onChange, disabled = false }: ParamSchemaEditorProps) {
  const schema: ParamSchema = value ?? { fields: [] }
  const fields = schema.fields ?? []

  const updateField = useCallback(
    (index: number, patch: Partial<ParamField>) => {
      if (!onChange) return
      const updated = [...fields]
      let field = { ...updated[index], ...patch }
      // 切换 type 时清无关字段
      if (patch.type && patch.type !== fields[index].type) {
        field = clearIrrelevantFields(field)
      }
      updated[index] = field
      onChange({ fields: updated })
    },
    [fields, onChange],
  )

  const addField = useCallback(() => {
    if (!onChange) return
    onChange({ fields: [...fields, createDefaultField()] })
  }, [fields, onChange])

  const removeField = useCallback(
    (index: number) => {
      if (!onChange) return
      const updated = fields.filter((_, i) => i !== index)
      onChange({ fields: updated })
    },
    [fields, onChange],
  )

  // 按 group 分组
  const groups = fields.reduce<Record<string, ParamField[]>>((acc, f) => {
    const g = f.group || '默认分组'
    if (!acc[g]) acc[g] = []
    acc[g].push(f)
    return acc
  }, {})

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs text-on-surface-variant">参数 Schema</span>
        {!disabled && (
          <button
            type="button"
            onClick={addField}
            className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            添加参数
          </button>
        )}
      </div>

      {fields.length === 0 ? (
        <div className="text-xs text-on-surface-variant py-4 text-center border border-dashed border-outline-variant/30 rounded-md">
          暂无参数定义，点击「添加参数」开始
        </div>
      ) : (
        Object.entries(groups).map(([groupName, groupFields]) => {
          const globalIndices = groupFields.map((f) =>
            fields.indexOf(f),
          )
          return (
            <div key={groupName} className="border border-outline-variant/20 rounded-md overflow-hidden">
              <button
                type="button"
                className="w-full flex items-center gap-2 px-3 py-2 bg-surface-container/50 hover:bg-surface-container transition-colors text-xs text-on-surface-variant"
                onClick={() =>
                  setCollapsed((prev) => ({ ...prev, [groupName]: !prev[groupName] }))
                }
              >
                {collapsed[groupName] ? (
                  <ChevronRight className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
                <span className="font-medium text-on-surface">{groupName}</span>
                <span className="ml-auto opacity-60">{groupFields.length} 个参数</span>
              </button>

              {!collapsed[groupName] && (
                <div className="divide-y divide-outline-variant/10">
                  {groupFields.map((field, localIdx) => {
                    const globalIdx = globalIndices[localIdx]
                    return (
                      <FieldEditor
                        key={`${globalIdx}-${field.key}`}
                        field={field}
                        onChange={(patch) => updateField(globalIdx, patch)}
                        onRemove={() => removeField(globalIdx)}
                        disabled={disabled}
                      />
                    )
                  })}
                </div>
              )}
            </div>
          )
        })
      )}
    </div>
  )
}

interface FieldEditorProps {
  field: ParamField
  onChange: (patch: Partial<ParamField>) => void
  onRemove: () => void
  disabled: boolean
}

function FieldEditor({ field, onChange, onRemove, disabled }: FieldEditorProps) {
  return (
    <div className="p-3 space-y-2 bg-surface-container-lowest">
      <div className="flex items-start gap-2">
        <div className="flex-1 grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-on-surface-variant mb-0.5 block">键名 *</label>
            <input
              type="text"
              value={field.key ?? ''}
              onChange={(e) => onChange({ key: e.target.value.replace(/[^a-z0-9_]/g, '') })}
              placeholder="如 short_window"
              disabled={disabled}
              className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs font-mono text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
            />
          </div>
          <div>
            <label className="text-xs text-on-surface-variant mb-0.5 block">类型 *</label>
            <select
              value={field.type}
              onChange={(e) => onChange({ type: e.target.value as ParamFieldType })}
              disabled={disabled}
              className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
            >
              {PARAM_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-on-surface-variant mb-0.5 block">展示标签 *</label>
            <input
              type="text"
              value={field.label ?? ''}
              onChange={(e) => onChange({ label: e.target.value })}
              placeholder="如 短期均线"
              disabled={disabled}
              className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
            />
          </div>
          <div>
            <label className="text-xs text-on-surface-variant mb-0.5 block">分组</label>
            <input
              type="text"
              value={field.group ?? ''}
              onChange={(e) => onChange({ group: e.target.value || undefined })}
              placeholder="如 均线参数（空=默认分组）"
              disabled={disabled}
              className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
            />
          </div>
        </div>
        {!disabled && (
          <button
            type="button"
            onClick={onRemove}
            className="mt-5 p-1.5 text-error/60 hover:text-error transition-colors"
            title="删除参数"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* 类型相关字段 */}
      <div className="grid grid-cols-3 gap-2">
        <div>
          <label className="text-xs text-on-surface-variant mb-0.5 block">默认值</label>
          <input
            type={field.type === 'int' || field.type === 'float' ? 'number' : 'text'}
            value={
              field.default == null
                ? ''
                : typeof field.default === 'string' || typeof field.default === 'number'
                  ? field.default
                  : ''
            }
            onChange={(e) => {
              const v = e.target.value
              onChange({ default: field.type === 'int' ? Number(v) : field.type === 'float' ? Number(v) : v })
            }}
            disabled={disabled}
            className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
          />
        </div>

        {(field.type === 'int' || field.type === 'float') && (
          <>
            <div>
              <label className="text-xs text-on-surface-variant mb-0.5 block">最小值</label>
              <input
                type="number"
                value={field.min ?? ''}
                onChange={(e) => onChange({ min: e.target.value ? Number(e.target.value) : undefined })}
                disabled={disabled}
                className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
              />
            </div>
            <div>
              <label className="text-xs text-on-surface-variant mb-0.5 block">最大值</label>
              <input
                type="number"
                value={field.max ?? ''}
                onChange={(e) => onChange({ max: e.target.value ? Number(e.target.value) : undefined })}
                disabled={disabled}
                className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
              />
            </div>
          </>
        )}

        {field.type === 'select' && (
          <div className="col-span-3">
            <label className="text-xs text-on-surface-variant mb-1 block flex items-center gap-1">
              <span>选项</span>
              <span className="text-error/60">*</span>
            </label>
            <OptionsEditor
              value={field.options ?? []}
              onChange={(opts) => onChange({ options: opts })}
              disabled={disabled}
            />
          </div>
        )}

        {field.type === 'list' && (
          <div className="col-span-3">
            <label className="text-xs text-on-surface-variant mb-0.5 block flex items-center gap-1">
              <span>元素类型</span>
              <span className="text-error/60">*</span>
            </label>
            <select
              value={field.item_type ?? 'int'}
              onChange={(e) => onChange({ item_type: e.target.value as ParamFieldType })}
              disabled={disabled}
              className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
            >
              {LIST_ITEM_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* 描述 + 必填 */}
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <label className="text-xs text-on-surface-variant mb-0.5 block">帮助文本</label>
          <input
            type="text"
            value={field.description ?? ''}
            onChange={(e) => onChange({ description: e.target.value || undefined })}
            placeholder="参数的说明文字"
            disabled={disabled}
            className="w-full h-8 px-2 rounded border border-outline-variant/30 bg-surface text-xs text-on-surface outline-none focus:border-primary transition-colors disabled:opacity-50"
          />
        </div>
        <label className="flex items-center gap-1.5 mt-5 cursor-pointer">
          <input
            type="checkbox"
            checked={field.required ?? false}
            onChange={(e) => onChange({ required: e.target.checked })}
            disabled={disabled}
            className="w-3.5 h-3.5 rounded border-outline text-primary"
          />
          <span className="text-xs text-on-surface-variant">必填</span>
        </label>
      </div>
    </div>
  )
}

// Need React for useState
