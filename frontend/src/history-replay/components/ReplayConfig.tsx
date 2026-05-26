import { useState, useRef, useEffect, useCallback } from 'react'
import { Search, Play } from 'lucide-react'
import { cn } from '@/common/utils'
import { useReplayConfig, useReplayOptions, useReplayRuntime } from '../hooks/useReplay'
import type { TimeFrame, StockOption } from '../types'

const TIMEFRAME_OPTIONS: { value: TimeFrame; label: string; group: string }[] = [
  { value: '1m', label: '1分钟', group: '分钟级' },
  { value: '5m', label: '5分钟', group: '分钟级' },
  { value: '15m', label: '15分钟', group: '分钟级' },
  { value: '30m', label: '30分钟', group: '分钟级' },
  { value: '1h', label: '1小时', group: '小时级' },
  { value: '4h', label: '4小时', group: '小时级' },
  { value: '1d', label: '日线', group: '日级' },
]

export function ReplayConfig() {
  const config = useReplayConfig()
  const options = useReplayOptions()
  const runtime = useReplayRuntime()
  const isRunning = runtime.status === 'running' || runtime.status === 'paused'

  useEffect(() => {
    options.fetchStrategies()
    options.fetchAccounts()
  }, [options.fetchStrategies, options.fetchAccounts])

  return (
    <div className="bg-surface-container-high rounded-lg p-4 shadow-card">
      <div className="flex items-end gap-4 flex-wrap">
        {/* 股票代码搜索 */}
        <StockSearchInput
          value={config.stockCode ? `${config.stockCode} ${config.stockName}` : ''}
          onChange={(code, name) => config.setStockCode(code, name)}
          disabled={isRunning}
        />

        {/* 策略选择 */}
        <SelectField
          label="策略"
          value={config.strategyId ?? ''}
          options={options.strategies.map((s) => ({ value: s.id, label: s.name }))}
          placeholder="选择策略"
          onChange={(v) => config.setStrategyId(Number(v))}
          disabled={isRunning}
        />

        {/* 虚拟账户 */}
        <SelectField
          label="虚拟账户"
          value={config.accountId ?? ''}
          options={options.accounts.map((a) => ({
            value: a.id,
            label: `${a.name} (¥${a.initial_capital.toLocaleString()})`,
          }))}
          placeholder="选择账户"
          onChange={(v) => config.setAccountId(Number(v))}
          disabled={isRunning}
        />

        {/* 时间间隔 */}
        <SelectField
          label="时间间隔"
          value={config.timeframe}
          options={TIMEFRAME_OPTIONS.map((t) => ({ value: t.value, label: t.label }))}
          onChange={(v) => config.setTimeframe(v as TimeFrame)}
          disabled={isRunning}
        />

        {/* 起始日期 */}
        <DateField
          label="起始日期"
          value={config.startDate}
          onChange={config.setStartDate}
          disabled={isRunning}
        />

        {/* 结束日期 */}
        <DateField
          label="结束日期"
          value={config.endDate}
          onChange={config.setEndDate}
          disabled={isRunning}
        />

        {/* 开始回测 */}
        <button
          onClick={() => runtime.startReplay()}
          disabled={
            !config.stockCode ||
            !config.strategyId ||
            !config.accountId ||
            runtime.loading ||
            isRunning
          }
          className={cn(
            'h-9 px-5 rounded-md text-sm font-medium flex items-center gap-2 transition-colors shrink-0',
            'bg-primary text-on-primary hover:bg-primary-container',
            'disabled:opacity-40 disabled:cursor-not-allowed'
          )}
        >
          <Play className="w-3.5 h-3.5" />
          {runtime.loading ? '启动中...' : '开始回测'}
        </button>
      </div>
    </div>
  )
}

// === 股票搜索输入框 ===

function StockSearchInput({
  value,
  onChange,
  disabled,
}: {
  value: string
  onChange: (code: string, name: string) => void
  disabled?: boolean
}) {
  const [keyword, setKeyword] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [results, setResults] = useState<StockOption[]>([])
  const wrapperRef = useRef<HTMLDivElement>(null)
  const searchStocks = useReplayOptions.getState().searchStocks
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 点击外部关闭下拉
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleInput = useCallback(
    (val: string) => {
      setKeyword(val)
      if (debounceRef.current) clearTimeout(debounceRef.current)
      if (!val.trim()) {
        setResults([])
        setIsOpen(false)
        return
      }
      debounceRef.current = setTimeout(async () => {
        await searchStocks(val)
        const stocks = useReplayOptions.getState().stocks
        setResults(stocks)
        setIsOpen(stocks.length > 0)
      }, 300)
    },
    [searchStocks]
  )

  const handleSelect = (stock: StockOption) => {
    setKeyword('')
    setIsOpen(false)
    onChange(stock.code, stock.name)
  }

  return (
    <div className="relative" ref={wrapperRef}>
      <FieldLabel label="股票代码" />
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-on-surface-variant" />
        {value ? (
          <div className="h-9 pl-8 pr-3 flex items-center bg-surface-container rounded-md text-sm font-medium">
            {value}
            {!disabled && (
              <button
                onClick={() => onChange('', '')}
                className="ml-2 text-on-surface-variant hover:text-on-surface text-xs"
              >
                ✕
              </button>
            )}
          </div>
        ) : (
          <input
            type="text"
            value={keyword}
            onChange={(e) => handleInput(e.target.value)}
            onFocus={() => results.length > 0 && setIsOpen(true)}
            placeholder="搜索代码/名称/拼音"
            disabled={disabled}
            className="h-9 w-52 pl-8 pr-3 bg-surface-container rounded-md text-sm placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-40"
          />
        )}
      </div>
      {/* 搜索结果下拉 */}
      {isOpen && results.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-surface-container-highest rounded-md shadow-float z-50 border border-outline-variant/20 overflow-hidden">
          {results.map((stock) => (
            <button
              key={stock.code}
              onClick={() => handleSelect(stock)}
              className="w-full px-3 py-2 text-left text-sm hover:bg-surface-container-high transition-colors flex items-center justify-between"
            >
              <span className="font-medium">{stock.code}</span>
              <span className="text-on-surface-variant">{stock.name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// === 通用下拉选择 ===

function SelectField({
  label,
  value,
  options,
  placeholder,
  onChange,
  disabled,
}: {
  label: string
  value: string | number
  options: { value: string | number; label: string }[]
  placeholder?: string
  onChange: (value: string) => void
  disabled?: boolean
}) {
  return (
    <div>
      <FieldLabel label={label} />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="h-9 px-3 bg-surface-container rounded-md text-sm appearance-none min-w-[140px] focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-40 cursor-pointer"
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

// === 日期输入 ===

function DateField({
  label,
  value,
  onChange,
  disabled,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  disabled?: boolean
}) {
  return (
    <div>
      <FieldLabel label={label} />
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="h-9 px-3 bg-surface-container rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-40"
      />
    </div>
  )
}

// === 字段标签 ===

function FieldLabel({ label }: { label: string }) {
  return <div className="text-xs text-on-surface-variant mb-1 font-medium">{label}</div>
}
