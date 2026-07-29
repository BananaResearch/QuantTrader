/**
 * useKeyboardShortcut hook 测试（strategy-engine-editor-ux-fix）。
 *
 * 覆盖：
 * - Cmd+S（macOS）/ Ctrl+S（Windows）触发 handler
 * - preventDefault=true 时调用 e.preventDefault()
 * - enabled=false 时不触发
 * - 不匹配的组合键不触发
 */

import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { useKeyboardShortcut } from '../useKeyboardShortcut'

function Probe({
  combo,
  handler,
  enabled = true,
}: {
  combo: string
  handler: () => void
  enabled?: boolean
}) {
  useKeyboardShortcut({ combo, handler, enabled })
  return <div>probe</div>
}

function fireKey(key: string, { meta = false, ctrl = false, shift = false }: { meta?: boolean; ctrl?: boolean; shift?: boolean } = {}) {
  const event = new KeyboardEvent('keydown', {
    key,
    metaKey: meta,
    ctrlKey: ctrl,
    shiftKey: shift,
    bubbles: true,
    cancelable: true,
  })
  window.dispatchEvent(event)
  return event
}

describe('useKeyboardShortcut', () => {
  it('Cmd+S 触发 handler（macOS）', () => {
    const handler = vi.fn()
    render(<Probe combo="mod+s" handler={handler} />)
    fireKey('s', { meta: true })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('Ctrl+S 触发 handler（Windows）', () => {
    const handler = vi.fn()
    render(<Probe combo="mod+s" handler={handler} />)
    fireKey('s', { ctrl: true })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('preventDefault=true（默认）阻止浏览器默认', () => {
    const handler = vi.fn()
    render(<Probe combo="mod+s" handler={handler} />)
    const event = fireKey('s', { meta: true })
    expect(event.defaultPrevented).toBe(true)
  })

  it('enabled=false 时不触发', () => {
    const handler = vi.fn()
    render(<Probe combo="mod+s" handler={handler} enabled={false} />)
    fireKey('s', { meta: true })
    expect(handler).not.toHaveBeenCalled()
  })

  it('未按 mod 时不触发（仅按 s）', () => {
    const handler = vi.fn()
    render(<Probe combo="mod+s" handler={handler} />)
    fireKey('s')
    expect(handler).not.toHaveBeenCalled()
  })

  it('组合键 shift+mod+p', () => {
    const handler = vi.fn()
    render(<Probe combo="mod+shift+p" handler={handler} />)
    fireKey('p', { meta: true, shift: true })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('shift 缺失时不触发 mod+shift+p', () => {
    const handler = vi.fn()
    render(<Probe combo="mod+shift+p" handler={handler} />)
    fireKey('p', { meta: true })
    expect(handler).not.toHaveBeenCalled()
  })

  it('卸载时移除监听器（不再触发）', () => {
    const handler = vi.fn()
    const { unmount } = render(<Probe combo="mod+s" handler={handler} />)
    unmount()
    fireKey('s', { meta: true })
    expect(handler).not.toHaveBeenCalled()
  })
})
