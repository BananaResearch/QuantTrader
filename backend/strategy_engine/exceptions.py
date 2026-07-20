"""strategy_engine 模块的异常类。

按 design.md §8.1 异常体系定义。
所有异常继承 BacktestError，提供 code/http_status 字段供 router 翻译为 HTTP 响应。
"""

from __future__ import annotations


class BacktestError(Exception):
    """策略引擎模块基础异常。"""

    code: str = "STRATEGY_ERROR"
    http_status: int = 400


class StrategyNotFound(BacktestError):
    """策略不存在。"""

    code = "STRATEGY_NOT_FOUND"
    http_status = 404


class StrategyNotActive(BacktestError):
    """策略未启用（status != 'active'）。"""

    code = "STRATEGY_NOT_ACTIVE"
    http_status = 400


class StrategyLoadError(BacktestError):
    """策略代码加载失败（语法错误 / import 拦截 / 沙箱逃逸）。

    兼容 runtime/loader.py 历史用法，保留 line/original 字段。
    """

    code = "STRATEGY_LOAD_ERROR"
    http_status = 400

    def __init__(self, message: str, line: int | None = None,
                 original: Exception | None = None):
        self.line = line
        self.original = original
        super().__init__(message)


class InvalidStrategyError(BacktestError):
    """策略结构不合法（缺钩子等）。"""

    code = "INVALID_STRATEGY"
    http_status = 400


class DataUnavailableError(BacktestError):
    """行情数据不可用。"""

    code = "DATA_UNAVAILABLE"
    http_status = 503


class StrategyRuntimeError(BacktestError):
    """策略运行时异常（已翻译，含 bar 时间与原始异常摘要）。"""

    code = "STRATEGY_RUNTIME_ERROR"
    http_status = 500


class StrategyTimeoutError(BacktestError):
    """钩子执行超时。"""

    code = "STRATEGY_TIMEOUT"
    http_status = 500


# ============================================================
# strategy-engine-params-redesign 新增异常
# ============================================================

class RuntimeConfigError(BacktestError):
    """运行配置相关异常基类。"""

    code = "RUNTIME_CONFIG_ERROR"
    http_status = 400


class RuntimeConfigNotFound(RuntimeConfigError):
    """运行配置模板不存在。"""

    code = "RUNTIME_CONFIG_NOT_FOUND"
    http_status = 404


class InvalidOverrideField(RuntimeConfigError):
    """不允许覆盖的字段。"""

    code = "INVALID_OVERRIDE_FIELD"
    http_status = 400


class RuntimeConfigNameDuplicated(RuntimeConfigError):
    """模板名称重复。"""

    code = "RUNTIME_CONFIG_NAME_DUPLICATED"
    http_status = 400


class RuntimeConfigDefaultForbidden(RuntimeConfigError):
    """系统预设模板禁止操作。"""

    code = "RUNTIME_CONFIG_DEFAULT_FORBIDDEN"
    http_status = 400


class RuntimeConfigDateRequired(RuntimeConfigError):
    """backtest 模式必须提供日期范围。"""

    code = "RUNTIME_CONFIG_DATE_REQUIRED"
    http_status = 400


class RuntimeConfigDateInvalid(RuntimeConfigError):
    """日期逻辑错误。"""

    code = "RUNTIME_CONFIG_DATE_INVALID"
    http_status = 400


class InvalidParamValue(BacktestError):
    """参数值校验失败（与 Schema 不匹配）。"""

    code = "INVALID_PARAM_VALUE"
    http_status = 400


class DryRunError(BacktestError):
    """试运行失败。"""

    code = "DRY_RUN_ERROR"
    http_status = 500


__all__ = [
    "BacktestError",
    "StrategyNotFound",
    "StrategyNotActive",
    "StrategyLoadError",
    "InvalidStrategyError",
    "DataUnavailableError",
    "StrategyRuntimeError",
    "StrategyTimeoutError",
    # 新增
    "RuntimeConfigError",
    "RuntimeConfigNotFound",
    "InvalidOverrideField",
    "RuntimeConfigNameDuplicated",
    "RuntimeConfigDefaultForbidden",
    "RuntimeConfigDateRequired",
    "RuntimeConfigDateInvalid",
    "InvalidParamValue",
    "DryRunError",
]
