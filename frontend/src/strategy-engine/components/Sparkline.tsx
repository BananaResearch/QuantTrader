/**
 * Sparkline — 迷你资产曲线图。
 *
 * 颜色语义（中国惯例）：
 * - 上涨（positive=true）→ text-up（红色 #ef4444）
 * - 下跌（positive=false）→ text-down（绿色 #22c55e）
 *
 * 用 currentColor + 父容器 className 控制颜色，避免硬编码。
 */

interface SparklineProps {
  points: number[]
  positive: boolean
}

export function Sparkline({ points, positive }: SparklineProps) {
  if (points.length < 2) return null
  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1
  const W = 200
  const H = 40
  const path = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * W
      const y = H - ((p - min) / range) * H
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
  // 红涨绿跌（中国惯例）：上涨=text-up（红），下跌=text-down（绿）
  const colorClass = positive ? 'text-up' : 'text-down'

  return (
    <svg
      width={W}
      height={H}
      className={`w-full ${colorClass}`}
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={positive ? '资产曲线（上涨）' : '资产曲线（下跌）'}
      data-testid="sparkline"
      data-positive={positive ? 'true' : 'false'}
    >
      <title>{positive ? '上涨' : '下跌'}资产曲线</title>
      <path d={path} fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}
