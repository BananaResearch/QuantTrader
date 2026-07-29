"""strategy_engine 模块的数据访问层。

变更说明（strategy-engine-params-redesign）：
- 删除 strategy_type 字段引用（strategy-crud delta spec）
- 新增 RuntimeConfigRepository（runtime-config-template spec）
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import RuntimeConfigTemplate, Strategy, StrategyVersion


class StrategyRepository:
    """策略主档 CRUD。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Strategy:
        strategy = Strategy(**data)
        self.session.add(strategy)
        await self.session.flush()
        await self.session.refresh(strategy)
        return strategy

    async def get_by_id(self, strategy_id: int) -> Optional[Strategy]:
        result = await self.session.execute(
            select(Strategy).where(Strategy.id == strategy_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[Strategy]:
        result = await self.session.execute(
            select(Strategy).where(Strategy.code == code)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Strategy]:
        """列表查询。

        注意：strategy_type 过滤参数已删除（见 strategy-crud delta spec）。
              如需分类，请使用 tags 字段过滤。
        """
        query = select(Strategy)
        if status:
            query = query.where(Strategy.status == status)
        query = query.order_by(Strategy.updated_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_options(
        self,
        status: Optional[str] = "active",
    ) -> list[Strategy]:
        """简化查询：仅返回指定 status 的策略，给 /options 接口用。

        注意：strategy_type 字段已从 StrategyOption 中移除。
        """
        query = select(Strategy)
        if status:
            query = query.where(Strategy.status == status)
        query = query.order_by(Strategy.id.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, strategy_id: int, data: dict) -> Optional[Strategy]:
        await self.session.execute(
            update(Strategy).where(Strategy.id == strategy_id).values(**data)
        )
        await self.session.flush()
        return await self.get_by_id(strategy_id)

    async def delete(self, strategy_id: int) -> bool:
        result = await self.session.execute(
            delete(Strategy).where(Strategy.id == strategy_id)
        )
        return result.rowcount > 0

    async def count(self, status: Optional[str] = None) -> int:
        query = select(func.count(Strategy.id))
        if status:
            query = query.where(Strategy.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0


class StrategyVersionRepository:
    """策略版本快照 CRUD。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> StrategyVersion:
        version = StrategyVersion(**data)
        self.session.add(version)
        await self.session.flush()
        await self.session.refresh(version)
        return version

    async def get_by_id(self, version_id: int) -> Optional[StrategyVersion]:
        result = await self.session.execute(
            select(StrategyVersion).where(StrategyVersion.id == version_id)
        )
        return result.scalar_one_or_none()

    async def list_by_strategy(
        self,
        strategy_id: int,
        status: Optional[str] = None,
    ) -> list[StrategyVersion]:
        query = select(StrategyVersion).where(StrategyVersion.strategy_id == strategy_id)
        if status:
            query = query.where(StrategyVersion.status == status)
        query = query.order_by(StrategyVersion.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest(self, strategy_id: int) -> Optional[StrategyVersion]:
        result = await self.session.execute(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_snapshot(
        self,
        version_id: int,
        runtime_config_snapshot: dict,
    ) -> Optional[StrategyVersion]:
        """更新版本的运行配置快照（dry-run 触发保存时调用）。"""
        await self.session.execute(
            update(StrategyVersion)
            .where(StrategyVersion.id == version_id)
            .values(runtime_config_snapshot=runtime_config_snapshot)
        )
        await self.session.flush()
        return await self.get_by_id(version_id)

    async def delete_by_strategy(self, strategy_id: int) -> int:
        """级联删除某策略的全部版本。返回删除条数。"""
        result = await self.session.execute(
            delete(StrategyVersion).where(StrategyVersion.strategy_id == strategy_id)
        )
        return result.rowcount


class RuntimeConfigRepository:
    """运行配置模板 CRUD（runtime-config-template spec）。"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> RuntimeConfigTemplate:
        template = RuntimeConfigTemplate(**data)
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def get_by_id(self, template_id: int) -> Optional[RuntimeConfigTemplate]:
        result = await self.session.execute(
            select(RuntimeConfigTemplate).where(RuntimeConfigTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        mode: Optional[str] = None,
    ) -> list[RuntimeConfigTemplate]:
        """列表查询，可按 mode 过滤。"""
        query = select(RuntimeConfigTemplate)
        if mode:
            query = query.where(RuntimeConfigTemplate.mode == mode)
        query = query.order_by(
            RuntimeConfigTemplate.is_default.desc(),
            RuntimeConfigTemplate.id.asc(),
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Optional[RuntimeConfigTemplate]:
        """按名称查找（用于唯一性校验）。"""
        result = await self.session.execute(
            select(RuntimeConfigTemplate).where(
                RuntimeConfigTemplate.name == name
            )
        )
        return result.scalar_one_or_none()

    async def update(
        self,
        template_id: int,
        data: dict,
    ) -> Optional[RuntimeConfigTemplate]:
        await self.session.execute(
            update(RuntimeConfigTemplate)
            .where(RuntimeConfigTemplate.id == template_id)
            .values(**data)
        )
        await self.session.flush()
        return await self.get_by_id(template_id)

    async def delete(self, template_id: int) -> bool:
        result = await self.session.execute(
            delete(RuntimeConfigTemplate).where(
                RuntimeConfigTemplate.id == template_id
            )
        )
        return result.rowcount > 0


__all__ = [
    "StrategyRepository",
    "StrategyVersionRepository",
    "RuntimeConfigRepository",
]
