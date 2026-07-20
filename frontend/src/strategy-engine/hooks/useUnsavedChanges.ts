/**
 * useUnsavedChanges — 未保存修改提示 hook。
 *
 * 行为：
 * - 浏览器关闭/刷新：通过 beforeunload 事件触发原生确认
 * - React Router 路由跳转：通过 useBlocker 拦截
 *
 * 用法：
 *   const isDirty = useMemo(() => computeDirty(state, snapshot), [state, snapshot])
 *   useUnsavedChanges({ isDirty, enabled: !saving })
 *
 *   // 保存成功后
 *   setSnapshot({ ...state })  // 重置快照
 */

import { useEffect, useRef } from 'react'
import { useBlocker } from 'react-router-dom'

interface UseUnsavedChangesOptions {
  /** 当前是否有未保存修改 */
  isDirty: boolean
  /** 是否启用拦截，默认 true。保存过程中可设为 false */
  enabled?: boolean
  /** 自定义提示文案 */
  message?: string
}

export function useUnsavedChanges({
  isDirty,
  enabled = true,
  message = '有未保存的修改，确认离开？',
}: UseUnsavedChangesOptions): void {
  const messageRef = useRef(message)
  // ref 同步放在 effect 里（react-hooks 7 规则禁止 render 阶段写 ref）
  useEffect(() => {
    messageRef.current = message
  }, [message])

  // beforeunload：浏览器关闭/刷新
  useEffect(() => {
    if (!enabled || !isDirty) return

    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = messageRef.current
      return messageRef.current
    }

    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [isDirty, enabled])

  // React Router 路由跳转拦截
  useBlocker(
    enabled && isDirty
      ? () => window.confirm(messageRef.current)
      : false,
  )
}
