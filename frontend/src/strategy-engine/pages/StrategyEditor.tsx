/**
 * 策略编辑器。
 *
 * 功能：
 * - URL ?id=xxx 加载已有策略 / ?new=1 新建策略
 * - Monaco 代码编辑器（Python 语法 + 项目暗色主题）
 * - 参数 Schema 编辑器（结构化表单） + 参数值表单
 * - 运行配置选择器（模板 + 临时覆盖）
 * - 校验按钮 / 试运行按钮 / 保存按钮
 * - dryRun=1 URL 参数：加载完成后自动触发试运行
 * - Cmd/Ctrl+S 快捷键保存
 * - 未保存修改提示（beforeunload + React Router blocker）
 *
 * 路由：/strategy-editor
 */

import { AppLayout } from '@/common/components'
import {
  AlertCircle,
  ArrowLeft,
  Brain,
  HelpCircle,
  Loader2,
  PlayCircle,
  Save,
  ShieldCheck,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'

import {
  createStrategy,
  dryRunStrategy,
  getStrategy,
  updateStrategy,
  validateStrategyCode,
} from '../api/strategy'
import { CodeEditor } from '../components/CodeEditor'
import { ParamSchemaEditor } from '../components/ParamSchemaEditor'
import { ParamValueForm } from '../components/ParamValueForm'
import { RuntimeConfigSelector } from '../components/RuntimeConfigSelector'
import { Sparkline } from '../components/Sparkline'
import { StrategyTemplatePicker } from '../components/StrategyTemplatePicker'
import { ToasterProvider, useToaster } from '../components/Toaster'
import { Tooltip } from '../components/Tooltip'
import { ValidationPanel } from '../components/ValidationPanel'
import { useKeyboardShortcut } from '../hooks/useKeyboardShortcut'
import { useUnsavedChanges } from '../hooks/useUnsavedChanges'
import type {
  DryRunRequestInput,
  DryRunResult,
  ParamSchema,
  RuntimeConfigTemplate,
  Strategy,
  StrategyStatus,
  StrategyTemplateItem,
  StrategyValidateResult,
} from '../types/strategy'

type Mode = 'loading' | 'create' | 'edit'

type RightTab = 'params' | 'runtime' | 'result'

// 默认代码模板（无模板时填入编辑器）
const DEFAULT_CODE_TEMPLATE = `# 策略说明：用 JoinQuant 风格 DSL 编写
# 必需钩子：initialize / handle_data
# 可选钩子：before_trading_start / control_risk
# 内置 API：g / context / data / log / get_history / order / order_value / order_target
# 允许 import：math / statistics / datetime / decimal / json / collections

def initialize(context):
    g.security = context.universe[0]
    g.window = 5


def handle_data(context, data):
    security = context.universe[0] if context.universe else None
    if not security:
        return

    df = get_history(g.window + 5, '1d', 'close', security, fq='qfq', include=True)
    if not df or 'close' not in df or len(df['close']) < g.window:
        return

    closes = df['close']
    ma = sum(closes[-g.window:]) / g.window
    price = data[security]['close']

    if price > ma and context.portfolio.cash > 10000:
        order_value(security, context.portfolio.cash * 0.5)
        log.info('价格 %.2f 上穿 MA%d %.2f，买入' % (price, g.window, ma))
    elif price < ma:
        pos = context.portfolio.positions.get(security)
        if pos and pos.quantity > 0:
            order_target(security, 0)
            log.info('价格 %.2f 下穿 MA%d %.2f，卖出' % (price, g.window, ma))


def control_risk(context):
    pass
`

const inputClass =
  'h-9 px-3 rounded-md border border-outline bg-surface-container text-sm text-on-surface outline-none focus:border-primary transition-colors w-full'

const selectClass =
  'h-9 px-3 rounded-md border border-outline bg-surface-container text-sm text-on-surface outline-none focus:border-primary transition-colors'

// dirty 快照字段
interface DirtySnapshot {
  code: string
  name: string
  codeField: string
  status: StrategyStatus
  version: string
  description: string
  paramSchema: ParamSchema | undefined | null
  parameters: Record<string, unknown> | null
  runtimeTemplateId: number | null
  runtimeOverride: Partial<RuntimeConfigTemplate> | null
}

export default function StrategyEditor() {
  return (
    <ToasterProvider>
      <StrategyEditorInner />
    </ToasterProvider>
  )
}

function StrategyEditorInner() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const strategyIdParam = searchParams.get('id')
  const isNew = searchParams.get('new') === '1'
  const autoDryRun = searchParams.get('dryRun') === '1'

  const { toast } = useToaster()

  const [mode, setMode] = useState<Mode>('loading')
  const [strategyId, setStrategyId] = useState<number | null>(
    strategyIdParam ? Number(strategyIdParam) : null,
  )

  // 表单字段
  const [code, setCode] = useState<string>(DEFAULT_CODE_TEMPLATE)
  const [name, setName] = useState<string>('')
  const [codeField, setCodeField] = useState<string>('') // 策略编码
  const [status, setStatus] = useState<StrategyStatus>('draft')
  const [version, setVersion] = useState<string>('1.0.0')
  const [description, setDescription] = useState<string>('')
  const [paramSchema, setParamSchema] = useState<ParamSchema | undefined | null>(undefined)
  const [parameters, setParameters] = useState<Record<string, unknown> | null>(null)

  // 运行配置（试运行用）
  const [runtimeTemplateId, setRuntimeTemplateId] = useState<number | null>(null)
  const [runtimeOverride, setRuntimeOverride] = useState<Partial<RuntimeConfigTemplate> | null>(null)

  // 操作状态
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [dryRunning, setDryRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 结果
  const [validation, setValidation] = useState<StrategyValidateResult | null>(null)
  const [dryRunResult, setDryRunResult] = useState<DryRunResult | null>(null)

  // 弹窗状态
  const [showTemplatePicker, setShowTemplatePicker] = useState(false)

  // 右侧 Tab
  const [activeTab, setActiveTab] = useState<RightTab>('params')

  // 用户是否手动改过 codeField（用于模板 code 视觉提示 4.5）
  const [codeFieldTouched, setCodeFieldTouched] = useState(false)

  // 自动触发 dryRun 标志（加载完成后消费）
  const autoDryRunTriggeredRef = useRef(false)

  // === dirty 快照（用 useState 而非 useRef，避免 render 阶段访问 ref） ===
  const [snapshot, setSnapshot] = useState<DirtySnapshot>({
    code: DEFAULT_CODE_TEMPLATE,
    name: '',
    codeField: '',
    status: 'draft',
    version: '1.0.0',
    description: '',
    paramSchema: undefined,
    parameters: null,
    runtimeTemplateId: null,
    runtimeOverride: null,
  })

  const isDirty = useMemo(() => {
    const s = snapshot
    return (
      s.code !== code ||
      s.name !== name ||
      s.codeField !== codeField ||
      s.status !== status ||
      s.version !== version ||
      s.description !== description ||
      JSON.stringify(s.paramSchema) !== JSON.stringify(paramSchema) ||
      JSON.stringify(s.parameters) !== JSON.stringify(parameters) ||
      s.runtimeTemplateId !== runtimeTemplateId ||
      JSON.stringify(s.runtimeOverride) !== JSON.stringify(runtimeOverride)
    )
  }, [
    snapshot,
    code,
    name,
    codeField,
    status,
    version,
    description,
    paramSchema,
    parameters,
    runtimeTemplateId,
    runtimeOverride,
  ])

  useUnsavedChanges({ isDirty, enabled: !saving })

  const markClean = useCallback(() => {
    setSnapshot( {
      code,
      name,
      codeField,
      status,
      version,
      description,
      paramSchema,
      parameters,
      runtimeTemplateId,
      runtimeOverride,
    })
  }, [
    code,
    name,
    codeField,
    status,
    version,
    description,
    paramSchema,
    parameters,
    runtimeTemplateId,
    runtimeOverride,
  ])

  // === 新建流程：弹出模板选择器 ===
  useEffect(() => {
    if (isNew) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setShowTemplatePicker(true)
    }
  }, [isNew])

  const handleTemplatePick = useCallback(
    (tpl: StrategyTemplateItem) => {
      setShowTemplatePicker(false)
      setMode('create')
      setName('')
      setCodeField(tpl.code || '')
      setCodeFieldTouched(false) // 模板预填，未手动改过
      setStatus('draft')
      setVersion('1.0.0')
      setDescription('')
      if (tpl.is_blank) {
        setParamSchema({ fields: [] })
        setParameters(null)
        setCode(DEFAULT_CODE_TEMPLATE)
      } else {
        setParamSchema(tpl.param_schema ?? { fields: [] })
        setParameters(tpl.parameters ?? null)
        setCode(tpl.code_content || DEFAULT_CODE_TEMPLATE)
      }
      // 同步 dirty 快照（避免模板预填触发 dirty）
      setSnapshot( {
        code: tpl.is_blank ? DEFAULT_CODE_TEMPLATE : tpl.code_content || DEFAULT_CODE_TEMPLATE,
        name: '',
        codeField: tpl.code || '',
        status: 'draft',
        version: '1.0.0',
        description: '',
        paramSchema: tpl.is_blank ? { fields: [] } : tpl.param_schema ?? { fields: [] },
        parameters: tpl.is_blank ? null : tpl.parameters ?? null,
        runtimeTemplateId: null,
        runtimeOverride: null,
      })
    },
    [],
  )

  // 模板选择器关闭：停留在编辑器（4.6），不跳转 /strategies
  const handleTemplatePickerClose = useCallback(() => {
    setShowTemplatePicker(false)
    setMode('create')
    setName('')
    setCodeField('')
    setCodeFieldTouched(false)
    setStatus('draft')
    setVersion('1.0.0')
    setDescription('')
    setParamSchema({ fields: [] })
    setParameters(null)
    setCode(DEFAULT_CODE_TEMPLATE)
    setSnapshot( {
      code: DEFAULT_CODE_TEMPLATE,
      name: '',
      codeField: '',
      status: 'draft',
      version: '1.0.0',
      description: '',
      paramSchema: { fields: [] },
      parameters: null,
      runtimeTemplateId: null,
      runtimeOverride: null,
    })
  }, [])

  // === 加载策略 ===
  useEffect(() => {
    if (isNew) {
      // 模板选择器接管初始化
      return
    }
    if (strategyId == null) {
      navigate('/strategies')
      return
    }

    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const s: Strategy = await getStrategy(strategyId)
        if (cancelled) return
        setName(s.name)
        setCodeField(s.code)
        setStatus(s.status)
        setVersion(s.version)
        setDescription(s.description ?? '')
        setParamSchema(s.param_schema ?? null)
        setParameters(s.parameters ?? null)
        setCode(s.code_content ?? DEFAULT_CODE_TEMPLATE)
        setMode('edit')
        // 同步 dirty 快照
        setSnapshot( {
          code: s.code_content ?? DEFAULT_CODE_TEMPLATE,
          name: s.name,
          codeField: s.code,
          status: s.status,
          version: s.version,
          description: s.description ?? '',
          paramSchema: s.param_schema ?? null,
          parameters: s.parameters ?? null,
          runtimeTemplateId: null,
          runtimeOverride: null,
        })
      } catch (err) {
        if (cancelled) return
        // 页面级阻塞错误：保留 setError
        const msg = err instanceof Error ? err.message : '加载策略失败'
        setError(msg)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [strategyId, isNew, navigate])

  // === 加载完成后自动 dry-run ===
  // 注意：handleDryRun 在下方定义，这里用 useRef 持有 latest 引用以避免"accessed before declared"错误
  const handleDryRunRef = useRef<() => void>(() => {})
  useEffect(() => {
    if (!autoDryRun || autoDryRunTriggeredRef.current) return
    if (mode !== 'edit' || strategyId == null) return
    if (status !== 'active') {
      toast('info', '仅 active 策略可试运行，请先启用')
      autoDryRunTriggeredRef.current = true
      return
    }
    autoDryRunTriggeredRef.current = true
    handleDryRunRef.current()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoDryRun, mode, strategyId, status])

  // === 校验 ===
  const handleValidate = useCallback(async () => {
    setValidating(true)
    setError(null)
    try {
      const result = await validateStrategyCode({ code_content: code })
      setValidation(result)
      if (result.valid) {
        toast('success', '校验通过')
      } else {
        toast('error', `发现 ${result.errors.length} 个错误`)
        setActiveTab('result')
      }
    } catch (err) {
      // 操作级错误：只走 toast
      const msg = err instanceof Error ? err.message : '校验请求失败'
      toast('error', msg)
    } finally {
      setValidating(false)
    }
  }, [code, toast])

  // === 试运行 ===
  const handleDryRun = useCallback(async () => {
    if (strategyId == null) {
      toast('error', '请先保存策略')
      return
    }
    if (status !== 'active') {
      toast('error', '仅 active 策略可试运行')
      return
    }
    if (runtimeTemplateId == null) {
      toast('error', '请先选择运行配置模板')
      return
    }
    setDryRunning(true)
    setError(null)
    setDryRunResult(null)
    try {
      const payload: DryRunRequestInput = {
        template_id: runtimeTemplateId,
        override: runtimeOverride ?? undefined,
        max_bars: 60,
        parameters: parameters ?? undefined,
      }
      const result = await dryRunStrategy(strategyId, payload)
      setDryRunResult(result)
      setActiveTab('result')
      toast(
        'success',
        `试运行完成：${result.total_bars} bar，收益 ${result.total_return_pct > 0 ? '+' : ''}${result.total_return_pct}%`,
      )
    } catch (err) {
      const msg = err instanceof Error ? err.message : '试运行失败'
      toast('error', msg)
    } finally {
      setDryRunning(false)
    }
  }, [strategyId, status, runtimeTemplateId, runtimeOverride, parameters, toast])

  // 同步 handleDryRun 到 ref（供 autoDryRun useEffect 调用，避免"used before declared"）
  useEffect(() => {
    handleDryRunRef.current = handleDryRun
  })

  // === BUG-STR-004：WebSocket 订阅 code_updated ===
  // 仅 edit 模式 + 已有 strategyId 时订阅；断线指数退避重连；收到推送时刷新 code_content
  useEffect(() => {
    if (mode !== 'edit' || strategyId == null) return

    let ws: WebSocket | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null
    let retryDelay = 1000 // 初始 1s
    let closed = false

    const connect = () => {
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${proto}//${window.location.host}/ws/strategy/${strategyId}`
      ws = new WebSocket(url)

      ws.onmessage = async (evt) => {
        try {
          const msg = JSON.parse(evt.data)
          if (msg.type === 'code_updated') {
            // 本地有未保存改动时不自动覆盖，仅提示
            if (isDirty) {
              toast('info', '策略已被他人更新，请保存或刷新')
              return
            }
            try {
              const s = await getStrategy(strategyId)
              setCode(s.code_content ?? DEFAULT_CODE_TEMPLATE)
              setParameters(s.parameters ?? null)
              toast('info', '策略已被他人更新')
            } catch {
              toast('error', '拉取最新策略失败')
            }
          }
        } catch {
          // ping/pong 等非 JSON 消息忽略
        }
      }

      ws.onclose = () => {
        if (closed) return
        // 指数退避重连，最大 30s
        retryTimer = setTimeout(() => {
          retryDelay = Math.min(retryDelay * 2, 30000)
          connect()
        }, retryDelay)
      }

      ws.onerror = () => {
        // 错误由 onclose 统一处理
        ws?.close()
      }
    }

    connect()

    return () => {
      closed = true
      if (retryTimer) clearTimeout(retryTimer)
      if (ws) {
        ws.onclose = null
        ws.close()
      }
    }
  }, [mode, strategyId, isDirty, toast])

  // === 保存 ===
  const handleSave = useCallback(async () => {
    if (!name.trim()) {
      toast('error', '策略名称不能为空')
      return
    }
    if (!codeField.trim() && mode === 'create') {
      toast('error', '策略编码不能为空（如 DOUBLE_MA）')
      return
    }
    if (codeField && !/^[A-Z][A-Z0-9_]{2,63}$/.test(codeField)) {
      toast('error', '编码格式：大写字母开头+数字/下划线，3~64 字符')
      return
    }

    setSaving(true)
    setError(null)
    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || undefined,
        status,
        version,
        code_content: code,
        param_schema: paramSchema ?? undefined,
        parameters: parameters ?? undefined,
        // create 模式需要 code 字段，edit 模式不需要
        ...(mode === 'create' ? { code: codeField } : {}),
      }
      if (mode === 'create') {
        const created = await createStrategy(payload as Parameters<typeof createStrategy>[0])
        setStrategyId(created.id)
        setMode('edit')
        markClean()
        toast('success', `策略已创建（id=${created.id}）`)
        navigate(`/strategy-editor?id=${created.id}`, { replace: true })
      } else if (mode === 'edit' && strategyId != null) {
        await updateStrategy(strategyId, payload as Parameters<typeof updateStrategy>[1])
        markClean()
        toast('success', '策略已更新')
      }
    } catch (err) {
      // BUG-STR-001：优先读取后端返回的 detail / message，避免只显示 axios 默认文本
      const axErr = err as { response?: { data?: { detail?: string; message?: string } } }
      const msg =
        axErr?.response?.data?.detail ??
        axErr?.response?.data?.message ??
        (err instanceof Error ? err.message : '保存失败')
      toast('error', msg)
    } finally {
      setSaving(false)
    }
  }, [name, codeField, description, status, version, code, paramSchema, parameters, mode, strategyId, toast, navigate, markClean])

  // === Cmd+S 快捷键 ===
  useKeyboardShortcut({
    combo: 'mod+s',
    handler: () => void handleSave(),
    enabled: mode !== 'loading' && !saving,
    preventDefault: true,
  })

  // === 派生值 ===
  const charCount = useMemo(() => code.length, [code])
  const lineCount = useMemo(() => code.split('\n').length, [code])

  // 4.2 试运行 disabled 原因
  const dryRunDisabledReason = useMemo(() => {
    if (dryRunning) return '试运行中...'
    if (mode !== 'edit') return '请先保存策略'
    if (status !== 'active') return '状态需改为「已启用」'
    if (runtimeTemplateId == null) return '请选择运行配置模板'
    return null
  }, [dryRunning, mode, status, runtimeTemplateId])

  // 校验/警告总数（Tab badge）
  const totalIssues = (validation?.errors.length ?? 0) + (validation?.warnings.length ?? 0)

  // codeField 视觉提示（来自模板且用户未改过）
  const codeFieldFromTemplate = mode === 'create' && !!codeField && !codeFieldTouched

  return (
    <AppLayout>
      {/* 模板选择器弹窗 */}
      {showTemplatePicker && (
        <StrategyTemplatePicker
          onPick={handleTemplatePick}
          onClose={handleTemplatePickerClose}
        />
      )}

      <div className="min-h-full p-6 space-y-4">
        {/* 顶部：返回 + 标题 + 操作 */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate('/strategies')}
              className="p-2 rounded-md hover:bg-surface-container text-on-surface-variant hover:text-on-surface transition-colors"
              title="返回策略列表"
              aria-label="返回策略列表"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="w-9 h-9 rounded-lg bg-primary/20 flex items-center justify-center">
              <Brain className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-on-surface">
                {mode === 'create' ? '新建策略' : name || '未命名策略'}
                {mode === 'edit' && codeField && (
                  <code className="ml-2 px-1.5 py-0.5 text-xs rounded border border-outline-variant/40 bg-surface-container text-on-surface-variant font-mono">
                    {codeField}
                  </code>
                )}
                {mode === 'edit' && (
                  <span
                    className={`ml-2 px-1.5 py-0.5 text-xs rounded-full border ${
                      status === 'active'
                        ? 'bg-success/15 text-success border-success/30'
                        : status === 'archived'
                          ? 'bg-on-surface-variant/15 text-on-surface-variant border-outline'
                          : 'bg-warning/15 text-warning border-warning/30'
                    }`}
                  >
                    {status === 'active' ? '已启用' : status === 'archived' ? '已归档' : '草稿'}
                  </span>
                )}
              </h1>
              <p className="text-xs text-on-surface-variant">
                {mode === 'edit' && strategyId != null && (
                  <>ID {strategyId} · {lineCount} 行 · {charCount} 字符 · </>
                )}
                {mode === 'create' ? '新建模式' : '编辑模式'}
                {isDirty && <span className="text-warning ml-1">· 未保存</span>}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void handleValidate()}
              disabled={validating}
              className="px-3 h-9 rounded-md border border-outline bg-surface-container hover:bg-surface-container-highest text-on-surface text-sm transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {validating ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              校验
            </button>
            <Tooltip content={dryRunDisabledReason ?? '基于 mock 数据跑 60 bar'}>
              <button
                type="button"
                onClick={() => void handleDryRun()}
                disabled={dryRunDisabledReason !== null}
                className="px-3 h-9 rounded-md border border-outline bg-surface-container hover:bg-surface-container-highest text-on-surface text-sm transition-colors flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {dryRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />}
                试运行
              </button>
            </Tooltip>
            <button
              type="button"
              onClick={() => void handleSave()}
              disabled={saving}
              className="px-4 h-9 rounded-md bg-primary hover:bg-primary-container text-primary-foreground text-sm font-medium transition-colors flex items-center gap-1.5 disabled:opacity-50"
              title="Cmd/Ctrl+S"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {mode === 'create' ? '创建' : '保存'}
            </button>
          </div>
        </div>

        {/* 错误提示（仅页面级阻塞错误） */}
        {error && (
          <div className="p-3 rounded-md border border-error/30 bg-error/10 text-error flex items-center gap-2 text-sm">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="break-all">{error}</span>
          </div>
        )}

        {/* 主体：左编辑器 + 右侧栏（4.1 断点改为 xl） */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* 左侧：基础信息 + 代码 */}
          <div className="xl:col-span-2 space-y-4">
            {/* 基础信息表单 */}
            <div className="bg-surface-container-high rounded-lg border border-outline-variant/20 p-4 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="flex items-center gap-1 text-xs text-on-surface-variant mb-1">
                    <span>策略名称 *</span>
                    <Tooltip content="1-128 字符">
                      <HelpCircle className="w-3 h-3 cursor-help opacity-60" />
                    </Tooltip>
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="如：双均线交叉"
                    maxLength={128}
                    className={inputClass}
                    aria-label="策略名称"
                  />
                </div>
                <div>
                  <label className="flex items-center gap-1 text-xs text-on-surface-variant mb-1">
                    <span>策略编码 *</span>
                    <Tooltip content="大写字母开头+数字/下划线，3-64 字符；保存后不可修改">
                      <HelpCircle className="w-3 h-3 cursor-help opacity-60" />
                    </Tooltip>
                  </label>
                  <input
                    type="text"
                    value={codeField}
                    onChange={(e) => {
                      setCodeField(e.target.value.toUpperCase())
                      setCodeFieldTouched(true)
                    }}
                    placeholder="如：DOUBLE_MA"
                    disabled={mode === 'edit'}
                    maxLength={64}
                    aria-label="策略编码"
                    className={`${inputClass} font-mono ${
                      codeFieldFromTemplate ? 'border-warning/50' : ''
                    }`}
                  />
                  {codeFieldFromTemplate && (
                    <p className="text-xs text-warning mt-1">来自模板，保存后不可修改</p>
                  )}
                </div>
                <div>
                  <label className="flex items-center gap-1 text-xs text-on-surface-variant mb-1">
                    <span>状态</span>
                    <Tooltip content="draft=草稿 / active=已启用（仅 active 可试运行与实盘执行）/ archived=已归档">
                      <HelpCircle className="w-3 h-3 cursor-help opacity-60" />
                    </Tooltip>
                  </label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value as StrategyStatus)}
                    className={selectClass}
                    aria-label="策略状态"
                  >
                    <option value="draft">草稿</option>
                    <option value="active">已启用</option>
                    <option value="archived">已归档</option>
                  </select>
                </div>
                <div>
                  <label className="flex items-center gap-1 text-xs text-on-surface-variant mb-1">
                    <span>版本号</span>
                    <Tooltip content="语义化版本号 1.0.0">
                      <HelpCircle className="w-3 h-3 cursor-help opacity-60" />
                    </Tooltip>
                  </label>
                  <input
                    type="text"
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                    placeholder="1.0.0"
                    maxLength={32}
                    className={`${inputClass} font-mono`}
                    aria-label="版本号"
                  />
                </div>
                <div className="col-span-2">
                  <label className="flex items-center gap-1 text-xs text-on-surface-variant mb-1">
                    <span>描述</span>
                  </label>
                  <input
                    type="text"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="简短说明策略逻辑"
                    className={inputClass}
                    aria-label="策略描述"
                  />
                </div>
              </div>
            </div>

            {/* Monaco 编辑器 */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-1 text-xs text-on-surface-variant">
                  <span>策略代码（Python DSL）</span>
                  <Tooltip content="用 JoinQuant 风格 DSL 编写，必需 initialize / handle_data">
                    <HelpCircle className="w-3 h-3 cursor-help opacity-60" />
                  </Tooltip>
                </label>
                <div className="text-xs text-on-surface-variant font-mono-num">
                  {lineCount} 行 · {charCount} 字符
                </div>
              </div>
              {loading ? (
                <div className="h-[480px] flex items-center justify-center bg-surface-container-lowest border border-outline-variant/20 rounded-md text-on-surface-variant text-sm">
                  <Loader2 className="w-5 h-5 animate-spin mr-2" />
                  加载策略代码...
                </div>
              ) : (
                <CodeEditor
                  value={code}
                  onChange={setCode}
                  errors={validation?.errors ?? []}
                  warnings={validation?.warnings ?? []}
                  minHeight={520}
                />
              )}
            </div>
          </div>

          {/* 右侧：3 Tab 布局 */}
          <div className="bg-surface-container-high rounded-lg border border-outline-variant/20 overflow-hidden flex flex-col min-h-[600px]">
            {/* Tab 头 */}
            <div className="flex border-b border-outline-variant/20 shrink-0">
              <TabButton
                active={activeTab === 'params'}
                onClick={() => setActiveTab('params')}
                badge={undefined}
              >
                参数
              </TabButton>
              <TabButton active={activeTab === 'runtime'} onClick={() => setActiveTab('runtime')}>
                运行
              </TabButton>
              <TabButton
                active={activeTab === 'result'}
                onClick={() => setActiveTab('result')}
                badge={totalIssues > 0 ? totalIssues : undefined}
              >
                结果
              </TabButton>
            </div>

            {/* Tab 内容 */}
            <div className="flex-1 overflow-y-auto p-4">
              {activeTab === 'params' && (
                <div className="space-y-4">
                  <div>
                    <ParamSchemaEditor
                      value={paramSchema}
                      onChange={setParamSchema}
                      disabled={mode === 'loading'}
                    />
                  </div>
                  <div className="border-t border-outline-variant/20 pt-4 space-y-2">
                    <div className="text-xs text-on-surface-variant">参数值</div>
                    {mode === 'create' ? (
                      <div className="text-xs text-on-surface-variant py-3 text-center border border-dashed border-outline-variant/30 rounded-md">
                        先保存参数 Schema 后再填值（切到编辑模式后生效）
                      </div>
                    ) : (
                      <ParamValueForm
                        schema={paramSchema ?? undefined}
                        value={parameters}
                        onChange={setParameters}
                        disabled={mode === 'loading'}
                      />
                    )}
                  </div>
                </div>
              )}

              {activeTab === 'runtime' && (
                <RuntimeConfigSelector
                  templateId={runtimeTemplateId}
                  override={runtimeOverride}
                  onChange={(id, override) => {
                    setRuntimeTemplateId(id)
                    setRuntimeOverride(override ?? null)
                  }}
                />
              )}

              {activeTab === 'result' && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center gap-1.5 text-xs text-on-surface-variant">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>校验结果</span>
                    </div>
                    <ValidationPanel result={validation} loading={validating} />
                  </div>
                  <div className="border-t border-outline-variant/20 pt-4 space-y-3">
                    <div className="flex items-center gap-1.5 text-xs text-on-surface-variant">
                      <PlayCircle className="w-3.5 h-3.5" />
                      <span>试运行结果</span>
                    </div>
                    <DryRunResultView result={dryRunResult} loading={dryRunning} />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

// ============================================================
// Tab 按钮
// ============================================================

function TabButton({
  active,
  onClick,
  children,
  badge,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
  badge?: number
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2.5 text-xs font-medium transition-colors border-b-2 ${
        active
          ? 'text-primary border-primary bg-surface-container/50'
          : 'text-on-surface-variant border-transparent hover:text-on-surface hover:bg-surface-container/30'
      }`}
    >
      {children}
      {badge != null && (
        <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-error/20 text-error border border-error/30">
          {badge}
        </span>
      )}
    </button>
  )
}

// ============================================================
// 试运行结果视图
// ============================================================

function DryRunResultView({
  result,
  loading,
}: {
  result: DryRunResult | null
  loading: boolean
}) {
  if (loading) {
    return (
      <div className="text-xs text-on-surface-variant flex items-center gap-2">
        <Loader2 className="w-3 h-3 animate-spin" />
        试运行中（基于 mock 数据）...
      </div>
    )
  }
  if (!result) {
    return (
      <div className="text-xs text-on-surface-variant">
        点击「试运行」使用选定的运行配置跑 mock 数据，验证策略能否产生订单。
      </div>
    )
  }

  const profit = result.total_return_pct >= 0
  const orders = result.bars.reduce((sum, b) => sum + b.orders_count, 0)

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <MetricCell label="总收益" value={`${profit ? '+' : ''}${result.total_return_pct}%`} profit={profit} />
        <MetricCell
          label="期末资产"
          value={result.final_capital.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}
        />
        <MetricCell label="Bar 数" value={`${result.total_bars}`} />
        <MetricCell label="订单数" value={`${orders}`} />
      </div>

      {result.bars.length > 0 && (
        <Sparkline points={result.bars.map((b) => b.total_assets)} positive={profit} />
      )}

      <div className="text-xs text-on-surface-variant">
        Session: <code className="font-mono">{result.session_id}</code>
      </div>
    </div>
  )
}

function MetricCell({
  label,
  value,
  profit,
}: {
  label: string
  value: string
  profit?: boolean
}) {
  return (
    <div className="bg-surface-container-lowest rounded px-2.5 py-1.5">
      <div className="text-xs text-on-surface-variant">{label}</div>
      <div
        className={`text-sm font-semibold font-mono-num ${
          profit === true ? 'text-up' : profit === false ? 'text-down' : 'text-on-surface'
        }`}
      >
        {value}
      </div>
    </div>
  )
}

// ============================================================
// 试运行结果视图
// ============================================================
