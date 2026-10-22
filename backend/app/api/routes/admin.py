"""管理端：开通咨询师、查看审计。"""

from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import AdminOrAuditor, AdminUser, DbSession
from app.schemas.admin import (
    AuditLogListResponse,
    AuditLogRead,
    CounselorCreate,
    CounselorListResponse,
)
from app.schemas.auth import UserRead
from app.services import admin as admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _client_ip(request: Request) -> str | None:
    """取客户端 IP；测试环境可能没有 client。"""
    return request.client.host if request.client else None


@router.post(
    "/counselors",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="开通咨询师账号（仅管理员）",
)
async def create_counselor(
    payload: CounselorCreate,
    db: DbSession,
    admin: AdminUser,
    request: Request,
) -> UserRead:
    """管理员创建咨询师账号，邮箱冲突返回 409，成功写入审计。"""
    counselor = await admin_service.create_counselor(
        db, payload, actor=admin, ip=_client_ip(request)
    )
    return UserRead.model_validate(counselor)


@router.get(
    "/counselors",
    response_model=CounselorListResponse,
    summary="咨询师列表（仅管理员）",
)
async def list_counselors(
    db: DbSession,
    _: AdminUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CounselorListResponse:
    """分页返回咨询师账号。"""
    items, total = await admin_service.list_counselors(db, offset=offset, limit=limit)
    return CounselorListResponse(
        items=[UserRead.model_validate(item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    summary="审计日志（管理员/审计员只读）",
)
async def list_audit_logs(
    db: DbSession,
    _: AdminOrAuditor,
    action: Annotated[str | None, Query(max_length=64)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AuditLogListResponse:
    """按时间倒序分页返回审计日志，可按 action 精确过滤。"""
    items, total = await admin_service.list_audit_logs(
        db, offset=offset, limit=limit, action=action
    )
    return AuditLogListResponse(
        items=[AuditLogRead.model_validate(item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )
