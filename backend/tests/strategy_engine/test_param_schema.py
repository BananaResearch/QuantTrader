"""ParamSchema / ParamFieldSchema 单元测试（strategy-engine-params-redesign）。

覆盖 strategy_param_schema spec 中的校验规则：
- ParamFieldSchema: type 一致性（select→options、list→item_type、min≤max）
- ParamSchema: 唯一 key 校验
- validate_param_values: 各类型值校验（int/float/select/stock_code/list）
"""

import pytest
from pydantic import ValidationError

from strategy_engine.schemas import (
    ParamFieldSchema,
    ParamFieldType,
    ParamSchema,
)
from strategy_engine.service import StrategyService
from strategy_engine.exceptions import InvalidParamValue


# ============================================================
# Helper
# ============================================================

def _invalid_msg(exc: Exception) -> str:
    """从 InvalidParamValue 中提取错误消息。"""
    return str(exc)


# ============================================================
# ParamFieldSchema type 一致性校验
# ============================================================

class TestParamFieldSchemaTypeConsistency:
    """select 类型必须提供 options。"""

    def test_select_missing_options_raises(self):
        """select 字段缺少 options 抛出 ValueError。"""
        with pytest.raises(ValidationError) as exc_info:
            ParamFieldSchema(
                key="mode",
                type=ParamFieldType.SELECT,
                label="运行模式",
            )
        errors = exc_info.value.errors()
        assert any("options" in e["msg"] for e in errors)

    def test_select_with_options_ok(self):
        """select 字段带 options 通过。"""
        field = ParamFieldSchema(
            key="mode",
            type=ParamFieldType.SELECT,
            label="运行模式",
            options=[{"label": "日线", "value": "daily"}, {"label": "分钟", "value": "1min"}],
        )
        assert field.type == ParamFieldType.SELECT
        assert len(field.options) == 2

    def test_select_options_value_duplicate_raises(self):
        """select options 的 value 重复抛出 ValueError。"""
        with pytest.raises(ValidationError) as exc_info:
            ParamFieldSchema(
                key="mode",
                type=ParamFieldType.SELECT,
                label="运行模式",
                options=[{"label": "A", "value": "x"}, {"label": "B", "value": "x"}],
            )
        errors = exc_info.value.errors()
        assert any("重复" in e["msg"] or "duplicate" in e["msg"].lower() for e in errors)

    def test_list_missing_item_type_raises(self):
        """list 字段缺少 item_type 抛出 ValueError。"""
        with pytest.raises(ValidationError) as exc_info:
            ParamFieldSchema(
                key="stocks",
                type=ParamFieldType.LIST,
                label="股票列表",
            )
        errors = exc_info.value.errors()
        assert any("item_type" in e["msg"] for e in errors)

    def test_list_with_item_type_ok(self):
        """list 字段带 item_type 通过。"""
        field = ParamFieldSchema(
            key="stocks",
            type=ParamFieldType.LIST,
            label="股票列表",
            item_type=ParamFieldType.STOCK_CODE,
        )
        assert field.item_type == ParamFieldType.STOCK_CODE

    def test_list_item_type_invalid_raises(self):
        """list item_type 为 list/select/bool 抛出 ValueError。"""
        for invalid_type in (ParamFieldType.LIST, ParamFieldType.SELECT, ParamFieldType.BOOL):
            with pytest.raises(ValidationError) as exc_info:
                ParamFieldSchema(
                    key="items",
                    type=ParamFieldType.LIST,
                    label="列表",
                    item_type=invalid_type,
                )
            errors = exc_info.value.errors()
            assert any("item_type" in e["msg"] for e in errors)

    def test_min_greater_than_max_raises(self):
        """min > max 抛出 ValueError。"""
        with pytest.raises(ValidationError) as exc_info:
            ParamFieldSchema(
                key="threshold",
                type=ParamFieldType.FLOAT,
                label="阈值",
                min=10.0,
                max=5.0,
            )
        errors = exc_info.value.errors()
        assert any("min" in e["msg"].lower() or "max" in e["msg"].lower() for e in errors)

    def test_min_equals_max_ok(self):
        """min == max 通过（固定值）。"""
        field = ParamFieldSchema(
            key="fixed",
            type=ParamFieldType.INT,
            label="固定值",
            min=5.0,
            max=5.0,
        )
        assert field.min == field.max == 5.0


# ============================================================
# ParamSchema 唯一 key 校验
# ============================================================

class TestParamSchemaUniqueKeys:
    """参数 Schema 中 key 必须唯一。"""

    def test_duplicate_keys_raises(self):
        """重复 key 抛出 ValueError。"""
        with pytest.raises(ValidationError) as exc_info:
            ParamSchema(
                fields=[
                    ParamFieldSchema(key="short_window", type=ParamFieldType.INT, label="短期"),
                    ParamFieldSchema(key="short_window", type=ParamFieldType.INT, label="短期重复"),
                ]
            )
        errors = exc_info.value.errors()
        assert any("重复" in e["msg"] or "duplicate" in e["msg"].lower() for e in errors)

    def test_unique_keys_ok(self):
        """唯一 key 通过。"""
        schema = ParamSchema(
            fields=[
                ParamFieldSchema(key="short_window", type=ParamFieldType.INT, label="短期"),
                ParamFieldSchema(key="long_window", type=ParamFieldType.INT, label="长期"),
            ]
        )
        assert len(schema.fields) == 2


# ============================================================
# validate_param_values 各类型校验
# ============================================================

class TestValidateParamValues:
    """StrategyService.validate_param_values() 类型校验。

    每个测试用最小 schema（只包含被测字段）避免 required 冲突。
    """

    def test_required_field_missing_raises(self):
        """必填字段缺失抛出 InvalidParamValue。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="window", type=ParamFieldType.INT, label="窗口", required=True),
        ])
        with pytest.raises(InvalidParamValue) as exc_info:
            StrategyService.validate_param_values(schema, {})
        msg = _invalid_msg(exc_info.value)
        assert "window" in msg and "必填" in msg

    def test_int_must_be_integer(self):
        """int 类型值必须为整数。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="window", type=ParamFieldType.INT, label="窗口"),
        ])
        # 浮点数
        with pytest.raises(InvalidParamValue) as exc_info:
            StrategyService.validate_param_values(schema, {"window": 5.5})
        assert "整数" in _invalid_msg(exc_info.value)
        # 布尔值
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"window": True})
        # 字符串
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"window": "5"})

    def test_int_ok(self):
        """合法整数通过。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="window", type=ParamFieldType.INT, label="窗口"),
        ])
        StrategyService.validate_param_values(schema, {"window": 5})

    def test_float_must_be_numeric(self):
        """float 类型值必须为数值。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="ratio", type=ParamFieldType.FLOAT, label="比例"),
        ])
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"ratio": "0.5"})
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"ratio": True})

    def test_float_out_of_range(self):
        """float 超出 min/max 范围抛出 InvalidParamValue。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="ratio", type=ParamFieldType.FLOAT, label="比例", min=0.0, max=1.0),
        ])
        with pytest.raises(InvalidParamValue) as exc_info:
            StrategyService.validate_param_values(schema, {"ratio": -0.1})
        assert "最小值" in _invalid_msg(exc_info.value)
        with pytest.raises(InvalidParamValue) as exc_info:
            StrategyService.validate_param_values(schema, {"ratio": 1.5})
        assert "最大值" in _invalid_msg(exc_info.value)

    def test_float_ok(self):
        """合法浮点数值通过。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="ratio", type=ParamFieldType.FLOAT, label="比例"),
        ])
        StrategyService.validate_param_values(schema, {"ratio": 0.5})

    def test_select_value_not_in_options(self):
        """select 值不在 options 中抛出 InvalidParamValue。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(
                key="mode", type=ParamFieldType.SELECT, label="模式",
                options=[{"label": "A", "value": "a"}, {"label": "B", "value": "b"}]
            ),
        ])
        with pytest.raises(InvalidParamValue) as exc_info:
            StrategyService.validate_param_values(schema, {"mode": "c"})
        assert "允许选项" in _invalid_msg(exc_info.value)

    def test_select_ok(self):
        """合法 select 值通过。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(
                key="mode", type=ParamFieldType.SELECT, label="模式",
                options=[{"label": "A", "value": "a"}, {"label": "B", "value": "b"}]
            ),
        ])
        StrategyService.validate_param_values(schema, {"mode": "a"})

    def test_stock_code_invalid_format(self):
        """stock_code 格式错误抛出 InvalidParamValue。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="stock", type=ParamFieldType.STOCK_CODE, label="股票"),
        ])
        with pytest.raises(InvalidParamValue) as exc_info:
            StrategyService.validate_param_values(schema, {"stock": "INVALID"})
        msg = _invalid_msg(exc_info.value)
        assert "格式" in msg or "匹配" in msg

    def test_stock_code_ok(self):
        """合法 stock_code 通过。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="stock", type=ParamFieldType.STOCK_CODE, label="股票"),
        ])
        for code in ["000001.SZ", "600519.SH", "830001.BJ"]:
            StrategyService.validate_param_values(schema, {"stock": code})

    def test_bool_ok(self):
        """布尔值通过。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="enabled", type=ParamFieldType.BOOL, label="启用"),
        ])
        StrategyService.validate_param_values(schema, {"enabled": True})
        StrategyService.validate_param_values(schema, {"enabled": False})

    def test_list_must_be_array(self):
        """list 类型值必须为数组。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(
                key="stocks", type=ParamFieldType.LIST, label="股票列表",
                item_type=ParamFieldType.STOCK_CODE
            ),
        ])
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"stocks": "000001.SZ"})
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"stocks": {"code": "x"}})

    def test_list_stock_code_items(self):
        """list[stock_code] 元素格式校验。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(
                key="stocks", type=ParamFieldType.LIST, label="股票列表",
                item_type=ParamFieldType.STOCK_CODE
            ),
        ])
        # 合法
        StrategyService.validate_param_values(schema, {
            "stocks": ["000001.SZ", "600519.SH"]
        })
        # 非法元素
        with pytest.raises(InvalidParamValue) as exc_info:
            StrategyService.validate_param_values(schema, {
                "stocks": ["000001.SZ", "INVALID"]
            })
        assert "格式错误" in _invalid_msg(exc_info.value)

    def test_list_int_items(self):
        """list[int] 元素类型校验。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(
                key="values", type=ParamFieldType.LIST, label="数值列表",
                item_type=ParamFieldType.INT
            ),
        ])
        # 合法
        StrategyService.validate_param_values(schema, {"values": [1, 2, 3]})
        # 非法元素
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {"values": [1, "x"]})

    def test_extra_fields_allowed(self):
        """values 可含 Schema 未声明的额外字段（向前兼容）。"""
        schema = ParamSchema(fields=[
            ParamFieldSchema(key="window", type=ParamFieldType.INT, label="窗口"),
        ])
        StrategyService.validate_param_values(schema, {
            "window": 5,
            "extra_unknown_field": "ignored",
        })  # 不抛异常


# ============================================================
# 集成：ParamSchema + validate_param_values
# ============================================================

class TestParamSchemaIntegration:
    """真实 Schema 场景集成测试。"""

    def test_double_ma_schema_validation(self):
        """双均线策略 Schema：校验合法参数。"""
        from strategy_engine.builtin import double_ma

        schema = ParamSchema.model_validate(double_ma.PARAM_SCHEMA)
        StrategyService.validate_param_values(schema, double_ma.DEFAULT_PARAMETERS)

    def test_double_ma_invalid_short_window(self):
        """双均线策略：short_window 类型错误。"""
        from strategy_engine.builtin import double_ma

        schema = ParamSchema.model_validate(double_ma.PARAM_SCHEMA)
        with pytest.raises(InvalidParamValue):
            StrategyService.validate_param_values(schema, {
                **double_ma.DEFAULT_PARAMETERS,
                "short_window": "5",  # 字符串
            })

    def test_bollinger_schema_validation(self):
        """布林带策略 Schema 校验。"""
        from strategy_engine.builtin import bollinger

        schema = ParamSchema.model_validate(bollinger.PARAM_SCHEMA)
        StrategyService.validate_param_values(schema, bollinger.DEFAULT_PARAMETERS)

    def test_rsi_schema_validation(self):
        """RSI 策略 Schema 校验。"""
        from strategy_engine.builtin import rsi

        schema = ParamSchema.model_validate(rsi.PARAM_SCHEMA)
        StrategyService.validate_param_values(schema, rsi.DEFAULT_PARAMETERS)

    def test_macd_schema_validation(self):
        """MACD 策略 Schema 校验。"""
        from strategy_engine.builtin import macd

        schema = ParamSchema.model_validate(macd.PARAM_SCHEMA)
        StrategyService.validate_param_values(schema, macd.DEFAULT_PARAMETERS)
