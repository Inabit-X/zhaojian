"""个案接口：管理员创建/分配，咨询师与学生按归属查看。"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import AdminUser, CaseViewer, DbSession
from app.schemas.case import CaseCreate, CaseListResponse, CaseRead
from app.services import cases as cases_service

router = APIRouter(prefix="/cases", tags=["cases"])


def _client_ip(request: Request) -> str | None:
    """取客户端 IP；测试环境可能没有 client。"""
    return request.client.host if request.client else None


@router.post(
    "",
    response_model=CaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建个案并分配咨询师（仅管理员）",
)
async def create_case(
    payload: CaseCreate,
    db: DbSession,
    admin: AdminUser,
    request: Request,
) -> CaseRead:
    """管理员按学生标识与咨询师 id 建档；学生或咨询师角色不符返回 404。"""
    case_record = await cases_service.create_case(
        db, payload, actor=admin, ip=_client_ip(request)
    )
    return CaseRead.model_validate(case_record)


@router.get(
    "",
    response_model=CaseListResponse,
    summary="本人个案列表（咨询师/学生）",
)
async def list_cases(
    db: DbSession,
    user: CaseViewer,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CaseListResponse:
    """咨询师返回本人接案，学生返回本人个案；管理员/审计员 403。"""
    items, total = await cases_service.list_cases(
        db, user=user, offset=offset, limit=limit
    )
    return CaseListResponse(
        items=[CaseRead.model_validate(item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{case_id}",
    response_model=CaseRead,
    summary="个案详情（咨询师/学生，越权 404）",
)
async def get_case(
    case_id: uuid.UUID,
    db: DbSession,
    user: CaseViewer,
    request: Request,
) -> CaseRead:
    """按角色归属返回个案；非同一个个案返回 404 并写查看审计。"""
    case_record = await cases_service.get_case(
        db, case_id, user=user, ip=_client_ip(request)
    )
    return CaseRead.model_validate(case_record)
