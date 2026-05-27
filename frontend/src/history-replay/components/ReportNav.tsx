import { useReplayRuntime } from '../hooks/useReplay'
import type { ReportTab } from '../types'

const tabs: { key: ReportTab; label: string }[] = [
  { key: 'overview', label: '收益概述' },
  { key: 'trades', label: '交易详情' },
  { key: 'daily_position', label: '每日持仓&收益' },
  { key: 'logs', label: '日志输出' },
]

/** 报告视图左侧 tab 导航 */
export default function ReportNav() {
  const activeTab = useReplayRuntime((s) => s.reportTab)
  const setTab = useReplayRuntime((s) => s.setReportTab)

  return (
    <nav className="w-36 shrink-0">
      <ul className="space-y-0.5">
        {tabs.map((tab) => (
          <li key={tab.key}>
            <button
              onClick={() => setTab(tab.key)}
              className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                activeTab === tab.key
                  ? 'bg-primary/15 text-primary font-medium'
                  : 'text-on-surface-variant hover:bg-surface-container-highest'
              }`}
            >
              {tab.label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  )
}
