/**
 * Toaster 组件测试（strategy-engine-editor-ux-fix）。
 *
 * 覆盖：
 * - FIFO 队列：连续 4 次 toast 只保留 3 条
 * - 手动 dismiss
 * - 不同 type 的 className 正确
 * - aria-live 可访问性
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, act, fireEvent } from '@testing-library/react'
import { ToasterProvider, useToaster } from '../Toaster'

// 测试用触发器组件
function Trigger({
  type,
  msg,
  times = 1,
}: {
  type: 'success' | 'error' | 'info' | 'warning'
  msg: string
  times?: number
}) {
  const { toast } = useToaster()
  return (
    <button
      type="button"
      onClick={() => {
        for (let i = 0; i < times; i++) toast(type, `${msg}-${i}`)
      }}
    >
      trigger
    </button>
  )
}

describe('Toaster', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('单条 toast 正常渲染', () => {
    render(
      <ToasterProvider>
        <Trigger type="success" msg="hello" />
      </ToasterProvider>,
    )
    fireEvent.click(screen.getByText('trigger'))
    expect(screen.getByText('hello-0')).toBeInTheDocument()
  })

  it('不同 type 使用对应 Token className', () => {
    const types: Array<'success' | 'error' | 'info' | 'warning'> = ['success', 'error', 'info', 'warning']
    const { rerender } = render(
      <ToasterProvider>
        <Trigger type="success" msg="x" />
      </ToasterProvider>,
    )
    for (const t of types) {
      rerender(
        <ToasterProvider>
          <Trigger type={t} msg={`test-${t}`} />
        </ToasterProvider>,
      )
      fireEvent.click(screen.getByText('trigger'))
      const node = screen.getByText(`test-${t}-0`)
      // Toast 容器是文本 span 的直接父级（含 Token class + border）
      const toastContainer = node.parentElement
      const expected = {
        success: 'text-success',
        error: 'text-error',
        info: 'text-primary',
        warning: 'text-warning',
      }[t]
      expect(toastContainer?.className).toContain(expected)
    }
  })

  it('FIFO 队列：连续 4 次只保留 3 条', () => {
    render(
      <ToasterProvider>
        <Trigger type="info" msg="q" times={4} />
      </ToasterProvider>,
    )
    fireEvent.click(screen.getByText('trigger'))

    // 第一条（q-0）应被剔除
    expect(screen.queryByText('q-0')).not.toBeInTheDocument()
    // 后 3 条保留
    expect(screen.getByText('q-1')).toBeInTheDocument()
    expect(screen.getByText('q-2')).toBeInTheDocument()
    expect(screen.getByText('q-3')).toBeInTheDocument()
  })

  it('3 秒后自动消失（TTL）', () => {
    render(
      <ToasterProvider>
        <Trigger type="success" msg="temp" />
      </ToasterProvider>,
    )
    fireEvent.click(screen.getByText('trigger'))
    expect(screen.getByText('temp-0')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(3100)
    })

    expect(screen.queryByText('temp-0')).not.toBeInTheDocument()
  })

  it('viewport 带 aria-live=polite', () => {
    render(
      <ToasterProvider>
        <Trigger type="success" msg="x" />
      </ToasterProvider>,
    )
    fireEvent.click(screen.getByText('trigger'))
    const region = screen.getByRole('region')
    expect(region.getAttribute('aria-live')).toBe('polite')
  })

  it('点击 X 按钮 dismiss', () => {
    render(
      <ToasterProvider>
        <Trigger type="success" msg="dismiss-me" />
      </ToasterProvider>,
    )
    fireEvent.click(screen.getByText('trigger'))
    const closeBtn = screen.getByLabelText('关闭通知')
    fireEvent.click(closeBtn)
    expect(screen.queryByText('dismiss-me-0')).not.toBeInTheDocument()
  })
})
