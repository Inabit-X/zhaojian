"""咨询记录接口：生成草稿、查看、编辑、确认（仅接案咨询师）。"""

import uuid

from fastapi import APIRouter, Request, status

from app.api.deps import CounselorUser, DbSession
from app.schemas.record import (
    RecordDraftRequest,
    RecordRead,
    RecordUpdateRequest,
)
from app.services import records as records_service

router = APIRouter(tags=["records"])


def _client_ip(request: Request) -> str | None:
    """取客户端 IP；测试环境可能没有 client。"""
    return request.client.host if request.client else None


@router.post(
    "/conversations/{conversation_id}/records/draft",
    response_model=RecordRead,
    status_code=status.HTTP_201_CREATED,
    summary="生成四段记录草稿（仅接案咨询师）",
)
async def draft_record(
    conversation_id: uuid.UUID,
    payload: RecordDraftRequest,
    db: DbSession,
    counselor: CounselorUser,
    request: Request,
) -> RecordRead:
    """基于已抽取事实生成草稿；LLM 失败回退规则模板。"""
    return await records_service.draft_record(
        db,
        conversation_id,
        user=counselor,
        use_llm=payload.use_llm,
        ip=_client_ip(request),
    )


@router.get(
    "/records/{record_id}",
    response_model=RecordRead,
    summary="记录详情（仅接案咨询师）",
)
async def get_record(
    record_id: uuid.UUID,
    db: DbSession,
    counselor: CounselorUser,
    request: Request,
) -> RecordRead:
    """返回四段内容、版本数与修改率，并写查看审计。"""
    return await records_service.get_record(
        db,
        record_id,
        user=counselor,
        ip=_client_ip(request),
    )


@router.patch(
    "/records/{record_id}",
    response_model=RecordRead,
    summary="编辑记录草稿（仅接案咨询师）",
)
async def update_record(
    record_id: uuid.UUID,
    payload: RecordUpdateRequest,
    db: DbSession,
    counselor: CounselorUser,
    request: Request,
) -> RecordRead:
    """整体替换四段文本并写新版本；已确认记录 409。"""
    return await records_service.update_record(
        db,
        record_id,
        user=counselor,
        sections=payload.sections,
        ip=_client_ip(request),
    )


@router.post(
    "/records/{record_id}/confirm",
    response_model=RecordRead,
    summary="确认记录（仅接案咨询师）",
)
async def confirm_record(
    record_id: uuid.UUID,
    db: DbSession,
    counselor: CounselorUser,
    request: Request,
) -> RecordRead:
    """固化草稿为确认稿；重复确认 409。"""
    return await records_service.confirm_record(
        db,
        record_id,
        user=counselor,
        ip=_client_ip(request),
    )
