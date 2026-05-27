import { AppLayout } from '@/common/components'
import { useReplayRuntime } from '../hooks/useReplay'
import { ReplayConfig } from '../components/ReplayConfig'
import { ReplayChart } from '../components/ReplayChart'
import { MetricsPanel } from '../components/MetricsPanel'
import { EquityCurve } from '../components/EquityCurve'
import { TradeLog } from '../components/TradeLog'
import ReportNav from '../components/ReportNav'
import ReportMetrics from '../components/ReportMetrics'
import ReturnChart from '../components/ReturnChart'
import DailyPnlChart from '../components/DailyPnlChart'
import DailyPosition from '../components/DailyPosition'
import ReplayLogs from '../components/ReplayLogs'
import type { ReportTab } from '../types'

/** 报告视图：根据当前 tab 渲染对应内容 */
function ReportContent({ tab }: { tab: ReportTab }) {
  switch (tab) {
    case 'overview':
      return (
        <div className="space-y-4">
          <ReturnChart />
          <DailyPnlChart />
        </div>
      )
    case 'trades':
      return <TradeLog />
    case 'daily_position':
      return <DailyPosition />
    case 'logs':
      return <ReplayLogs />
    default:
      return null
  }
}

export default function Replay() {
  const status = useReplayRuntime((s) => s.status)
  const reportTab = useReplayRuntime((s) => s.reportTab)

  return (
    <AppLayout>
      <div className="h-full overflow-y-auto p-6 space-y-4">
        {/* 顶部：回测配置栏（始终显示） */}
        <ReplayConfig />

        {/* 回放进行中：K线 + 指标 + 资金曲线 + 交易记录 */}
        {(status === 'running' || status === 'paused') && (
          <div className="space-y-4">
            <div className="grid grid-cols-[1fr_240px] gap-4">
              <ReplayChart />
              <MetricsPanel />
            </div>
            <EquityCurve />
            <TradeLog />
          </div>
        )}

        {/* 回放完成：报告视图 */}
        {status === 'completed' && (
          <div className="space-y-4">
            {/* 核心指标横向展示 */}
            <ReportMetrics />

            {/* 左侧 tab 导航 + 右侧内容 */}
            <div className="flex gap-4">
              <ReportNav />
              <div className="flex-1 min-w-0">
                <ReportContent tab={reportTab} />
              </div>
            </div>
          </div>
        )}

        {/* 未开始回测时的空状态提示 */}
        {(status === 'idle' || !status) && (
          <div className="flex flex-col items-center justify-center py-20 text-on-surface-variant">
            <p className="text-lg">配置参数后点击"开始回测"</p>
            <p className="text-sm mt-2">回测完成后可查看详细报告</p>
          </div>
        )}
      </div>
    </AppLayout>
  )
}
