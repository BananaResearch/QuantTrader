/**
 * useUnsavedChanges hook 测试（strategy-engine-editor-ux-fix）。
 *
 * 覆盖：
 * - isDirty=false 时不拦截（无 beforeunload listener）
 * - isDirty=true 时挂载 beforeunload listener
 * - enabled=false 时不拦截
 *
 * 注意：React Router v7 useBlocker 在测试环境需要 DataRouterContext，
 * 完整路由集成测试留给 e2e；此处只验证 beforeunload 行为。
 */

import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { useUnsavedChanges } from '../useUnsavedChanges'

function Probe({ isDirty, enabled = true }: { isDirty: boolean; enabled?: boolean }) {
  useUnsavedChanges({ isDirty, enabled })
  return <div>probe</div>
}

// React Router v7 的 useBlocker 需要 context；我们 mock 掉避免依赖
vi.mock('react-router-dom', () => ({
  useBlocker: () => null,
}))

describe('useUnsavedChanges', () => {
  it('isDirty=false 时不挂 beforeunload', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    render(<Probe isDirty={false} />)
    // 确认没有 beforeunload 注册（react-router-dom 已 mock，不会注册路由 blocker）
    const registered = addSpy.mock.calls.filter(([event]) => event === 'beforeunload')
    expect(registered).toHaveLength(0)
    addSpy.mockRestore()
  })

  it('isDirty=true 且 enabled=true 时挂 beforeunload', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    render(<Probe isDirty={true} enabled={true} />)
    const registered = addSpy.mock.calls.filter(([event]) => event === 'beforeunload')
    expect(registered.length).toBeGreaterThanOrEqual(1)
    addSpy.mockRestore()
  })

  it('enabled=false 时不挂 beforeunload（即使 dirty）', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    render(<Probe isDirty={true} enabled={false} />)
    const registered = addSpy.mock.calls.filter(([event]) => event === 'beforeunload')
    expect(registered).toHaveLength(0)
    addSpy.mockRestore()
  })

  it('isDirty 从 false 切到 true，listener 被注册', () => {
    const addSpy = vi.spyOn(window, 'addEventListener')
    const { rerender } = render(<Probe isDirty={false} />)
    expect(addSpy.mock.calls.filter(([e]) => e === 'beforeunload')).toHaveLength(0)

    rerender(<Probe isDirty={true} />)
    expect(addSpy.mock.calls.filter(([e]) => e === 'beforeunload').length).toBeGreaterThanOrEqual(1)
    addSpy.mockRestore()
  })
})
