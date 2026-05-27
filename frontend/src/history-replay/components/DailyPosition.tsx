import { useReplayRuntime } from '../hooks/useReplay'

/** 每日持仓 & 收益表 */
export default function DailyPosition() {
  const data = useReplayRuntime((s) => s.dailyPositionData)

  if (data.length === 0) {
    return <div className="text-on-surface-variant text-sm py-8 text-center">暂无持仓数据</div>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-outline-variant">
            <th className="text-left py-2 px-3 text-on-surface-variant font-medium">日期</th>
            <th className="text-right py-2 px-3 text-on-surface-variant font-medium">持仓数量</th>
            <th className="text-right py-2 px-3 text-on-surface-variant font-medium">持仓市值</th>
            <th className="text-right py-2 px-3 text-on-surface-variant font-medium">当日盈亏</th>
            <th className="text-right py-2 px-3 text-on-surface-variant font-medium">当日收益率</th>
            <th className="text-right py-2 px-3 text-on-surface-variant font-medium">总资产</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.time} className="border-b border-outline-variant/50 hover:bg-surface-container-highest/50">
              <td className="py-2 px-3 text-on-surface">{row.time}</td>
              <td className="py-2 px-3 text-right font-mono-num text-on-surface">
                {row.quantity > 0 ? row.quantity.toLocaleString() : '-'}
              </td>
              <td className="py-2 px-3 text-right font-mono-num text-on-surface">
                {row.quantity > 0 ? `¥${row.market_value.toLocaleString()}` : '-'}
              </td>
              <td className={`py-2 px-3 text-right font-mono-num ${row.daily_pnl >= 0 ? 'text-up' : 'text-down'}`}>
                {row.daily_pnl >= 0 ? '+' : ''}¥{row.daily_pnl.toLocaleString()}
              </td>
              <td className={`py-2 px-3 text-right font-mono-num ${row.daily_return_pct >= 0 ? 'text-up' : 'text-down'}`}>
                {row.daily_return_pct >= 0 ? '+' : ''}{row.daily_return_pct.toFixed(2)}%
              </td>
              <td className="py-2 px-3 text-right font-mono-num text-on-surface">
                ¥{row.total_equity.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
