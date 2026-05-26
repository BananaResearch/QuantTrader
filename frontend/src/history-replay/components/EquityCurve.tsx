import ReactECharts from 'echarts-for-react'
import { useReplayRuntime } from '../hooks/useReplay'

export function EquityCurve() {
  const { equityCurve } = useReplayRuntime()

  if (equityCurve.length === 0) {
    return (
      <div className="bg-surface-container-high rounded-lg shadow-card p-5">
        <h3 className="text-sm font-semibold mb-4">资金曲线</h3>
        <div className="h-48 flex items-center justify-center text-on-surface-variant text-sm">
          启动回测后显示资金曲线
        </div>
      </div>
    )
  }

  const times = equityCurve.map((p) => p.time)
  const equities = equityCurve.map((p) => p.equity)
  const drawdowns = equityCurve.map((p) => p.drawdown)

  const option = {
    backgroundColor: 'transparent',
    animation: true,
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: '#242438',
      borderColor: '#2a2a3e',
      textStyle: { color: '#e5e7eb', fontSize: 12 },
      formatter: (params: unknown[]) => {
        const p = params as { seriesName: string; value: number; axisValue: string }[]
        let html = `<div style="font-size:12px;margin-bottom:4px">${p[0]?.axisValue}</div>`
        p.forEach((item) => {
          const color = item.seriesName === '净值' ? '#3b82f6' : '#ef4444'
          html += `<div style="display:flex;align-items:center;gap:4px;font-size:12px">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color}"></span>
            ${item.seriesName}: <span style="font-family:JetBrains Mono,monospace">${item.value.toLocaleString()}</span>
          </div>`
        })
        return html
      },
    },
    grid: {
      left: 60,
      right: 60,
      top: 30,
      bottom: 30,
    },
    xAxis: {
      type: 'category' as const,
      data: times,
      axisLine: { lineStyle: { color: '#1e1e30' } },
      axisLabel: { color: '#9ca3af', fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: [
      {
        type: 'value' as const,
        name: '净值',
        nameTextStyle: { color: '#9ca3af', fontSize: 10 },
        axisLine: { show: false },
        axisLabel: { color: '#9ca3af', fontSize: 10, formatter: (v: number) => (v / 10000).toFixed(0) + '万' },
        splitLine: { lineStyle: { color: '#1e1e30' } },
      },
      {
        type: 'value' as const,
        name: '回撤%',
        nameTextStyle: { color: '#9ca3af', fontSize: 10 },
        axisLine: { show: false },
        axisLabel: { color: '#9ca3af', fontSize: 10, formatter: '{value}%' },
        splitLine: { show: false },
      },
    ],
    series: [
      {
        name: '净值',
        type: 'line' as const,
        data: equities,
        yAxisIndex: 0,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#3b82f6', width: 2 },
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59,130,246,0.25)' },
              { offset: 1, color: 'rgba(59,130,246,0.02)' },
            ],
          },
        },
      },
      {
        name: '回撤',
        type: 'line' as const,
        data: drawdowns,
        yAxisIndex: 1,
        smooth: true,
        showSymbol: false,
        lineStyle: { color: '#ef4444', width: 1.5 },
        areaStyle: {
          color: {
            type: 'linear' as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(239,68,68,0.15)' },
              { offset: 1, color: 'rgba(239,68,68,0.02)' },
            ],
          },
        },
      },
    ],
  }

  return (
    <div className="bg-surface-container-high rounded-lg shadow-card p-5">
      <h3 className="text-sm font-semibold mb-4">资金曲线</h3>
      <ReactECharts option={option} style={{ height: '240px' }} opts={{ renderer: 'canvas' }} />
    </div>
  )
}
