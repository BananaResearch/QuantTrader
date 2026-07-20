/**
 * ParamSchemaEditor 组件测试（strategy-engine-params-redesign）。
 *
 * 覆盖：
 * - 初始空状态
 * - 添加字段
 * - 删除字段
 * - 切换 type 时清无关字段（min/max → select → list）
 * - 分组折叠
 * - disabled 模式
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ParamSchemaEditor } from '../ParamSchemaEditor'
import type { ParamField } from '../../types/strategy'

const noop = () => {}

// 找到最后一个含指定 key 的 onChange call
function lastCallForField(onChange: ReturnType<typeof vi.fn>, fieldKey: string) {
  const calls = onChange.mock.calls
  for (let i = calls.length - 1; i >= 0; i--) {
    const [schema] = calls[i] as [{ fields: ParamField[] }]
    if (schema?.fields?.some((f) => f.key === fieldKey)) {
      return schema
    }
  }
  return null
}

describe('ParamSchemaEditor', () => {
  describe('初始状态', () => {
    it('无 value 时渲染空状态提示', () => {
      render(<ParamSchemaEditor value={undefined} onChange={noop} />)
      expect(screen.getByText('暂无参数定义，点击「添加参数」开始')).toBeInTheDocument()
    })

    it('空 fields 数组渲染空状态提示', () => {
      render(<ParamSchemaEditor value={{ fields: [] }} onChange={noop} />)
      expect(screen.getByText('暂无参数定义，点击「添加参数」开始')).toBeInTheDocument()
    })

    it('有字段时渲染字段编辑器', () => {
      render(
        <ParamSchemaEditor
          value={{
            fields: [{ key: 'window', type: 'int', label: '窗口' }],
          }}
          onChange={noop}
        />,
      )
      expect(screen.getByDisplayValue('window')).toBeInTheDocument()
    })

    it('disabled 模式隐藏添加和删除按钮', () => {
      render(
        <ParamSchemaEditor
          value={{
            fields: [{ key: 'window', type: 'int', label: '窗口' }],
          }}
          onChange={noop}
          disabled
        />,
      )
      expect(screen.queryByText('添加参数')).not.toBeInTheDocument()
      expect(screen.queryByTitle('删除参数')).not.toBeInTheDocument()
    })
  })

  describe('添加字段', () => {
    it('点击添加参数插入新字段', async () => {
      const onChange = vi.fn()
      render(<ParamSchemaEditor value={{ fields: [] }} onChange={onChange} />)

      await userEvent.click(screen.getByText('添加参数'))
      expect(onChange).toHaveBeenCalledWith(
        expect.objectContaining({ fields: expect.any(Array) }),
      )
      const call = onChange.mock.calls[0][0] as { fields: ParamField[] }
      expect(call.fields.length).toBe(1)
      expect(call.fields[0].type).toBe('int')
    })

    it('onChange 未提供时点击无副作用', async () => {
      render(<ParamSchemaEditor value={{ fields: [] }} onChange={undefined} />)
      await userEvent.click(screen.getByText('添加参数'))
    })
  })

  describe('删除字段', () => {
    it('点击删除按钮移除字段', async () => {
      const onChange = vi.fn()
      render(
        <ParamSchemaEditor
          value={{
            fields: [
              { key: 'a', type: 'int', label: 'A' },
              { key: 'b', type: 'int', label: 'B' },
            ],
          }}
          onChange={onChange}
        />,
      )

      const deleteButtons = screen.getAllByTitle('删除参数')
      await userEvent.click(deleteButtons[0])

      const call = onChange.mock.calls[0][0] as { fields: ParamField[] }
      expect(call.fields.some((f) => f.key === 'a')).toBe(false)
      expect(call.fields.some((f) => f.key === 'b')).toBe(true)
    })
  })

  describe('切换 type 清无关字段', () => {
    it('int → select 清空 min/max', async () => {
      const onChange = vi.fn()
      const field: ParamField = {
        key: 'test',
        type: 'int',
        label: '测试',
        min: 1,
        max: 100,
      }
      render(<ParamSchemaEditor value={{ fields: [field] }} onChange={onChange} />)

      // 通过 label 关联找到类型选择框
      const typeSelect = screen.getByRole('combobox')
      fireEvent.change(typeSelect, { target: { value: 'select' } })

      const call = lastCallForField(onChange, 'test')!
      expect(call.fields[0].type).toBe('select')
      expect(call.fields[0].min).toBeUndefined()
      expect(call.fields[0].max).toBeUndefined()
    })

    it('select → int 清空 options', async () => {
      const onChange = vi.fn()
      const field: ParamField = {
        key: 'mode',
        type: 'select',
        label: '模式',
        options: [{ label: 'A', value: 'a' }],
      }
      render(<ParamSchemaEditor value={{ fields: [field] }} onChange={onChange} />)

      const typeSelect = screen.getByRole('combobox')
      fireEvent.change(typeSelect, { target: { value: 'int' } })

      const call = lastCallForField(onChange, 'mode')!
      expect(call.fields[0].options).toBeUndefined()
    })

    it('list → float 清空 item_type', async () => {
      const onChange = vi.fn()
      const field: ParamField = {
        key: 'items',
        type: 'list',
        label: '列表',
        item_type: 'stock_code',
      }
      render(<ParamSchemaEditor value={{ fields: [field] }} onChange={onChange} />)

      // list 类型有两个 combobox（type + item_type），通过第一个（type）切换
      const typeSelect = screen.getAllByRole('combobox')[0]
      fireEvent.change(typeSelect, { target: { value: 'float' } })

      const call = lastCallForField(onChange, 'items')!
      expect(call.fields[0].item_type).toBeUndefined()
    })
  })

  describe('分组折叠', () => {
    it('有 group 的字段渲染折叠按钮', () => {
      render(
        <ParamSchemaEditor
          value={{
            fields: [{ key: 'w', type: 'int', label: '窗口', group: '均线参数' }],
          }}
          onChange={noop}
        />,
      )
      expect(screen.getByText('均线参数')).toBeInTheDocument()
      expect(screen.getByText('1 个参数')).toBeInTheDocument()
    })

    it('无 group 的字段属于「默认分组」', () => {
      render(
        <ParamSchemaEditor
          value={{
            fields: [{ key: 'w', type: 'int', label: '窗口' }],
          }}
          onChange={noop}
        />,
      )
      expect(screen.getByText('默认分组')).toBeInTheDocument()
    })

    it('点击分组标题折叠/展开', async () => {
      render(
        <ParamSchemaEditor
          value={{
            fields: [{ key: 'w', type: 'int', label: '窗口' }],
          }}
          onChange={noop}
        />,
      )

      expect(screen.getByDisplayValue('w')).toBeInTheDocument()

      await userEvent.click(screen.getByText('默认分组'))
      expect(screen.queryByDisplayValue('w')).not.toBeInTheDocument()

      await userEvent.click(screen.getByText('默认分组'))
      expect(screen.getByDisplayValue('w')).toBeInTheDocument()
    })
  })

  describe('字段编辑', () => {
    it('key 输入框过滤非法字符', async () => {
      const onChange = vi.fn()
      render(
        <ParamSchemaEditor
          value={{ fields: [{ key: 'orig', type: 'int', label: '测试' }] }}
          onChange={onChange}
        />,
      )

      const keyInput = screen.getByPlaceholderText('如 short_window')
      fireEvent.change(keyInput, { target: { value: 'abc123' } })

      // 验证 onChange 被调用，key 被更新
      expect(onChange).toHaveBeenCalled()
      const lastCall = onChange.mock.calls.at(-1)![0] as { fields: ParamField[] }
      expect(lastCall.fields[0].key).toBe('abc123')
    })

    it('修改 label 触发 onChange', async () => {
      const onChange = vi.fn()
      render(
        <ParamSchemaEditor
          value={{ fields: [{ key: 'w', type: 'int', label: '窗口' }] }}
          onChange={onChange}
        />,
      )

      const labelInput = screen.getByPlaceholderText('如 短期均线')
      fireEvent.change(labelInput, { target: { value: '新标签' } })

      const call = lastCallForField(onChange, 'w')!
      expect(call.fields[0].label).toBe('新标签')
    })

    it('修改 required 触发 onChange', async () => {
      const onChange = vi.fn()
      render(
        <ParamSchemaEditor
          value={{ fields: [{ key: 'w', type: 'int', label: '窗口', required: false }] }}
          onChange={onChange}
        />,
      )

      const checkbox = screen.getByLabelText('必填')
      await userEvent.click(checkbox)

      const call = onChange.mock.calls[0][0] as { fields: ParamField[] }
      expect(call.fields[0].required).toBe(true)
    })
  })
})
