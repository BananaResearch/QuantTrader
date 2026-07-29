/**
 * useKeyboardShortcut — 全局键盘快捷键 hook。
 *
 * 特性：
 * - 支持 meta（macOS）/ ctrl（Windows/Linux）自动识别
 * - enabled 开关，便于在 loading/disabled 时禁用
 * - preventDefault 选项（默认 true）
 * - 自动 cleanup
 *
 * 用法：
 *   useKeyboardShortcut({ combo: 'mod+s', handler: handleSave, enabled: !saving })
 *
 * combo 格式：
 *   'mod+s'        → meta+s 或 ctrl+s（自动按平台）
 *   'mod+shift+p'  → meta+shift+p 或 ctrl+shift+p
 *   'enter'        → 单键
 */

import { useEffect } from 'react'

interface UseKeyboardShortcutOptions {
  /** 快捷键组合，如 'mod+s' / 'mod+shift+p' / 'enter' */
  combo: string
  /** 触发回调 */
  handler: (e: KeyboardEvent) => void
  /** 是否启用，默认 true */
  enabled?: boolean
  /** 是否阻止默认行为，默认 true */
  preventDefault?: boolean
}

function parseCombo(combo: string): {
  needMod: boolean
  needShift: boolean
  needAlt: boolean
  key: string
} {
  const parts = combo.toLowerCase().split('+').map((p) => p.trim())
  return {
    needMod: parts.includes('mod'),
    needShift: parts.includes('shift'),
    needAlt: parts.includes('alt'),
    key: parts[parts.length - 1],
  }
}

export function useKeyboardShortcut({
  combo,
  handler,
  enabled = true,
  preventDefault = true,
}: UseKeyboardShortcutOptions): void {
  useEffect(() => {
    if (!enabled) return

    const parsed = parseCombo(combo)

    const onKeyDown = (e: KeyboardEvent) => {
      const hasMod = e.metaKey || e.ctrlKey
      const matchesMod = parsed.needMod ? hasMod : true
      const matchesShift = parsed.needShift ? e.shiftKey : true
      const matchesAlt = parsed.needAlt ? e.altKey : true
      const matchesKey = e.key.toLowerCase() === parsed.key

      if (matchesMod && matchesShift && matchesAlt && matchesKey) {
        if (preventDefault) e.preventDefault()
        handler(e)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [combo, handler, enabled, preventDefault])
}
