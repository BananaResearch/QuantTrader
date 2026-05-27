import { useEffect, useRef } from 'react'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useReplayRuntime } from '../hooks/useReplay'

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

/** 策略收益 vs 基准收益 对比折线图（面积图） */
export default function ReturnChart() {
  const chartRef = useRef<HTMLDivElement>(null)
  const instanceRef = useRef<echarts.ECharts | null>(null)
  const strategyReturnData = useReplayRuntime((s) => s.strategyReturnData)
  const benchmarkData = useReplayRuntime((s) => s.benchmarkData)

  useEffect(() => {
    if (!chartRef.current) return
    if (!instanceRef.current) {
      instanceRef.current = echarts.init(chartRef.current, undefined, { renderer: 'canvas' })
    }

    const dates = strategyReturnData.map((d) => d.time)
    const strategyValues = strategyReturnData.map((d) => d.return_pct)
    const benchmarkValues = benchmarkData.map((d) => d.return_pct)

    instanceRef.current.setOption({
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(30,30,30,0.9)',
        borderColor: '#444',
        textStyle: { color: '#eee', fontSize: 12 },
        formatter: (params: unknown) => {
          const ps = params as Array<{ seriesName: string; value: number; axisValue: string }>
          let html = `<div style="font-size:12px;margin-bottom:4px">${ps[0]?.axisValue}</div>`
          for (const p of ps) {
            const color = p.seriesName === '策略收益率' ? '#3b82f6' : '#ef4444'
            const prefix = p.value > 0 ? '+' : ''
            html += `<div style="display:flex;align-items:center;gap:6px;font-size:12px">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color}"></span>
              ${p.seriesName}: <span style="font-family:JetBrains Mono,monospace">${prefix}${p.value.toFixed(2)}%</span>
            </div>`
          }
          return html
        },
      },
      legend: {
        data: ['策略收益率', '基准收益率'],
        top: 0,
        right: 10,
        textStyle: { color: '#999', fontSize: 12 },
      },
      grid: {
        left: 60,
        right: 30,
        top: 40,
        bottom: 60,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#444' } },
        axisLabel: { color: '#999', fontSize: 10, rotate: 0, formatter: (v: string) => v.slice(5) },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#999', fontSize: 10, formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#333', type: 'dashed' } },
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
        },
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
          name: '策略收益率',
          type: 'line',
          data: strategyValues,
          smooth: true,
          symbol: 'none',
          lineStyle: { color: '#3b82f6', width: 2 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59,130,246,0.3)' },
            { offset: 1, color: 'rgba(59,130,246,0.02)' },
          ]) },
        },
        {
          name: '基准收益率',
          type: 'line',
          data: benchmarkValues,
          smooth: true,
          symbol: 'none',
          lineStyle: { color: '#ef4444', width: 2 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(239,68,68,0.15)' },
            { offset: 1, color: 'rgba(239,68,68,0.02)' },
          ]) },
        },
      ],
    }, true)
  }, [strategyReturnData, benchmarkData])

  useEffect(() => {
    const handleResize = () => instanceRef.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return (
    <div className="bg-surface-container-high rounded-lg p-4">
      <h3 className="text-sm font-medium text-on-surface mb-3">收益对比</h3>
      <div ref={chartRef} className="w-full h-[300px]" />
    </div>
  )
}
