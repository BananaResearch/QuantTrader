"""strategy_engine 模块的 FastAPI 路由。

变更说明（strategy-engine-params-redesign）：
- 删除 strategy_type 字段过滤与响应（strategy-crud delta spec）
- dry-run 接口签名变更（DryRunRequest 替代硬编码字段）
- 新增 RuntimeConfigTemplate CRUD（runtime-config-template spec）
- 新增策略模板列表接口（/templates）
- 路由顺序：所有静态路径（/runtime-configs、/templates）在 /{strategy_id} 之前，避免 FastAPI 路由冲突
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_db

from .exceptions import (
    BacktestError,
    DryRunError,
    InvalidParamValue,
    InvalidOverrideField,
    InvalidStrategyError,
    RuntimeConfigDateInvalid,
    RuntimeConfigDateRequired,
    RuntimeConfigDefaultForbidden,
    RuntimeConfigNameDuplicated,
    RuntimeConfigNotFound,
    StrategyLoadError,
    StrategyNotActive,
    StrategyNotFound,
)
from .models import RuntimeConfigTemplate, Strategy, StrategyVersion
from .repository import RuntimeConfigRepository, StrategyRepository, StrategyVersionRepository
from .schemas import (
    BatchBacktestRequest,
    BatchBacktestResponse,
    CompareRequest,
    CompareResponse,
    DryRunRequest,
    DryRunResponse,
    ExportRequest,
    ExportResponse,
    ImportRequest,
    ImportResponse,
    ParamSchema,
    RuntimeConfigTemplateCreate,
    RuntimeConfigTemplateResponse,
    RuntimeConfigTemplateUpdate,
    StrategyCreate,
    StrategyOption,
    StrategyResponse,
    StrategyTemplateItem,
    StrategyUpdate,
    StrategyValidateRequest,
    StrategyValidateResponse,
    StrategyVersionCreate,
    StrategyVersionResponse,
)


router = APIRouter(prefix="/api/strategy", tags=["策略引擎"])


# ============================================================
# 策略 CRUD（{strategy_id} 路径路由放在静态路径之后，避免路由冲突）
# ============================================================

@router.get("/list", response_model=dict)
async def get_strategies(
    status: Optional[str] = Query(None, description="状态过滤"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """获取策略列表。

    注意：strategy_type 过滤参数已删除（见 strategy-crud delta spec）。
    """
    repo = StrategyRepository(db)
    strategies = await repo.list_all(status=status, limit=limit, offset=offset)
    total = await repo.count(status=status)
    return {
        "success": True,
        "data": [StrategyResponse.model_validate(s).model_dump() for s in strategies],
        "total": total,
        "message": "success",
    }


@router.post("/create", response_model=dict)
async def create_strategy(
    data: StrategyCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建策略。"""
    if not data.code_content or not data.code_content.strip():
        raise HTTPException(status_code=400, detail="策略代码不能为空")

    repo = StrategyRepository(db)
    existing = await repo.get_by_code(data.code)
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"策略编码 {data.code} 已存在",
        )

    # BUG-STR-012/013：基于 param_schema 校验 parameters（若提供）
    if data.param_schema is not None and data.parameters:
        from .service import StrategyService
        try:
            StrategyService.validate_param_values(data.param_schema, data.parameters)
        except InvalidParamValue as e:
            raise HTTPException(status_code=400, detail=str(e))

    create_data = data.model_dump()
    if data.param_schema is not None:
        create_data["param_schema"] = data.param_schema.model_dump()

    strategy = await repo.create(create_data)
    return {
        "success": True,
        "data": StrategyResponse.model_validate(strategy).model_dump(),
        "message": "策略创建成功",
    }


# ============================================================
# RuntimeConfigTemplate CRUD（静态路径，在 /{strategy_id} 之前）
# ============================================================

@router.get("/runtime-configs", response_model=dict)
async def list_runtime_configs(
    mode: Optional[str] = Query(None, description="按模式过滤：backtest/paper/live"),
    db: AsyncSession = Depends(get_db),
):
    """获取运行配置模板列表。"""
    from .service import RuntimeConfigService

    svc = RuntimeConfigService(db)
    templates = await svc.list_templates(mode=mode)
    return {
        "success": True,
        "data": [
            RuntimeConfigTemplateResponse.model_validate(t).model_dump()
            for t in templates
        ],
        "message": "success",
    }


@router.post("/runtime-configs", response_model=dict)
async def create_runtime_config(
    data: RuntimeConfigTemplateCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建运行配置模板。"""
    from .service import RuntimeConfigService

    svc = RuntimeConfigService(db)
    try:
        template = await svc.create_template(data)
    except RuntimeConfigNameDuplicated as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except RuntimeConfigDateRequired as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except RuntimeConfigDateInvalid as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

    return {
        "success": True,
        "data": RuntimeConfigTemplateResponse.model_validate(template).model_dump(),
        "message": "模板创建成功",
    }


@router.get("/runtime-configs/{template_id}", response_model=dict)
async def get_runtime_config(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取运行配置模板详情。"""
    from .service import RuntimeConfigService

    svc = RuntimeConfigService(db)
    try:
        template = await svc.get_template(template_id)
    except RuntimeConfigNotFound as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

    return {
        "success": True,
        "data": RuntimeConfigTemplateResponse.model_validate(template).model_dump(),
        "message": "success",
    }


@router.put("/runtime-configs/{template_id}", response_model=dict)
async def update_runtime_config(
    template_id: int,
    data: RuntimeConfigTemplateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新运行配置模板（系统预设禁止）。"""
    from .service import RuntimeConfigService

    svc = RuntimeConfigService(db)
    try:
        template = await svc.update_template(template_id, data)
    except RuntimeConfigNotFound as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except RuntimeConfigDefaultForbidden as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except RuntimeConfigNameDuplicated as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

    return {
        "success": True,
        "data": RuntimeConfigTemplateResponse.model_validate(template).model_dump(),
        "message": "模板更新成功",
    }


@router.delete("/runtime-configs/{template_id}", response_model=dict)
async def delete_runtime_config(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除运行配置模板（系统预设禁止）。"""
    from .service import RuntimeConfigService

    svc = RuntimeConfigService(db)
    try:
        await svc.delete_template(template_id)
    except RuntimeConfigNotFound as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except RuntimeConfigDefaultForbidden as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

    return {
        "success": True,
        "data": {},
        "message": "模板删除成功",
    }


# ============================================================
# 策略模板列表（静态路径）
# ============================================================

@router.get("/templates", response_model=dict)
async def get_strategy_templates():
    """获取内置策略模板列表（来自 builtin/，带内存缓存）。"""
    templates = _get_cached_templates()
    return {
        "success": True,
        "data": [t.model_dump() for t in templates],
        "message": "success",
    }


@lru_cache(maxsize=1)
def _get_cached_templates() -> list[StrategyTemplateItem]:
    """从 builtin/ 模块加载策略模板（启动时缓存）。"""
    from strategy_engine import builtin

    items: list[StrategyTemplateItem] = []

    # 空白模板
    items.append(
        StrategyTemplateItem(
            code="",
            name="空白策略",
            description="从零开始，完全自定义策略代码和参数",
            code_content="",
            param_schema=None,
            parameters=None,
            is_blank=True,
        )
    )

    for module_name in ("double_ma", "bollinger", "macd", "rsi"):
        module = getattr(builtin, module_name, None)
        if not module:
            continue

        code_content = getattr(module, "STRATEGY_CODE", "")
        param_schema_raw = getattr(module, "PARAM_SCHEMA", None)
        param_schema: ParamSchema | None = None
        if param_schema_raw:
            param_schema = ParamSchema.model_validate(param_schema_raw)
        default_params = getattr(module, "DEFAULT_PARAMETERS", {})

        items.append(
            StrategyTemplateItem(
                code=getattr(module, "STRATEGY_CODE_NAME", module_name.upper()),
                name=getattr(module, "STRATEGY_NAME", module_name),
                description=module.__doc__.strip().split("\n")[0] if module.__doc__ else module_name,
                code_content=code_content,
                param_schema=param_schema,
                parameters=default_params,
                is_blank=False,
            )
        )

    return items


# ============================================================
# 策略版本（/{strategy_id}/versions 在 /{strategy_id} 之后）
# ============================================================

@router.get("/{strategy_id}/versions", response_model=dict)
async def get_strategy_versions(
    strategy_id: int,
    status: Optional[str] = Query(None, description="版本状态过滤"),
    db: AsyncSession = Depends(get_db),
):
    """获取策略版本历史。"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    version_repo = StrategyVersionRepository(db)
    versions = await version_repo.list_by_strategy(strategy_id, status=status)
    return {
        "success": True,
        "data": [StrategyVersionResponse.model_validate(v).model_dump() for v in versions],
        "message": "success",
    }


@router.post("/{strategy_id}/versions", response_model=dict)
async def create_strategy_version(
    strategy_id: int,
    data: StrategyVersionCreate,
    db: AsyncSession = Depends(get_db),
):
    """创建策略新版本。"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    version_data = data.model_dump(exclude_unset=True)
    version_data["strategy_id"] = strategy_id

    version_repo = StrategyVersionRepository(db)
    try:
        version = await version_repo.create(version_data)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"版本创建失败: {e}",
        )

    await repo.update(strategy_id, {"version": data.version})

    return {
        "success": True,
        "data": StrategyVersionResponse.model_validate(version).model_dump(),
        "message": "版本创建成功",
    }


# ============================================================
# 简化列表 / 校验 / 试运行
# ============================================================

@router.get("/options/all", response_model=dict)
async def get_strategy_options(
    status: Optional[str] = Query(
        "active",
        description="默认只返回 active 策略；传 all 返回全部",
    ),
    db: AsyncSession = Depends(get_db),
):
    """获取策略简化列表（给 history_replay 等模块调用）。

    注意：strategy_type 字段已从响应中移除（strategy-crud delta spec）。
    """
    repo = StrategyRepository(db)
    filter_status = None if status == "all" else status
    strategies = await repo.list_options(status=filter_status)
    return {
        "success": True,
        "data": [
            StrategyOption(
                id=s.id,
                name=s.name,
                description=s.description,
            ).model_dump()
            for s in strategies
        ],
        "message": "success",
    }


@router.post("/validate", response_model=dict)
async def validate_strategy_code(
    payload: StrategyValidateRequest,
):
    """校验策略代码语法 + 沙箱可加载性。不查 DB。"""
    from .runtime.loader import validate_code

    result = validate_code(payload.code_content)
    return {
        "success": True,
        "data": result,
        "message": "校验完成",
    }


@router.post("/{strategy_id}/dry-run", response_model=dict)
async def dry_run_strategy(
    strategy_id: int,
    payload: DryRunRequest,
    db: AsyncSession = Depends(get_db),
):
    """策略试运行：基于运行配置模板 + 临时覆盖，跑最多 1000 bar。

    注意：接口签名已变更（template_id + override 替代硬编码 stock_code/date）。
    """
    from .service import dry_run

    try:
        result = await dry_run(
            db=db,
            strategy_id=strategy_id,
            payload=payload,
        )
    except StrategyNotFound as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except StrategyNotActive as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except RuntimeConfigNotFound as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except InvalidOverrideField as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except (RuntimeConfigDateInvalid, RuntimeConfigDateRequired) as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except InvalidParamValue as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except DryRunError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except InvalidStrategyError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

    # BUG-STR-009：同日或短区间 dry-run 可能返回空 bars，给业务化提示
    message = "试运行完成"
    if result.total_bars == 0:
        message = "试运行完成（区间内无足够 K 线，结果为空）"

    return {
        "success": True,
        "data": result.model_dump(),
        "message": message,
    }


# ============================================================
# /{strategy_id} CRUD（必须放在所有 /runtime-configs 和 /templates 之后）
# ============================================================

@router.get("/{strategy_id}", response_model=dict)
async def get_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取策略详情。"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    return {
        "success": True,
        "data": StrategyResponse.model_validate(strategy).model_dump(),
        "message": "success",
    }


@router.put("/{strategy_id}", response_model=dict)
async def update_strategy(
    strategy_id: int,
    data: StrategyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新策略。"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    update_data = data.model_dump(exclude_unset=True)

    # BUG-STR-012/013：当 parameters 更新时，基于 strategy.param_schema 校验
    if "parameters" in update_data and update_data["parameters"] and strategy.param_schema:
        from .schemas import ParamSchema
        from .service import StrategyService
        schema = ParamSchema.model_validate(strategy.param_schema)
        try:
            StrategyService.validate_param_values(schema, update_data["parameters"])
        except InvalidParamValue as e:
            raise HTTPException(status_code=400, detail=str(e))

    # 记录 code_content 变更前的值（用于 BUG-STR-004 广播 diff 判断）
    code_before = strategy.code_content

    updated = await repo.update(strategy_id, update_data)

    # BUG-STR-004：仅在 code_content 实际变化时广播；广播异常隔离不影响主流程
    code_after = updated.code_content if hasattr(updated, "code_content") else code_before
    if "code_content" in update_data and code_after != code_before:
        import logging
        from .runtime.websocket import get_ws_manager
        logger = logging.getLogger(__name__)
        try:
            manager = get_ws_manager()
            await manager.broadcast(
                strategy_id,
                {
                    "type": "code_updated",
                    "strategy_id": strategy_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as ws_err:
            logger.warning(
                "WebSocket broadcast failed for strategy_id=%d: %s",
                strategy_id, ws_err,
            )

    return {
        "success": True,
        "data": StrategyResponse.model_validate(updated).model_dump(),
        "message": "策略更新成功",
    }


@router.delete("/{strategy_id}", response_model=dict)
async def delete_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除策略（级联删除历史版本）。"""
    repo = StrategyRepository(db)
    strategy = await repo.get_by_id(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")

    version_repo = StrategyVersionRepository(db)
    deleted_versions = await version_repo.delete_by_strategy(strategy_id)

    await repo.delete(strategy_id)

    from .runtime.websocket import get_ws_manager
    manager = get_ws_manager()
    await manager.broadcast(
        strategy_id,
        {
            "type": "strategy_deleted",
            "strategy_id": strategy_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    return {
        "success": True,
        "data": {"deleted_versions": deleted_versions},
        "message": "策略删除成功",
    }


# ============================================================
# 热加载 / WebSocket / P3 扩展
# ============================================================

@router.post("/{strategy_id}/reload", response_model=dict)
async def reload_strategy(
    strategy_id: int,
    db: AsyncSession = Depends(get_db),
):
    """热加载策略实例（清除缓存并重新加载）。"""
    from strategy_engine.runtime.registry import get_global_registry
    from .service import load_strategy

    registry = get_global_registry()
    await registry.evict(strategy_id)

    try:
        instance = await load_strategy(db, strategy_id)
        return {
            "success": True,
            "data": {
                "strategy_id": strategy_id,
                "status": "reloaded",
            },
            "message": "策略已重新加载",
        }
    except StrategyNotFound:
        raise HTTPException(status_code=404, detail=f"策略 {strategy_id} 不存在")
    except StrategyNotActive as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidStrategyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StrategyLoadError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.websocket("/ws/strategy/{strategy_id}")
async def websocket_strategy_endpoint(
    websocket: WebSocket,
    strategy_id: int,
):
    """WebSocket 端点：订阅策略代码变更推送。"""
    from .runtime.websocket import get_ws_manager

    manager = get_ws_manager()
    await websocket.accept()
    await manager.handle_connection(websocket, strategy_id)


@router.post("/batch-backtest", response_model=dict, tags=["策略引擎"])
async def batch_backtest_endpoint(
    req: BatchBacktestRequest,
    db: AsyncSession = Depends(get_db),
):
    """并发执行多个策略回测，最多 10 个。"""
    from .service import batch_backtest

    if len(req.strategy_ids) > 10:
        raise HTTPException(
            status_code=400,
            detail="并发回测最多支持 10 个策略",
        )

    try:
        results = await batch_backtest(
            db=db,
            strategy_ids=req.strategy_ids,
            stock_code=req.stock_code,
            start_date=req.start_date,
            end_date=req.end_date,
            timeframe=req.timeframe,
        )
    except StrategyNotFound as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except StrategyNotActive as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except InvalidStrategyError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

    return {
        "success": True,
        "data": {
            "results": [
                {
                    "session_id": r.session_id,
                    "strategy_id": r.strategy_id,
                    "strategy_name": r.strategy_name,
                    "total_bars": r.total_bars,
                    "time_elapsed": r.time_elapsed,
                }
                for r in results
            ]
        },
        "message": "并发回测完成",
    }


@router.post("/compare", response_model=dict, tags=["策略引擎"])
async def compare_versions_endpoint(
    req: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    """对比两个策略版本的回测结果。"""
    from .exceptions import InvalidStrategyError, StrategyNotFound
    from .runtime.compare import CompareService

    if len(req.version_ids) != 2:
        raise HTTPException(
            status_code=400,
            detail="版本 ID 列表必须包含 2 个版本",
        )

    svc = CompareService()
    try:
        result = await svc.compare(
            db=db,
            version_ids=req.version_ids,
            stock_code=req.stock_code,
            start_date=req.start_date,
            end_date=req.end_date,
            timeframe=req.timeframe,
        )
    except InvalidStrategyError as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))
    except StrategyNotFound as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

    return {
        "success": True,
        "data": {
            "version_1": result.version_1,
            "version_2": result.version_2,
            "diff": result.diff,
        },
        "message": "版本对比完成",
    }


@router.post("/export", response_model=dict, tags=["策略引擎"])
async def export_strategies_endpoint(
    req: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """导出策略为 JSON 格式（strategy_type 字段已从 Schema 移除）。"""
    from .runtime.sharing import SharingService

    svc = SharingService()
    try:
        items = await svc.export_strategies(
            db=db,
            strategy_ids=req.strategy_ids,
            include_versions=req.include_versions,
        )
    except StrategyNotFound as e:
        raise HTTPException(status_code=e.http_status, detail=str(e))

    return {
        "success": True,
        "data": {
            "strategies": [
                {
                    "code": item.code,
                    "name": item.name,
                    "description": item.description,
                    "code_content": item.code_content,
                    "parameters": item.parameters,
                    "versions": item.versions if req.include_versions else None,
                }
                for item in items
            ],
        },
        "message": "策略导出成功",
    }


@router.post("/import", response_model=dict, tags=["策略引擎"])
async def import_strategies_endpoint(
    req: ImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """导入 JSON 格式的策略（strategy_type 字段已移除）。"""
    from .runtime.sharing import SharingService

    svc = SharingService()
    strategies_data = []
    for item in req.strategies:
        d = item.model_dump()
        if d.get("param_schema") is not None:
            d["param_schema"] = d["param_schema"].model_dump()
        strategies_data.append(d)
    result = await svc.import_strategies(db=db, strategies_data=strategies_data)

    return {
        "success": True,
        "data": {
            "imported": result.imported,
            "skipped": result.skipped,
            "skipped_codes": result.skipped_codes,
        },
        "message": f"导入完成：成功 {result.imported} 个，跳过 {result.skipped} 个",
    }


__all__ = ["router"]
