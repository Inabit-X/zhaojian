"""健康检查：live 不依赖外部组件，ready 检查数据库。"""

import logging

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import DbSession
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health/live", summary="存活探针")
async def live() -> dict[str, str]:
    """返回存活状态，不依赖任何外部组件。"""
    return {"status": "ok"}


@router.get("/health/ready", summary="就绪探针（含数据库）")
async def ready(db: DbSession) -> dict[str, str]:
    """执行 SELECT 1 检查数据库连通性，并返回就绪状态。"""
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("就绪检查失败：数据库不可用")
        raise AppError(
            "数据库暂不可用", code="database_unavailable", status_code=503
        ) from exc
    return {"status": "ok", "database": "ok"}
