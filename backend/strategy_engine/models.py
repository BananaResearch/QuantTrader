"""strategy_engine 模块的 SQLAlchemy ORM 模型。

模型：
- Strategy：策略主档（当前生效代码 + 参数）
- StrategyVersion：策略版本快照

变更说明（vs 旧 `_db.py`）：
- 表名保持单数 `strategy` / `strategy_version`（与原设计一致）
- Strategy 删除冗余字段 entry_rules / exit_rules / risk_rules（DSL 全在 code_content）
- Strategy 新增 code_content 字段（当前生效代码）
- 统一使用 common.database.Base/TimestampMixin（不再重复定义 Base/engine/session）
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Boolean, String, Text, UniqueConstraint, Index, DECIMAL, Date, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base, TimestampMixin


class Strategy(Base, TimestampMixin):
    """策略主档。"""

    __tablename__ = "strategy"
    __table_args__ = (
        UniqueConstraint("code", name="uk_strategy_code"),
        # idx_strategy_type 已通过 Alembic 迁移删除（strategy_type 字段移除）
        Index("idx_strategy_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), comment="策略编码")
    name: Mapped[str] = mapped_column(String(128), comment="策略名称")
    # 注意：strategy_type 字段已删除（见 strategy-engine-params-redesign change）
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="策略描述")
    status: Mapped[str] = mapped_column(String(16), default="draft", comment="状态：draft/active/archived")
    version: Mapped[str] = mapped_column(String(32), default="1.0.0", comment="当前版本号")
    code_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="当前生效的 Python 策略代码")
    param_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="参数 Schema 定义")
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="基于 Schema 的参数值")
    account_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, comment="实盘账户 FK（弱引用）")
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, comment="标签数组")
    author: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, comment="创建者")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否默认策略")


class StrategyVersion(Base, TimestampMixin):
    """策略版本快照。每次保存策略代码变更时插入一条。"""

    __tablename__ = "strategy_version"
    __table_args__ = (
        UniqueConstraint("strategy_id", "version", name="uk_strategy_version"),
        Index("ix_sv_strategy", "strategy_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(comment="关联 strategy.id")
    version: Mapped[str] = mapped_column(String(32), comment="版本号")
    change_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="变更日志")
    code_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="代码快照")
    param_schema: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="Schema 快照")
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="参数值快照")
    runtime_config_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="运行配置快照（仅作复现参考）")
    status: Mapped[str] = mapped_column(String(16), default="active", comment="状态：active/historical")
    backtest_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="该版本的回测结果摘要")


class RuntimeConfigTemplate(Base, TimestampMixin):
    """运行配置模板（业务上下文预设）。"""

    __tablename__ = "runtime_config_template"
    __table_args__ = (
        Index("idx_runtime_config_mode", "mode"),
        Index("idx_runtime_config_default", "is_default"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), comment="模板名称")
    description: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, comment="描述")
    mode: Mapped[str] = mapped_column(String(16), comment="backtest/paper/live")
    universe: Mapped[list] = mapped_column(JSON, comment="标的列表")
    start_date: Mapped[Optional[object]] = mapped_column(Date, nullable=True, comment="仅 backtest 用")
    end_date: Mapped[Optional[object]] = mapped_column(Date, nullable=True, comment="仅 backtest 用")
    initial_capital: Mapped[float] = mapped_column(DECIMAL(18, 2), default=1000000.0, comment="初始资金")
    frequency: Mapped[str] = mapped_column(String(8), default="daily", comment="数据频率")
    slippage: Mapped[float] = mapped_column(DECIMAL(6, 4), default=0.0003, comment="滑点")
    commission: Mapped[float] = mapped_column(DECIMAL(6, 4), default=0.0001, comment="佣金")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="系统预设")


__all__ = ["Strategy", "StrategyVersion", "RuntimeConfigTemplate"]
