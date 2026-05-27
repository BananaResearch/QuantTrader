import { useReplayRuntime } from '../hooks/useReplay'

const levelStyles: Record<string, { bg: string; text: string; label: string }> = {
  info: { bg: 'bg-blue-500/15', text: 'text-blue-400', label: 'INFO' },
  warn: { bg: 'bg-yellow-500/15', text: 'text-yellow-400', label: 'WARN' },
  error: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'ERROR' },
}

/** 回测日志输出 */
export default function ReplayLogs() {
  const logs = useReplayRuntime((s) => s.logEntries)

  if (logs.length === 0) {
    return <div className="text-on-surface-variant text-sm py-8 text-center">暂无日志</div>
  }

  return (
    <div className="space-y-1 font-mono text-xs">
      {logs.map((log, i) => {
        const style = levelStyles[log.level] ?? levelStyles.info
        return (
          <div key={i} className="flex items-start gap-2 py-1.5 px-2 rounded hover:bg-surface-container-highest/50">
            <span className="text-on-surface-variant shrink-0 w-20">{log.time}</span>
            <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold ${style.bg} ${style.text}`}>
              {style.label}
            </span>
            <span className="text-on-surface">{log.message}</span>
          </div>
        )
      })}
    </div>
  )
}
