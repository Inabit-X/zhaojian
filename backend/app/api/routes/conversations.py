"""会谈接口：创建、列表、详情与重新抽取（仅接案咨询师）。"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from app.api.deps import CounselorUser, DbSession
from app.db.models import Conversation
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationExtractRequest,
    ConversationListResponse,
    ConversationRead,
    ExtractionRead,
    SegmentRead,
)
from app.services import conversations as conversations_service

router = APIRouter(tags=["conversations"])


def _client_ip(request: Request) -> str | None:
    """取客户端 IP；测试环境可能没有 client。"""
    return request.client.host if request.client else None


def _to_read(conversation: Conversation) -> ConversationRead:
    """把 ORM 会话转成带计数的列表项。"""
    return ConversationRead.model_validate(conversation).model_copy(
        update={
            "segment_count": len(conversation.segments),
            "extraction_count": len(conversation.extractions),
        }
    )


def _to_detail(conversation: Conversation) -> ConversationDetail:
    """把 ORM 会话转成包含分段与抽取的详情。"""
    return ConversationDetail(
        **_to_read(conversation).model_dump(),
        segments=[
            SegmentRead.model_validate(segment)
            for segment in conversation.segments
        ],
        extractions=[
            ExtractionRead.model_validate(item)
            for item in conversation.extractions
        ],
        record_id=(
            conversation.record.id if conversation.record is not None else None
        ),
    )


@router.post(
    "/cases/{case_id}/conversations",
    response_model=ConversationDetail,
    status_code=status.HTTP_201_CREATED,
    summary="新建会谈并同步分段/抽取（仅接案咨询师）",
)
async def create_conversation(
    case_id: uuid.UUID,
    payload: ConversationCreate,
    db: DbSession,
    counselor: CounselorUser,
    request: Request,
) -> ConversationDetail:
    """粘贴会谈全文或提交分段；同步完成切分与规则/LLM 抽取。"""
    conversation = await conversations_service.create_conversation(
        db,
        user=counselor,
        case_id=case_id,
        payload=payload,
        ip=_client_ip(request),
    )
    return _to_detail(conversation)


@router.get(
    "/cases/{case_id}/conversations",
    response_model=ConversationListResponse,
    summary="个案下的会谈列表（仅接案咨询师）",
)
async def list_conversations(
    case_id: uuid.UUID,
    db: DbSession,
    counselor: CounselorUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ConversationListResponse:
    """按会谈时间倒序分页；非本人个案 404。"""
    items, total = await conversations_service.list_conversations(
        db,
        user=counselor,
        case_id=case_id,
        offset=offset,
        limit=limit,
    )
    return ConversationListResponse(
        items=[_to_read(item) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetail,
    summary="会谈详情（仅接案咨询师）",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: DbSession,
    counselor: CounselorUser,
    request: Request,
) -> ConversationDetail:
    """返回分段与抽取结果，并写查看审计。"""
    conversation = await conversations_service.get_conversation(
        db,
        conversation_id,
        user=counselor,
        ip=_client_ip(request),
    )
    return _to_detail(conversation)


@router.post(
    "/conversations/{conversation_id}/extract",
    response_model=ConversationDetail,
    summary="重新抽取会谈事实（仅接案咨询师）",
)
async def reextract_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationExtractRequest,
    db: DbSession,
    counselor: CounselorUser,
    request: Request,
) -> ConversationDetail:
    """删除旧结果后重跑；LLM 不可用时自动回退规则版。"""
    conversation = await conversations_service.reextract_conversation(
        db,
        conversation_id,
        user=counselor,
        use_llm=payload.use_llm,
        ip=_client_ip(request),
    )
    return _to_detail(conversation)
