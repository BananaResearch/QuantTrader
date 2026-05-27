import { useEffect, useRef, useCallback, useState } from 'react'
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type DeepPartial,
  type CandlestickStyleOptions,
  type HistogramStyleOptions,
  ColorType,
} from 'lightweight-charts'
import { Play, Pause, Square } from 'lucide-react'
import { cn } from '@/common/utils'
import { useReplayRuntime } from '../hooks/useReplay'
import type { KlineBar, TradeSignal } from '../types'

const SPEED_OPTIONS = [1, 2, 4, 8] as const

export function ReplayChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markersRef = useRef<any>(null)

  const runtime = useReplayRuntime()
  const { klineData, signals, status, speed } = runtime
  const hasData = klineData.length > 0
  const [chartReady, setChartReady] = useState(false)

  // 初始化图表（仅在 hasData 变为 true 且容器存在时）
  useEffect(() => {
    if (!hasData || !chartContainerRef.current) return

    // 如果图表已存在，先销毁重建
    if (chartRef.current) {
      chartRef.current.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
      markersRef.current = null
    }

    const container = chartContainerRef.current
    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: '#12121a' },
        textColor: '#9ca3af',
        fontSize: 12,
      },
      grid: {
        vertLines: { color: '#1e1e30' },
        horzLines: { color: '#1e1e30' },
      },
      crosshair: {
        vertLine: { color: '#3b82f6', width: 1, style: 2 },
        horzLine: { color: '#3b82f6', width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: '#1e1e30',
      },
      timeScale: {
        borderColor: '#1e1e30',
        timeVisible: true,
      },
    })

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#ef4444',
      downColor: '#22c55e',
      borderUpColor: '#ef4444',
      borderDownColor: '#22c55e',
      wickUpColor: '#ef4444',
      wickDownColor: '#22c55e',
    } as DeepPartial<CandlestickStyleOptions>)

    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    } as DeepPartial<HistogramStyleOptions>)

    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    })

    chartRef.current = chart
    candleSeriesRef.current = candleSeries
    volumeSeriesRef.current = volumeSeries
    setChartReady(true)

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        })
      }
    }
    window.addEventListener('resize', handleResize)
    handleResize()

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
      candleSeriesRef.current = null
      volumeSeriesRef.current = null
      markersRef.current = null
      setChartReady(false)
    }
  }, [hasData])

  // 数据更新
  useEffect(() => {
    if (!chartReady || !candleSeriesRef.current || !volumeSeriesRef.current || klineData.length === 0) return

    const candleData = klineData.map((bar: KlineBar) => ({
      time: bar.time,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }))

    const volumeData = klineData.map((bar: KlineBar) => ({
      time: bar.time,
      value: bar.volume,
      color: bar.close >= bar.open ? 'rgba(239,68,68,0.3)' : 'rgba(34,197,94,0.3)',
    }))

    candleSeriesRef.current.setData(candleData as never)
    volumeSeriesRef.current.setData(volumeData as never)

    // 设置买卖标记
    if (signals.length > 0 && candleSeriesRef.current) {
      const markers = signals.map((s: TradeSignal) => ({
        time: s.time,
        position: s.side === 'buy' ? 'belowBar' as const : 'aboveBar' as const,
        color: s.side === 'buy' ? '#ef4444' : '#22c55e',
        shape: s.side === 'buy' ? 'arrowUp' as const : 'arrowDown' as const,
        text: s.side === 'buy' ? `买 ${s.signal}` : `卖 ${s.signal}`,
      }))
      if (markersRef.current) {
        markersRef.current.setMarkers(markers as never)
      } else {
        markersRef.current = createSeriesMarkers(candleSeriesRef.current, markers as never)
      }
    }

    // 自适应缩放
    chartRef.current?.timeScale().fitContent()
  }, [chartReady, klineData, signals])

  // 控制按钮
  const handlePlay = useCallback(() => {
    if (status === 'running') {
      runtime.controlReplay('pause')
    } else if (status === 'paused') {
      runtime.controlReplay('resume')
    }
  }, [status, runtime])

  const handleStop = useCallback(() => {
    runtime.controlReplay('stop')
  }, [runtime])

  const handleSpeedChange = useCallback(
    (s: 1 | 2 | 4 | 8) => {
      runtime.setSpeed(s)
    },
    [runtime]
  )

  return (
    <div className="bg-surface-container-high rounded-lg shadow-card overflow-hidden flex flex-col">
      {/* 图表区 */}
      <div className="relative flex-1 min-h-[380px]">
        {hasData && <div ref={chartContainerRef} className="absolute inset-0" />}
        {!hasData && (
          <div className="absolute inset-0 flex items-center justify-center text-on-surface-variant text-sm">
            配置参数后点击「开始回测」查看K线
          </div>
        )}
      </div>

      {/* 播放控制条 */}
      {hasData && (
        <div className="h-11 bg-surface-container flex items-center px-4 gap-3 border-t border-outline-variant/20">
          {/* 播放/暂停 */}
          <button
            onClick={handlePlay}
            className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-surface-container-high transition-colors"
            title={status === 'running' ? '暂停' : '继续'}
          >
            {status === 'running' ? (
              <Pause className="w-4 h-4 text-on-surface" />
            ) : (
              <Play className="w-4 h-4 text-on-surface" />
            )}
          </button>

          {/* 停止 */}
          <button
            onClick={handleStop}
            className="w-8 h-8 flex items-center justify-center rounded-md hover:bg-surface-container-high transition-colors"
            title="停止"
          >
            <Square className="w-4 h-4 text-on-surface" />
          </button>

          {/* 分隔 */}
          <div className="w-px h-5 bg-outline-variant/30" />

          {/* 速度选择 */}
          {SPEED_OPTIONS.map((s) => (
            <button
              key={s}
              onClick={() => handleSpeedChange(s)}
              className={cn(
                'px-2 py-0.5 rounded text-xs font-medium transition-colors',
                speed === s
                  ? 'bg-primary text-on-primary'
                  : 'text-on-surface-variant hover:bg-surface-container-high'
              )}
            >
              {s}x
            </button>
          ))}

          {/* 分隔 */}
          <div className="w-px h-5 bg-outline-variant/30" />

          {/* 状态信息 */}
          <div className="ml-auto text-xs text-on-surface-variant font-mono-num">
            {runtime.currentIndex} / {runtime.totalBars}
          </div>
        </div>
      )}
    </div>
  )
}
