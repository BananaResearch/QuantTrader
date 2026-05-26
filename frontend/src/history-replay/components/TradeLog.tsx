import { cn } from '@/common/utils'
import { formatNumber } from '@/common/utils/format'
import { useReplayRuntime } from '../hooks/useReplay'
import type { TradeRecord } from '../types'

export function TradeLog() {
  const { trades } = useReplayRuntime()

  if (trades.length === 0) {
    return (
      <div className="bg-surface-container-high rounded-lg shadow-card p-5">
        <h3 className="text-sm font-semibold mb-4">交易记录</h3>
        <div className="text-sm text-on-surface-variant text-center py-8">
          启动回测后显示交易记录
        </div>
      </div>
    )
  }

  return (
    <div className="bg-surface-container-high rounded-lg shadow-card overflow-hidden">
      <div className="px-5 pt-4 pb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold">交易记录</h3>
        <span className="text-xs text-on-surface-variant">共 {trades.length} 笔</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-on-surface-variant text-xs border-b border-outline-variant/20">
              <th className="text-left py-2.5 px-5 font-medium">时间</th>
              <th className="text-left py-2.5 px-3 font-medium">方向</th>
              <th className="text-left py-2.5 px-3 font-medium">股票代码</th>
              <th className="text-right py-2.5 px-3 font-medium">价格</th>
              <th className="text-right py-2.5 px-3 font-medium">数量</th>
              <th className="text-right py-2.5 px-3 font-medium">金额</th>
              <th className="text-right py-2.5 px-3 font-medium">盈亏</th>
              <th className="text-right py-2.5 px-3 font-medium">手续费</th>
              <th className="text-left py-2.5 px-3 font-medium">信号</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/20">
            {trades.map((trade: TradeRecord) => (
              <TradeRow key={trade.id} trade={trade} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TradeRow({ trade }: { trade: TradeRecord }) {
  const isBuy = trade.side === 'buy'

  return (
    <tr className="hover:bg-surface-container-highest transition-colors">
      <td className="py-2.5 px-5 text-on-surface-variant">{trade.time}</td>
      <td className="py-2.5 px-3">
        <span
          className={cn(
            'text-xs px-1.5 py-0.5 rounded font-medium',
            isBuy ? 'bg-up/15 text-up' : 'bg-down/15 text-down'
          )}
        >
          {isBuy ? '买入' : '卖出'}
        </span>
      </td>
      <td className="py-2.5 px-3 font-medium">{trade.stock_code}</td>
      <td className="py-2.5 px-3 text-right font-mono-num">{formatNumber(trade.price)}</td>
      <td className="py-2.5 px-3 text-right font-mono-num">{trade.quantity.toLocaleString()}</td>
      <td className="py-2.5 px-3 text-right font-mono-num">{formatNumber(trade.amount)}</td>
      <td
        className={cn(
          'py-2.5 px-3 text-right font-mono-num',
          trade.pnl > 0 ? 'text-up' : trade.pnl < 0 ? 'text-down' : 'text-on-surface-variant'
        )}
      >
        {trade.pnl > 0 ? '+' : ''}{formatNumber(trade.pnl)}
      </td>
      <td className="py-2.5 px-3 text-right font-mono-num text-on-surface-variant">
        {formatNumber(trade.commission)}
      </td>
      <td className="py-2.5 px-3 text-on-surface-variant text-xs">{trade.signal}</td>
    </tr>
  )
}
