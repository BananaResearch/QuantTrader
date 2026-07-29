"""StrategyService.validate_param_values 单元测试。

覆盖 BUG-STR-012（enum）、BUG-STR-013（string max_length）、BUG-STR-014（bool 严格）以及既有类型回归。
"""

from __future__ import annotations

import pytest

from strategy_engine.exceptions import InvalidParamValue
from strategy_engine.schemas import ParamFieldSchema, ParamFieldType, ParamSchema
from strategy_engine.service import StrategyService


def _field(
    key: str,
    type_: ParamFieldType,
    *,
    required: bool = False,
    min_: float | None = None,
    max_: float | None = None,
    max_length: int | None = None,
    options: list[dict] | None = None,
    item_type: ParamFieldType | None = None,
) -> ParamFieldSchema:
    return ParamFieldSchema(
        key=key,
        type=type_,
        label=key,
        required=required,
        min=min_,
        max=max_,
        max_length=max_length,
        options=options,
        item_type=item_type,
    )


def _schema(*fields: ParamFieldSchema) -> ParamSchema:
    return ParamSchema(fields=list(fields))


class TestStringValidation:
    """BUG-STR-013：string 字段 max_length 校验。"""

    def test_string_too_long_rejected(self):
        schema = _schema(_field("tag", ParamFieldType.STRING, max_length=64))
        with pytest.raises(InvalidParamValue) as exc_info:
            StrategyService.validate_param_values(schema, {"tag": "x" * 65})
        assert "max_length" in str(exc_info.value) or "长度" in str(exc_info.value)

    def test_string_at_max_accepted(self):
        schema = _schema(_field("tag", ParamFieldType.STRING, max_length=64))
        # 不应抛异常
        StrategyService.validate_param_values(schema, {"tag": "x" * 64})

    def test_string_without_max_length_accepts_any(self):
        schema = _schema(_field("tag", ParamFieldType.STRING))
        StrategyService.validate_param_values(schema, {"tag": "x" * 10000})

    def test_string_non_str_rejected(self):
        schema = _schema(_field("tag", ParamFieldType.STRING, max_length=64))
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"tag": 123})


class TestBoolValidation:
    """BUG-STR-014：bool 字段严格类型校验。"""

    def test_bool_true_accepted(self):
        schema = _schema(_field("enabled", ParamFieldType.BOOL))
        StrategyService.validate_param_values(schema, {"enabled": True})

    def test_bool_false_accepted(self):
        schema = _schema(_field("enabled", ParamFieldType.BOOL))
        StrategyService.validate_param_values(schema, {"enabled": False})

    def test_bool_int_rejected(self):
        """int(1) 不应被接受为 bool（Python 的 isinstance(1, bool) 为 False 但 isinstance(1, int) 为 True）。"""
        schema = _schema(_field("enabled", ParamFieldType.BOOL))
        with pytest.raises(InvalidParamValue) as exc_info:
            StrategyService.validate_param_values(schema, {"enabled": 1})
        assert "布尔" in str(exc_info.value)

    def test_bool_string_rejected(self):
        schema = _schema(_field("enabled", ParamFieldType.BOOL))
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"enabled": "true"})


class TestSelectValidation:
    """BUG-STR-012：select 字段 enum 校验（回归）。"""

    def test_select_valid_value_accepted(self):
        schema = _schema(
            _field(
                "mode",
                ParamFieldType.SELECT,
                options=[
                    {"label": "Fast", "value": "fast"},
                    {"label": "Slow", "value": "slow"},
                ],
            )
        )
        StrategyService.validate_param_values(schema, {"mode": "fast"})

    def test_select_invalid_value_rejected(self):
        schema = _schema(
            _field(
                "mode",
                ParamFieldType.SELECT,
                options=[
                    {"label": "Fast", "value": "fast"},
                    {"label": "Slow", "value": "slow"},
                ],
            )
        )
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"mode": "unknown"})


class TestIntRangeValidation:
    """回归：int 字段 min/max 范围。"""

    def test_int_in_range_accepted(self):
        schema = _schema(_field("period", ParamFieldType.INT, min_=2, max_=100))
        StrategyService.validate_param_values(schema, {"period": 20})

    def test_int_below_min_rejected(self):
        schema = _schema(_field("period", ParamFieldType.INT, min_=2, max_=100))
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"period": 1})

    def test_int_above_max_rejected(self):
        schema = _schema(_field("period", ParamFieldType.INT, min_=2, max_=100))
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"period": 101})

    def test_int_rejects_bool(self):
        """bool 是 int 的子类，需显式排除。"""
        schema = _schema(_field("period", ParamFieldType.INT))
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"period": True})


class TestListValidation:
    """回归：list 字段递归校验。"""

    def test_list_of_stock_code_accepted(self):
        schema = _schema(
            _field(
                "symbols",
                ParamFieldType.LIST,
                item_type=ParamFieldType.STOCK_CODE,
            )
        )
        StrategyService.validate_param_values(
            schema, {"symbols": ["000001.SZ", "600000.SH"]}
        )

    def test_list_of_stock_code_rejects_invalid(self):
        schema = _schema(
            _field(
                "symbols",
                ParamFieldType.LIST,
                item_type=ParamFieldType.STOCK_CODE,
            )
        )
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(
                schema, {"symbols": ["000001.SZ", "INVALID"]}
            )


class TestRequiredValidation:
    """回归：required 字段缺失。"""

    def test_required_missing_rejected(self):
        schema = _schema(_field("threshold", ParamFieldType.FLOAT, required=True))
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {})

    def test_optional_missing_accepted(self):
        schema = _schema(_field("threshold", ParamFieldType.FLOAT))
        StrategyService.validate_param_values(schema, {})


class TestExtraFieldsTolerated:
    """向前兼容：Schema 未声明的字段允许存在。"""

    def test_extra_field_accepted(self):
        schema = _schema(_field("tag", ParamFieldType.STRING, max_length=64))
        StrategyService.validate_param_values(
            schema, {"tag": "ok", "unknown_field": "anything"}
        )
