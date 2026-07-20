/**
 * Sparkline 组件测试（strategy-engine-editor-ux-fix）。
 *
 * 覆盖：
 * - 涨跌色语义正确（中国惯例：红涨绿跌）
 * - points < 2 时不渲染
 * - SVG stroke 使用 currentColor（避免硬编码）
 */

import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Sparkline } from '../Sparkline'

describe('Sparkline', () => {
  const points = [100, 105, 110, 108, 115]

  it('上涨时使用 text-up（红色，中国惯例）', () => {
    const { getByTestId } = render(<Sparkline points={points} positive={true} />)
    const svg = getByTestId('sparkline')
    expect(svg.getAttribute('class')).toContain('text-up')
    expect(svg.getAttribute('class')).not.toContain('text-down')
    expect(svg.getAttribute('data-positive')).toBe('true')
  })

  it('下跌时使用 text-down（绿色，中国惯例）', () => {
    const { getByTestId } = render(<Sparkline points={points} positive={false} />)
    const svg = getByTestId('sparkline')
    expect(svg.getAttribute('class')).toContain('text-down')
    expect(svg.getAttribute('class')).not.toContain('text-up')
    expect(svg.getAttribute('data-positive')).toBe('false')
  })

  it('path stroke 使用 currentColor，不硬编码十六进制', () => {
    const { container } = render(<Sparkline points={points} positive={true} />)
    const path = container.querySelector('path')
    expect(path).not.toBeNull()
    expect(path?.getAttribute('stroke')).toBe('currentColor')
  })

  it('points 不足 2 个时不渲染', () => {
    const { container } = render(<Sparkline points={[100]} positive={true} />)
    expect(container.querySelector('svg')).toBeNull()
  })

  it('带 role=img 和 aria-label（a11y）', () => {
    const { getByTestId } = render(<Sparkline points={points} positive={true} />)
    const svg = getByTestId('sparkline')
    expect(svg.getAttribute('role')).toBe('img')
    expect(svg.getAttribute('aria-label')).toContain('上涨')
  })
})
