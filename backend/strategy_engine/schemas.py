"""strategy_engine 模块的 Pydantic 请求/响应 Schema。

变更说明（strategy-engine-params-redesign）：
- 删除 strategy_type 字段（strategy-crud delta spec）
- 新增 param_schema 字段（strategy-param-schema spec）
- 新增 RuntimeConfigTemplate CRUD Schema（runtime-config-template spec）
- dry-run 接口签名变更（template_id + override 替代硬编码 stock_code/date）
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ============================================================
# 枚举类（strategy-param-schema / runtime-config-template spec）
# ============================================================

class ParamFieldType(str, Enum):
    """参数字段类型"""
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    SELECT = "select"
    STOCK_CODE = "stock_code"
    LIST = "list"


class RuntimeMode(str, Enum):
    """运行配置模式"""
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class DataFrequency(str, Enum):
    """数据频率"""
    DAILY = "daily"
    MIN1 = "1min"
    MIN5 = "5min"
    MIN15 = "15min"
    MIN30 = "30min"
    MIN60 = "60min"


# ============================================================
# 参数 Schema（strategy-param-schema spec）
# ============================================================

class ParamFieldSchema(BaseModel):
    """单个参数字段的 Schema 定义"""
    key: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9_]{0,63}$",
        description="参数键名（小写字母开头，含下划线/数字，1~64 字符）",
    )
    type: ParamFieldType
    label: str = Field(..., max_length=64, description="展示标签")
    description: Optional[str] = Field(None, max_length=256, description="帮助文本")
    default: Optional[Any] = None
    min: Optional[float] = None
    max: Optional[float] = None
    max_length: Optional[int] = Field(None, gt=0, le=4096, description="string 类型最大长度")
    options: Optional[list[dict[str, Any]]] = None  # [{label, value}]
    item_type: Optional[ParamFieldType] = Field(None, description="仅 list 类型使用")
    group: Optional[str] = Field(None, max_length=32, description="分组名称")
    required: bool = False

    @model_validator(mode="after")
    def validate_type_consistency(self):
        # select 类型必须提供 options
        if self.type == ParamFieldType.SELECT:
            if not self.options:
                raise ValueError("select 类型必须提供 options")
            # options.value 唯一性
            values = [opt.get("value") for opt in self.options]
            if len(values) != len(set(values)):
                raise ValueError("select options 的 value 重复")
        # list 类型必须提供 item_type
        if self.type == ParamFieldType.LIST:
            if not self.item_type:
                raise ValueError("list 类型必须提供 item_type")
            if self.item_type in (ParamFieldType.LIST, ParamFieldType.SELECT, ParamFieldType.BOOL):
                raise ValueError("item_type 不允许为 list/select/bool")
        # min <= max
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise ValueError("min 不能大于 max")
        return self


class ParamSchema(BaseModel):
    """参数 Schema 容器"""
    fields: list[ParamFieldSchema] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_keys(self):
        keys = [f.key for f in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError(f"参数键名重复: {[k for k in keys if keys.count(k) > 1]}")
        return self


# ============================================================
# 策略主档（删除 strategy_type，新增 param_schema/account_id）
# ============================================================

CODE_PATTERN = r"^[A-Z][A-Z0-9_]{2,63}$"


class StrategyBase(BaseModel):
    """策略基础字段（创建/响应共享）。

    注意：strategy_type 字段已删除（见 strategy-crud delta spec）。
    """
    code: str = Field(..., pattern=CODE_PATTERN, max_length=64, description="策略编码")
    name: str = Field(..., min_length=1, max_length=128, description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    status: str = Field(default="draft", max_length=16, description="状态：draft/active/archived")
    version: str = Field(default="1.0.0", max_length=32, description="当前版本号")
    code_content: Optional[str] = Field(None, max_length=50000, description="当前生效的 Python 策略代码")
    param_schema: Optional[ParamSchema] = Field(None, description="参数 Schema 定义")
    parameters: Optional[dict[str, Any]] = Field(None, description="基于 Schema 的参数值")
    account_id: Optional[int] = Field(None, description="实盘账户 FK（弱引用）")
    tags: Optional[list[str]] = None
    author: Optional[str] = Field(None, max_length=64)
    is_default: bool = False


class StrategyCreate(StrategyBase):
    """创建策略请求。"""


class StrategyUpdate(BaseModel):
    """更新策略请求（部分更新）。"""
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    status: Optional[str] = Field(None, max_length=16)
    version: Optional[str] = Field(None, max_length=32)
    code_content: Optional[str] = Field(None, max_length=50000)
    param_schema: Optional[ParamSchema] = None
    parameters: Optional[dict[str, Any]] = None
    account_id: Optional[int] = None
    tags: Optional[list[str]] = None
    author: Optional[str] = Field(None, max_length=64)
    is_default: Optional[bool] = None


class StrategyResponse(StrategyBase):
    """策略响应。"""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 策略版本（新增 param_schema / runtime_config_snapshot）
# ============================================================

class StrategyVersionBase(BaseModel):
    strategy_id: Optional[int] = None  # 从 URL 路径获取，不在 request body 中
    version: str = Field(..., max_length=32)
    change_log: Optional[str] = None
    code_content: Optional[str] = None
    param_schema: Optional[ParamSchema] = None  # 新增：Schema 快照
    parameters: Optional[dict[str, Any]] = None
    runtime_config_snapshot: Optional[dict[str, Any]] = None  # 新增：运行配置快照
    status: str = Field(default="active", max_length=16)
    backtest_result: Optional[dict[str, Any]] = None


class StrategyVersionCreate(StrategyVersionBase):
    pass


class StrategyVersionResponse(StrategyVersionBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 简化列表（strategy_type 已删除）
# ============================================================

class StrategyOption(BaseModel):
    """策略简化字段，用于下拉框填充。

    注意：strategy_type 字段已删除。
    """
    id: int
    name: str
    description: Optional[str] = None


# ============================================================
# 校验与试运行
# ============================================================

class StrategyValidateRequest(BaseModel):
    """策略代码语法 + 沙箱加载校验请求。"""
    code_content: str = Field(..., min_length=1, max_length=50000)
    parameters: Optional[dict[str, Any]] = None


class ValidationIssue(BaseModel):
    """校验问题项。"""
    line: Optional[int] = None
    column: Optional[int] = None
    severity: str  # "error" / "warning"
    code: str      # "SYNTAX_ERROR" / "FORBIDDEN_IMPORT" / "MISSING_HOOK" / ...
    message: str


class StrategyValidateResponse(BaseModel):
    """策略校验响应。"""
    valid: bool
    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []


class DryRunRequest(BaseModel):
    """策略试运行请求（签名变更：template_id + override 替代硬编码字段）。"""
    template_id: int = Field(..., description="运行配置模板 ID")
    override: Optional[dict[str, Any]] = Field(None, description="临时覆盖字段（仅允许 universe/start_date/end_date/initial_capital/frequency/slippage/commission）")
    max_bars: int = Field(default=60, ge=1, le=1000, description="最大 bar 数")
    parameters: Optional[dict[str, Any]] = Field(None, description="临时覆盖策略参数值")
    save_snapshot: bool = Field(default=False, description="是否保存运行配置快照到最新版本")


class DryRunBarSummary(BaseModel):
    """试运行 bar 简化结构。"""
    time: str
    close: float
    total_assets: float
    signal: Optional[str] = None
    orders_count: int = 0


class DryRunResponse(BaseModel):
    """试运行响应。"""
    session_id: str
    total_bars: int
    time_elapsed: float
    final_capital: float
    total_return_pct: float
    bars: list[DryRunBarSummary]


# ============================================================
# RuntimeConfigTemplate CRUD（runtime-config-template spec）
# ============================================================

class RuntimeConfigTemplateCreate(BaseModel):
    """创建运行配置模板请求。"""
    name: str = Field(..., max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    mode: RuntimeMode
    universe: list[str] = Field(..., min_length=1, description="标的列表")
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    initial_capital: Decimal = Field(default=Decimal("1000000"), gt=0)
    frequency: DataFrequency = DataFrequency.DAILY
    slippage: Decimal = Field(default=Decimal("0.0003"), ge=Decimal("0"), lt=Decimal("1"))
    commission: Decimal = Field(default=Decimal("0.0001"), ge=Decimal("0"), lt=Decimal("1"))

    @model_validator(mode="after")
    def validate_backtest_dates(self):
        if self.mode == RuntimeMode.BACKTEST:
            if not self.start_date or not self.end_date:
                raise ValueError("backtest 模式必须提供 start_date/end_date")
            if self.start_date >= self.end_date:
                raise ValueError("start_date 必须早于 end_date")
        else:
            if self.start_date is not None or self.end_date is not None:
                raise ValueError("live/paper 模式不允许设置 start_date/end_date")
        return self


class RuntimeConfigTemplateUpdate(BaseModel):
    """更新运行配置模板请求（系统预设禁止）。"""
    name: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=256)
    universe: Optional[list[str]] = Field(None, min_length=1)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    initial_capital: Optional[Decimal] = Field(None, gt=Decimal("0"))
    frequency: Optional[DataFrequency] = None
    slippage: Optional[Decimal] = Field(None, ge=Decimal("0"), lt=Decimal("1"))
    commission: Optional[Decimal] = Field(None, ge=Decimal("0"), lt=Decimal("1"))


class RuntimeConfigTemplateResponse(BaseModel):
    """运行配置模板响应。"""
    id: int
    name: str
    description: Optional[str] = None
    mode: str
    universe: list[str]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    initial_capital: Decimal
    frequency: str
    slippage: Decimal
    commission: Decimal
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 策略模板列表（用于新建策略时的模板选择器）
# ============================================================

class StrategyTemplateItem(BaseModel):
    """内置策略模板项（来自 builtin/）"""
    code: str = Field(..., description="策略编码")
    name: str
    description: str
    code_content: str
    param_schema: Optional[ParamSchema] = None
    parameters: Optional[dict[str, Any]] = None
    is_blank: bool = Field(False, description="是否空白模板")


# ============================================================
# P3: 并发回测（保留，与本次 change 无冲突）
# ============================================================

class BatchBacktestRequest(BaseModel):
    """并发回测请求。"""
    strategy_ids: list[int] = Field(..., min_length=1, max_length=10)
    stock_code: str = Field(..., max_length=20)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    timeframe: str = Field("1d")


class BatchBacktestResponse(BaseModel):
    """并发回测响应。"""
    results: list[dict]


# ============================================================
# P3: 版本对比（保留，与本次 change 无冲突）
# ============================================================

class CompareRequest(BaseModel):
    """版本对比请求。"""
    version_ids: list[int] = Field(..., min_length=2, max_length=2)
    stock_code: str = Field(..., max_length=20)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    timeframe: str = Field("1d")


class CompareResponse(BaseModel):
    """版本对比响应。"""
    version_1: dict
    version_2: dict
    diff: dict


# ============================================================
# P3: 策略导出/导入（strategy_type 字段从 Schema 中移除）
# ============================================================

class ExportRequest(BaseModel):
    """策略导出请求。"""
    strategy_ids: list[int] = Field(..., min_length=1)
    include_versions: bool = False


class ExportResponse(BaseModel):
    """策略导出响应。"""
    strategies: list[dict]


class StrategyImportItem(BaseModel):
    """单个策略导入数据（strategy_type 字段已移除）。"""
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    description: Optional[str] = None
    code_content: str = Field(...)
    param_schema: Optional[ParamSchema] = None
    parameters: Optional[dict[str, Any]] = None
    version: str = Field("1.0.0", max_length=32)
    versions: Optional[list[dict]] = None


class ImportRequest(BaseModel):
    """策略导入请求。"""
    strategies: list[StrategyImportItem] = Field(..., min_length=1)


class ImportResponse(BaseModel):
    """策略导入响应。"""
    imported: int
    skipped: int
    skipped_codes: list[str] = []


__all__ = [
    # 枚举
    "ParamFieldType",
    "RuntimeMode",
    "DataFrequency",
    # 参数 Schema
    "ParamFieldSchema",
    "ParamSchema",
    # 策略主档
    "StrategyBase",
    "StrategyCreate",
    "StrategyUpdate",
    "StrategyResponse",
    # 策略版本
    "StrategyVersionBase",
    "StrategyVersionCreate",
    "StrategyVersionResponse",
    # 简化列表
    "StrategyOption",
    # 校验与试运行
    "StrategyValidateRequest",
    "ValidationIssue",
    "StrategyValidateResponse",
    "DryRunRequest",
    "DryRunBarSummary",
    "DryRunResponse",
    # RuntimeConfigTemplate
    "RuntimeConfigTemplateCreate",
    "RuntimeConfigTemplateUpdate",
    "RuntimeConfigTemplateResponse",
    # 策略模板
    "StrategyTemplateItem",
    # P3 扩展
    "BatchBacktestRequest",
    "BatchBacktestResponse",
    "CompareRequest",
    "CompareResponse",
    "ExportRequest",
    "ExportResponse",
    "StrategyImportItem",
    "ImportRequest",
    "ImportResponse",
]
