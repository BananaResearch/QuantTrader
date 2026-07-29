"""strategy_engine 参数体系重构迁移

变更（strategy-engine-params-redesign change）：
- 删除 strategy.strategy_type 字段（如果存在）
- 新增 strategy.param_schema（JSON, NULL）——如果不存在
- 新增 strategy.account_id（BIGINT, NULL）——如果不存在
- 新增 strategy_version.param_schema（JSON, NULL）——如果不存在
- 新增 strategy_version.runtime_config_snapshot（JSON, NULL）——如果不存在
- 新建 runtime_config_template 表

注意：迁移 4ad58868baa7（add_strategy_execution_tables）已部分实现了本迁移的内容
（删除了 strategy_type，添加了 param_schema/account_id/runtime_config_snapshot）。
本迁移兼容：只添加尚不存在的列/表。

Revision ID: 20260718120814
Revises: 4ad58868baa7
Create Date: 2026-07-18 12:08:14.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260718120814"
down_revision = "4ad58868baa7"
branch_labels = None
depends_on = None


def column_exists(table: str, column: str) -> bool:
    """检查列是否存在"""
    r = op.get_bind().execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name=:tbl AND column_name=:col "
            "LIMIT 1"
        ),
        {"tbl": table, "col": column},
    )
    return r.fetchone() is not None


def table_exists(table: str) -> bool:
    """检查表是否存在"""
    r = op.get_bind().execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema=DATABASE() AND table_name=:tbl LIMIT 1"
        ),
        {"tbl": table},
    )
    return r.fetchone() is not None


def upgrade() -> None:
    # 1. 删除 strategy.strategy_type（如果存在）
    if column_exists("strategy", "strategy_type"):
        try:
            op.execute("DROP INDEX idx_strategy_type ON strategy")
        except Exception:
            pass
        with op.batch_alter_table("strategy") as batch:
            batch.drop_column("strategy_type")

    # 2. 新增 strategy 字段（幂等）
    if not column_exists("strategy", "param_schema"):
        with op.batch_alter_table("strategy") as batch:
            batch.add_column(
                sa.Column("param_schema", sa.JSON(), nullable=True, comment="参数 Schema 定义")
            )
    if not column_exists("strategy", "account_id"):
        with op.batch_alter_table("strategy") as batch:
            batch.add_column(
                sa.Column("account_id", sa.BigInteger(), nullable=True, comment="实盘账户 FK（弱引用）")
            )

    # 3. 新增 strategy_version 字段（幂等）
    if not column_exists("strategy_version", "param_schema"):
        with op.batch_alter_table("strategy_version") as batch:
            batch.add_column(
                sa.Column("param_schema", sa.JSON(), nullable=True, comment="Schema 快照")
            )
    if not column_exists("strategy_version", "runtime_config_snapshot"):
        with op.batch_alter_table("strategy_version") as batch:
            batch.add_column(
                sa.Column("runtime_config_snapshot", sa.JSON(), nullable=True, comment="运行配置快照（仅作复现参考）")
            )

    # 4. 新建 runtime_config_template 表（幂等）
    if not table_exists("runtime_config_template"):
        op.create_table(
            "runtime_config_template",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(64), nullable=False, comment="模板名称"),
            sa.Column("description", sa.String(256), nullable=True, comment="描述"),
            sa.Column("mode", sa.String(16), nullable=False, comment="backtest/paper/live"),
            sa.Column("universe", sa.JSON(), nullable=False, comment="标的列表"),
            sa.Column("start_date", sa.Date(), nullable=True, comment="仅 backtest 用"),
            sa.Column("end_date", sa.Date(), nullable=True, comment="仅 backtest 用"),
            sa.Column("initial_capital", sa.Numeric(18, 2), nullable=False, server_default=sa.text("1000000.00"), comment="初始资金"),
            sa.Column("frequency", sa.String(8), nullable=False, server_default=sa.text("'daily'"), comment="数据频率"),
            sa.Column("slippage", sa.Numeric(6, 4), nullable=False, server_default=sa.text("0.0003"), comment="滑点"),
            sa.Column("commission", sa.Numeric(6, 4), nullable=False, server_default=sa.text("0.0001"), comment="佣金"),
            sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="系统预设"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("idx_runtime_config_mode", "runtime_config_template", ["mode"])
        op.create_index("idx_runtime_config_default", "runtime_config_template", ["is_default"])

        # 种子数据
        op.execute("""
            INSERT INTO `runtime_config_template`
              (`name`, `description`, `mode`, `universe`, `start_date`, `end_date`,
               `initial_capital`, `frequency`, `slippage`, `commission`, `is_default`)
            VALUES
              ('沪深300-近1年-100w-日线',
               '默认回测模板，沪深 5 只代表性股票，1 年日线数据',
               'backtest',
               '["000001.SZ", "600000.SH", "600519.SH", "000858.SZ", "002594.SZ"]',
               '2025-07-18', '2026-07-18',
               1000000.00, 'daily', 0.0003, 0.0001, 1),
              ('沪深300-近3年-100w-日线',
               '长期回测模板，适合观察跨周期表现',
               'backtest',
               '["000001.SZ", "600000.SH", "600519.SH"]',
               '2023-07-18', '2026-07-18',
               1000000.00, 'daily', 0.0003, 0.0001, 1),
              ('保守实盘',
               '低资金保守配置，适合实盘验证',
               'live', '[]', NULL, NULL,
               100000.00, 'daily', 0.0001, 0.00005, 1),
              ('激进实盘',
               '高资金配置，适合大资金实盘',
               'live', '[]', NULL, NULL,
               1000000.00, 'daily', 0.0005, 0.0002, 1)
        """)


def downgrade() -> None:
    # 删除种子数据
    op.execute("DELETE FROM `runtime_config_template` WHERE `is_default` = 1")

    # 删除表
    if table_exists("runtime_config_template"):
        try:
            op.drop_index("idx_runtime_config_default", table_name="runtime_config_template")
        except Exception:
            pass
        try:
            op.drop_index("idx_runtime_config_mode", table_name="runtime_config_template")
        except Exception:
            pass
        op.drop_table("runtime_config_template")

    # 删除 strategy_version 新增字段
    for col in ("runtime_config_snapshot", "param_schema"):
        if column_exists("strategy_version", col):
            try:
                with op.batch_alter_table("strategy_version") as batch:
                    batch.drop_column(col)
            except Exception:
                pass

    # 删除 strategy 新增字段
    for col in ("account_id", "param_schema"):
        if column_exists("strategy", col):
            try:
                with op.batch_alter_table("strategy") as batch:
                    batch.drop_column(col)
            except Exception:
                pass

    # 重建 strategy_type 列（老数据会丢失）
    if not column_exists("strategy", "strategy_type"):
        with op.batch_alter_table("strategy") as batch:
            batch.add_column(
                sa.Column(
                    "strategy_type",
                    sa.String(32),
                    nullable=True,
                    comment="策略类型：trend/mean_reversion/arbitrage/sentiment",
                )
            )
        try:
            op.create_index("idx_strategy_type", "strategy", ["strategy_type"], unique=False)
        except Exception:
            pass
