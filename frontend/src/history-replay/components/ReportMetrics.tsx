import { useReplayRuntime } from '../hooks/useReplay'

/** 报告视图横向指标栏，展示 10 个核心指标 */
export default function ReportMetrics() {
  const metrics = useReplayRuntime((s) => s.metrics)

  if (!metrics) return null

  const items: { label: string; value: string; color: string; tooltip?: string }[] = [
    {
      label: '策略总收益',
      value: fmtPct(metrics.total_return),
      color: colorBySign(metrics.total_return),
    },
    {
      label: '基准收益',
      value: fmtPct(metrics.benchmark_return ?? 0),
      color: colorBySign(metrics.benchmark_return ?? 0),
    },
    { label: '阿尔法', value: metrics.alpha?.toFixed(3) ?? '-', color: colorBySign(metrics.alpha ?? 0) },
    { label: '贝塔', value: metrics.beta?.toFixed(3) ?? '-', color: 'text-on-surface' },
    {
      label: '夏普比率',
      value: metrics.sharpe_ratio.toFixed(3),
      color: metrics.sharpe_ratio > 1 ? 'text-up' : metrics.sharpe_ratio > 0.5 ? 'text-warning' : 'text-down',
    },
    {
      label: '索提诺比率',
      value: metrics.sortino_ratio?.toFixed(3) ?? '-',
      color: (metrics.sortino_ratio ?? 0) > 0 ? 'text-up' : 'text-down',
    },
    {
      label: '信息率',
      value: metrics.information_ratio?.toFixed(3) ?? '-',
      color: colorBySign(metrics.information_ratio ?? 0),
    },
    {
      label: '策略波动率',
      value: metrics.strategy_volatility?.toFixed(3) ?? '-',
      color: 'text-on-surface',
    },
    {
      label: '基准波动率',
      value: metrics.benchmark_volatility?.toFixed(3) ?? '-',
      color: 'text-on-surface',
    },
    {
      label: '最大回撤',
      value: fmtPct(metrics.max_drawdown),
      color: 'text-down',
      tooltip: '最大回撤，在选定周期内任一历史时点往后推，产品净值走到最低点时的收益率回撤幅度的最大值',
    },
  ]

  return (
    <div className="grid grid-cols-5 gap-x-6 gap-y-3">
      {items.map((item) => (
        <div key={item.label} className="flex flex-col items-start gap-0.5 group relative">
          <span className="text-xs text-on-surface-variant">{item.label}</span>
          <span className={`text-sm font-medium font-mono-num ${item.color}`}>{item.value}</span>
          {item.tooltip && (
            <div className="absolute bottom-full left-0 mb-2 hidden group-hover:block bg-on-surface text-surface text-xs rounded px-3 py-2 max-w-xs z-50 shadow-lg">
              {item.tooltip}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function fmtPct(v: number): string {
  const prefix = v > 0 ? '+' : ''
  return `${prefix}${v.toFixed(2)}%`
}

function colorBySign(v: number): string {
  if (v > 0) return 'text-up'
  if (v < 0) return 'text-down'
  return 'text-on-surface'
}
