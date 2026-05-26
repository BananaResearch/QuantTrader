import { useReplayRuntime } from '../hooks/useReplay'
import { formatPercent, formatNumber } from '@/common/utils/format'
import { cn } from '@/common/utils'

interface MetricItemProps {
  label: string
  value: string
  subtext?: string
  trend?: 'up' | 'down' | 'neutral'
}

function MetricItem({ label, value, subtext, trend }: MetricItemProps) {
  return (
    <div className="py-2.5 px-3 border-b border-outline-variant/20 last:border-b-0">
      <div className="text-xs text-on-surface-variant mb-1">{label}</div>
      <div
        className={cn(
          'text-lg font-semibold font-mono-num',
          trend === 'up' && 'text-up',
          trend === 'down' && 'text-down',
          trend === 'neutral' && 'text-on-surface',
          !trend && 'text-on-surface'
        )}
      >
        {value}
      </div>
      {subtext && <div className="text-xs text-on-surface-variant mt-0.5">{subtext}</div>}
    </div>
  )
}

export function MetricsPanel() {
  const { metrics } = useReplayRuntime()

  if (!metrics) {
    return (
      <div className="bg-surface-container-high rounded-lg shadow-card p-4">
        <h3 className="text-sm font-semibold mb-3">回测指标</h3>
        <div className="text-sm text-on-surface-variant text-center py-8">
          启动回测后显示指标
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface-container-high rounded-lg shadow-card">
      <h3 className="text-sm font-semibold px-3 pt-3 pb-2">回测指标</h3>
      <MetricItem
        label="总收益率"
        value={formatPercent(metrics.total_return)}
        trend={metrics.total_return > 0 ? 'up' : metrics.total_return < 0 ? 'down' : 'neutral'}
      />
      <MetricItem
        label="年化收益"
        value={formatPercent(metrics.annual_return)}
        trend={metrics.annual_return > 0 ? 'up' : metrics.annual_return < 0 ? 'down' : 'neutral'}
      />
      <MetricItem
        label="最大回撤"
        value={formatPercent(metrics.max_drawdown)}
        trend={metrics.max_drawdown < 0 ? 'down' : 'neutral'}
      />
      <MetricItem
        label="夏普比率"
        value={metrics.sharpe_ratio.toFixed(2)}
        trend={metrics.sharpe_ratio > 1 ? 'up' : metrics.sharpe_ratio < 0 ? 'down' : 'neutral'}
        subtext={metrics.sharpe_ratio > 1 ? '优秀' : metrics.sharpe_ratio > 0.5 ? '良好' : '一般'}
      />
      <MetricItem
        label="胜率"
        value={formatPercent(metrics.win_rate)}
        trend={metrics.win_rate > 50 ? 'up' : 'down'}
      />
      <MetricItem
        label="盈亏比"
        value={metrics.profit_loss_ratio.toFixed(2)}
        trend={metrics.profit_loss_ratio > 1 ? 'up' : 'down'}
      />
      <MetricItem label="交易次数" value={String(metrics.trade_count)} />
      <MetricItem
        label="总盈亏"
        value={`¥${formatNumber(metrics.total_pnl)}`}
        trend={metrics.total_pnl > 0 ? 'up' : metrics.total_pnl < 0 ? 'down' : 'neutral'}
      />
    </div>
  )
}
