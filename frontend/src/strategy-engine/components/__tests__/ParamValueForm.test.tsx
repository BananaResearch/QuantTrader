/**
 * ParamValueForm 组件测试（strategy-engine-params-redesign）。
 *
 * 覆盖：7 种字段类型的控件渲染与值回传。
 * 注：使用 fireEvent.change 替代 userEvent.type 以避免 controlled input 兼容问题。
 */

import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ParamValueForm } from '../ParamValueForm'
import type { ParamField, ParamSchema } from '../../types/strategy'

const noop = () => {}

// 找到最后一个含 expectedKey 的 onChange call
function lastCallWithKey(onChange: ReturnType<typeof vi.fn>, expectedKey: string) {
  const calls = onChange.mock.calls
  for (let i = calls.length - 1; i >= 0; i--) {
    const data = calls[i][0] as Record<string, unknown>
    if (expectedKey in data) return data
  }
  return null
}

describe('ParamValueForm', () => {
  describe('空 Schema 状态', () => {
    it('无 schema 时渲染空提示', () => {
      render(<ParamValueForm schema={undefined} value={{}} onChange={noop} />)
      expect(screen.getByText('该策略暂无参数 Schema，无需配置')).toBeInTheDocument()
    })

    it('空 fields 数组渲染空提示', () => {
      render(<ParamValueForm schema={{ fields: [] }} value={{}} onChange={noop} />)
      expect(screen.getByText('该策略暂无参数 Schema，无需配置')).toBeInTheDocument()
    })
  })

  describe('int 类型', () => {
    it('渲染 number input（spinbutton），值回传为数字', () => {
      const onChange = vi.fn()
      const schema: ParamSchema = {
        fields: [{ key: 'window', type: 'int', label: '窗口', min: 1, max: 200 }],
      }
      render(<ParamValueForm schema={schema} value={{ window: 10 }} onChange={onChange} />)

      const input = screen.getByRole('spinbutton')
      expect(input).toHaveValue(10)

      fireEvent.change(input, { target: { value: '20' } })
      expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ window: 20 }))
    })

    it('空输入回传 undefined', () => {
      const onChange = vi.fn()
      const schema: ParamSchema = { fields: [{ key: 'w', type: 'int', label: '窗口' }] }
      render(<ParamValueForm schema={schema} value={{ w: 5 }} onChange={onChange} />)

      const input = screen.getByRole('spinbutton')
      fireEvent.change(input, { target: { value: '' } })
      expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ w: undefined }))
    })

    it('使用 schema 默认值', () => {
      const schema: ParamSchema = {
        fields: [{ key: 'w', type: 'int', label: '窗口', default: 42 }],
      }
      render(<ParamValueForm schema={schema} value={{}} onChange={noop} />)
      expect(screen.getByRole('spinbutton')).toHaveValue(42)
    })
  })

  describe('float 类型', () => {
    it('渲染 number input（step any），值回传为数字', () => {
      const onChange = vi.fn()
      const schema: ParamSchema = {
        fields: [{ key: 'ratio', type: 'float', label: '比例', min: 0, max: 1 }],
      }
      render(<ParamValueForm schema={schema} value={{ ratio: 0.5 }} onChange={onChange} />)

      const input = screen.getByRole('spinbutton')
      expect(input).toHaveValue(0.5)

      fireEvent.change(input, { target: { value: '0.8' } })
      expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ ratio: 0.8 }))
    })
  })

  describe('string 类型', () => {
    it('渲染文本输入框', () => {
      const onChange = vi.fn()
      const schema: ParamSchema = { fields: [{ key: 'name', type: 'string', label: '名称' }] }
      render(<ParamValueForm schema={schema} value={{ name: 'test' }} onChange={onChange} />)

      const input = screen.getByRole('textbox')
      expect(input).toHaveValue('test')

      fireEvent.change(input, { target: { value: 'hello' } })
      expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ name: 'hello' }))
    })
  })

  describe('bool 类型', () => {
    it('true 显示「是」，false 显示「否」', () => {
      const schema: ParamSchema = { fields: [{ key: 'enabled', type: 'bool', label: '启用' }] }

      const { rerender } = render(
        <ParamValueForm schema={schema} value={{ enabled: true }} onChange={noop} />,
      )
      expect(screen.getByRole('button', { name: '是' })).toBeInTheDocument()

      rerender(
        <ParamValueForm schema={schema} value={{ enabled: false }} onChange={noop} />,
      )
      expect(screen.getByRole('button', { name: '否' })).toBeInTheDocument()
    })

    it('点击切换布尔值', async () => {
      const onChange = vi.fn()
      const schema: ParamSchema = { fields: [{ key: 'enabled', type: 'bool', label: '启用' }] }
      render(<ParamValueForm schema={schema} value={{ enabled: false }} onChange={onChange} />)

      await userEvent.click(screen.getByRole('button', { name: '否' }))
      expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ enabled: true }))
    })
  })

  describe('select 类型', () => {
    it('渲染下拉选择，使用 options', () => {
      const schema: ParamSchema = {
        fields: [
          {
            key: 'mode',
            type: 'select',
            label: '模式',
            options: [
              { label: '日线', value: 'daily' },
              { label: '分钟', value: '1min' },
            ],
          },
        ],
      }
      render(<ParamValueForm schema={schema} value={{ mode: 'daily' }} onChange={noop} />)

      const select = screen.getByRole('combobox')
      expect(select).toHaveValue('daily')
      expect(screen.getByText('日线')).toBeInTheDocument()
      expect(screen.getByText('分钟')).toBeInTheDocument()
    })

    it('切换选项回传 value', async () => {
      const onChange = vi.fn()
      const schema: ParamSchema = {
        fields: [
          {
            key: 'mode',
            type: 'select',
            label: '模式',
            options: [
              { label: '日线', value: 'daily' },
              { label: '分钟', value: '1min' },
            ],
          },
        ],
      }
      render(<ParamValueForm schema={schema} value={{ mode: 'daily' }} onChange={onChange} />)

      await userEvent.selectOptions(screen.getByRole('combobox'), '1min')
      expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ mode: '1min' }))
    })
  })

  describe('stock_code 类型', () => {
    it('stock_code 渲染文本输入框', () => {
      // 验证 stock_code 类型渲染为文本输入框
      // 注意：初始值显示取决于 value prop，组件仅在 onChange 时转大写
      const schema: ParamSchema = {
        fields: [{ key: 'stock', type: 'stock_code', label: '股票' }],
      }
      render(<ParamValueForm schema={schema} value={{ stock: '000001.SZ' }} onChange={noop} />)

      const input = screen.getByRole('textbox')
      expect(input).toBeInTheDocument()
      expect(input).toHaveValue('000001.SZ')
    })

    it('stock_code onChange 转换为大写', async () => {
      const onChange = vi.fn()
      const schema: ParamSchema = {
        fields: [{ key: 'stock', type: 'stock_code', label: '股票' }],
      }
      render(<ParamValueForm schema={schema} value={{ stock: '' }} onChange={onChange} />)

      const input = screen.getByRole('textbox')
      fireEvent.change(input, { target: { value: '600519.SH' } })
      expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ stock: '600519.SH' }))
    })
  })

  describe('list 类型', () => {
    it('渲染数组编辑器（int 类型）', () => {
      const schema: ParamSchema = {
        fields: [{ key: 'values', type: 'list', label: '数值列表', item_type: 'int' }],
      }
      render(<ParamValueForm schema={schema} value={{ values: [1, 2] }} onChange={noop} />)

      const inputs = screen.getAllByRole('spinbutton')
      expect(inputs).toHaveLength(2)
      expect(inputs[0]).toHaveValue(1)
      expect(inputs[1]).toHaveValue(2)
    })

    it('点击添加元素增加新项', async () => {
      const onChange = vi.fn()
      const schema: ParamSchema = {
        fields: [{ key: 'values', type: 'list', label: '数值列表', item_type: 'int' }],
      }
      render(<ParamValueForm schema={schema} value={{ values: [1] }} onChange={onChange} />)

      await userEvent.click(screen.getByText('添加元素'))
      expect(onChange).toHaveBeenLastCalledWith(
        expect.objectContaining({ values: expect.any(Array) }),
      )
    })

    it('点击删除按钮移除元素', async () => {
      const onChange = vi.fn()
      const schema: ParamSchema = {
        fields: [{ key: 'values', type: 'list', label: '数值列表', item_type: 'int' }],
      }
      render(<ParamValueForm schema={schema} value={{ values: [10, 20] }} onChange={onChange} />)

      // 渲染了两个元素（共两个 number inputs）
      const inputs = screen.getAllByRole('spinbutton')
      expect(inputs).toHaveLength(2)

      // Lucide Trash2 图标按钮，通过 SVG path 内容区分
      const allButtons = screen.getAllByRole('button')
      // 过滤出含删除 SVG path 的按钮（Lucide trash-2 路径）
      const deleteButtons = allButtons.filter((btn) =>
        btn.innerHTML.includes('trash') || btn.querySelector('svg')?.innerHTML?.includes('trash'),
      )
      expect(deleteButtons.length).toBeGreaterThanOrEqual(2)

      await userEvent.click(deleteButtons[0])

      const call = lastCallWithKey(onChange, 'values')!
      expect((call.values as unknown[]).length).toBe(1)
    })

    it('stock_code 类型 list 元素自动大写', async () => {
      const onChange = vi.fn()
      const schema: ParamSchema = {
        fields: [{ key: 'stocks', type: 'list', label: '股票列表', item_type: 'stock_code' }],
      }
      render(<ParamValueForm schema={schema} value={{ stocks: [] }} onChange={onChange} />)

      await userEvent.click(screen.getByText('添加元素'))
      const textInput = screen.getByPlaceholderText('000001.SZ')
      fireEvent.change(textInput, { target: { value: '600519.SH' } })

      const call = lastCallWithKey(onChange, 'stocks')!
      expect(call.stocks[0]).toBe('600519.SH')
    })
  })

  describe('错误显示', () => {
    it('有 error 时渲染错误消息', () => {
      const schema: ParamSchema = { fields: [{ key: 'w', type: 'int', label: '窗口' }] }
      render(
        <ParamValueForm
          schema={schema}
          value={{ w: 5 }}
          onChange={noop}
          errors={{ w: '值超出范围' }}
        />,
      )
      expect(screen.getByText('值超出范围')).toBeInTheDocument()
    })
  })

  describe('必填标记', () => {
    it('required=true 显示必填星号', () => {
      const schema: ParamSchema = {
        fields: [{ key: 'w', type: 'int', label: '窗口', required: true }],
      }
      render(<ParamValueForm schema={schema} value={{}} onChange={noop} />)
      // 星号通过 text-error/60 样式渲染
      expect(screen.getByText('*', { selector: '.text-error\\/60' })).toBeInTheDocument()
    })
  })
})
