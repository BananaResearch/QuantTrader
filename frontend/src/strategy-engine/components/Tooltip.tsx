/**
 * Tooltip — 轻量 hover/focus 提示组件。
 *
 * 特性：
 * - 纯 CSS 定位（不引入第三方）
 * - 支持 hover + focus-visible 触发（鼠标和键盘均可）
 * - 暗色主题：surface-container-highest + outline border
 *
 * 用法：
 *   <Tooltip content="保存后不可修改">
 *     <HelpCircle className="w-3 h-3" />
 *   </Tooltip>
 */

import { type ReactNode } from 'react'

interface TooltipProps {
  content: string
  children: ReactNode
  side?: 'top' | 'bottom' | 'left' | 'right'
}

const SIDE_CLASS: Record<NonNullable<TooltipProps['side']>, string> = {
  top: 'bottom-full left-1/2 -translate-x-1/2 mb-1',
  bottom: 'top-full left-1/2 -translate-x-1/2 mt-1',
  left: 'right-full top-1/2 -translate-y-1/2 mr-1',
  right: 'left-full top-1/2 -translate-y-1/2 ml-1',
}

export function Tooltip({ content, children, side = 'top' }: TooltipProps) {
  if (!content) return <>{children}</>

  return (
    <span className="relative inline-flex group/tip focus-within/tip:outline-none">
      <span tabIndex={0} className="inline-flex outline-none focus-visible:ring-2 focus-visible:ring-primary/30 rounded">
        {children}
      </span>
      <span
        role="tooltip"
        className={`pointer-events-none absolute ${SIDE_CLASS[side]} z-50 px-2 py-1 rounded text-xs whitespace-nowrap bg-surface-container-highest text-on-surface border border-outline shadow-float opacity-0 group-hover/tip:opacity-100 group-focus-within/tip:opacity-100 transition-opacity duration-150`}
      >
        {content}
      </span>
    </span>
  )
}
