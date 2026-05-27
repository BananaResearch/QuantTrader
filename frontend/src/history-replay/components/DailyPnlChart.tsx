import { useEffect, useRef } from 'react'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useReplayRuntime } from '../hooks/useReplay'

echarts.use([BarChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

/** 每日盈亏柱状图 */
export default function DailyPnlChart() {
  const chartRef = useRef<HTMLDivElement>(null)
  const instanceRef = useRef<echarts.ECharts | null>(null)
  const dailyPnlData = useReplayRuntime((s) => s.dailyPnlData)

  useEffect(() => {
    if (!chartRef.current) return
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, undefined, { renderer: 'canvas' })
    }

    const dates = dailyPnlData.map((d) => d.time)
    const pnlValues = dailyPnlData.map((d) => d.pnl)

    instanceRef.current.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(30,30,30,0.9)',
        borderColor: '#444',
        textStyle: { color: '#eee', fontSize: 12 },
        formatter: (params: unknown) => {
          const ps = params as Array<{ seriesName: string; value: number; axisValue: string; color: string }>
          const p = ps[0]
          if (!p) return ''
          const prefix = p.value > 0 ? '+' : ''
          const color = p.value >= 0 ? '#ef4444' : '#22c55e'
          return `<div style="font-size:12px;margin-bottom:4px">${p.axisValue}</div>
            <div style="display:flex;align-items:center;gap:6px;font-size:12px">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color}"></span>
              当日盈亏: <span style="font-family:JetBrains Mono,monospace;color:${color}">${prefix}¥${Math.abs(p.value).toLocaleString()}</span>
            </div>`
        },
      },
      grid: {
        left: 70,
        right: 30,
        top: 20,
        bottom: 60,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#444' } },
        axisLabel: { color: '#999', fontSize: 10, formatter: (v: string) => v.slice(5) },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          color: '#999',
          fontSize: 10,
          formatter: (v: number) => {
            if (Math.abs(v) >= 10000) return `${(v / 10000).toFixed(0)}万`
            return `¥${v.toLocaleString()}`
          },
        },
        splitLine: { lineStyle: { color: '#333', type: 'dashed' } },
      },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        {
          type: 'slider',
          start: 0,
          end: 100,
          height: 20,
          bottom: 5,
          borderColor: '#444',
          fillerColor: 'rgba(59,130,246,0.15)',
          handleStyle: { color: '#3b82f6' },
          textStyle: { color: '#999' },
        },
      ],
      series: [
        {
          name: '当日盈亏',
          type: 'bar',
          data: pnlValues.map((v) => ({
            value: v,
            itemStyle: { color: v >= 0 ? '#ef4444' : '#22c55e' },
          })),
          barMaxWidth: 8,
        },
      ],
    }, true)
  }, [dailyPnlData])

  useEffect(() => {
    const handleResize = () => instanceRef.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div className="bg-surface-container-high rounded-lg p-4">
      <h3 className="text-sm font-medium text-on-surface mb-3">每日盈亏</h3>
      <div ref={chartRef} className="w-full h-[200px]" />
    </div>
  )
}
