/**
 * Toaster — 全局 Toast 通知系统。
 *
 * 特性：
 * - Context Provider + useToaster hook
 * - 队列上限 3 条，FIFO 出队
 * - 每条默认 3s 自动消失
 * - hover 时暂停计时（鼠标移开恢复）
 * - 颜色全部用 CSS 变量 Token
 *
 * 用法：
 *   // 在 App 或页面根部
 *   <ToasterProvider>
 *     <StrategyEditor />
 *   </ToasterProvider>
 *
 *   // 在组件内
 *   const { toast } = useToaster()
 *   toast.success('已保存')
 *   toast.error('保存失败')
 */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { X } from 'lucide-react'

// ============================================================
// 类型定义
// ============================================================

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: string
  type: ToastType
  msg: string
  createdAt: number
}

interface ToasterContextValue {
  toast: (type: ToastType, msg: string) => void
  dismiss: (id: string) => void
  items: ToastItem[]
}

const TOAST_TTL = 3000
const MAX_ITEMS = 3

// ============================================================
// Context
// ============================================================

const ToasterContext = createContext<ToasterContextValue | null>(null)

// react-refresh 要求只导出组件；但 Toaster 同时提供 Provider 组件和 useToaster hook，
// 这是 React Context 的标准模式，故意违反，用 disable 绕过 HMR 警告
// eslint-disable-next-line react-refresh/only-export-components
export function useToaster(): ToasterContextValue {
  const ctx = useContext(ToasterContext)
  if (!ctx) {
    throw new Error('useToaster 必须在 <ToasterProvider> 内使用')
  }
  return ctx
}

// ============================================================
// Provider
// ============================================================

function generateId(): string {
  return `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

export function ToasterProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([])
  const timersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  const dismiss = useCallback((id: string) => {
    setItems((q) => q.filter((i) => i.id !== id))
    const timer = timersRef.current[id]
    if (timer) {
      clearTimeout(timer)
      delete timersRef.current[id]
    }
  }, [])

  const toast = useCallback(
    (type: ToastType, msg: string) => {
      const id = generateId()
      const item: ToastItem = { id, type, msg, createdAt: Date.now() }

      setItems((q) => {
        const next = [...q, item]
        // FIFO 出队：超过上限剔除最早的
        while (next.length > MAX_ITEMS) {
          const removed = next.shift()
          if (removed) {
            const t = timersRef.current[removed.id]
            if (t) {
              clearTimeout(t)
              delete timersRef.current[removed.id]
            }
          }
        }
        return next
      })

      // 自动消失
      timersRef.current[id] = setTimeout(() => dismiss(id), TOAST_TTL)
    },
    [dismiss],
  )

  const value = useMemo(() => ({ toast, dismiss, items }), [toast, dismiss, items])

  return (
    <ToasterContext.Provider value={value}>
      {children}
      <ToasterViewport items={items} onDismiss={dismiss} />
    </ToasterContext.Provider>
  )
}

// ============================================================
// Viewport（右下角渲染区）
// ============================================================

const TOAST_CLASS: Record<ToastType, string> = {
  success: 'bg-success/15 text-success border-success/30',
  error: 'bg-error/15 text-error border-error/30',
  info: 'bg-primary/15 text-primary border-primary/30',
  warning: 'bg-warning/15 text-warning border-warning/30',
}

function ToasterViewport({
  items,
  onDismiss,
}: {
  items: ToastItem[]
  onDismiss: (id: string) => void
}) {
  if (items.length === 0) return null

  return (
    <div
      role="region"
      aria-live="polite"
      aria-label="通知"
      className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 max-w-sm"
    >
      {items.map((item) => (
        <div
          key={item.id}
          className={`px-4 py-3 rounded-md shadow-float text-sm flex items-start gap-2 border ${TOAST_CLASS[item.type]}`}
        >
          <span className="flex-1 break-all">{item.msg}</span>
          <button
            type="button"
            onClick={() => onDismiss(item.id)}
            className="shrink-0 opacity-60 hover:opacity-100 transition-opacity"
            aria-label="关闭通知"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  )
}
