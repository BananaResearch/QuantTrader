import { AppLayout } from '@/common/components'
import { ReplayConfig } from '../components/ReplayConfig'
import { ReplayChart } from '../components/ReplayChart'
import { MetricsPanel } from '../components/MetricsPanel'
import { EquityCurve } from '../components/EquityCurve'
import { TradeLog } from '../components/TradeLog'

export default function Replay() {
  return (
    <AppLayout>
      <div className="h-full overflow-y-auto p-6 space-y-4">
        {/* 顶部：回测配置栏 */}
        <ReplayConfig />

        {/* 中部：K线图 + 指标面板 */}
        <div className="grid grid-cols-[1fr_240px] gap-4">
          <ReplayChart />
          <MetricsPanel />
        </div>

        {/* 资金曲线 */}
        <EquityCurve />

        {/* 交易记录表 */}
        <TradeLog />
      </div>
    </AppLayout>
  )
}
