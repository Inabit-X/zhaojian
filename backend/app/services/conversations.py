"""会谈业务：创建（分段 + 抽取）、列表、查看、重新抽取。

权限：仅接案咨询师可访问；管理员/审计员/学生一律 403 或 404。
越权与不存在统一 404，避免泄露个案是否存在。
"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import AuditAction, CaseStatus, ConversationStatus
from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.roles import Role
from app.db.models import Case, Conversation, Extraction, Segment, User
from app.schemas.conversation import ConversationCreate
from app.services.audit import record_audit
from app.services.extraction import extract_facts
from app.services.segmentation import (
    normalize_segments,
    parse_transcript,
    render_transcript,
)

MAX_TRANSCRIPT_CHARS = 100_000


async def get_owned_case(
    db: AsyncSession,
    case_id: uuid.UUID,
    user: User,
    *,
    require_active: bool = False,
) -> Case:
    """校验当前咨询师是个案负责人；非咨询师 403，非本人个案 404。"""
    if user.role != Role.COUNSELOR.value:
        raise PermissionDeniedError("仅咨询师可访问会谈内容", code="forbidden")
    case_record = await db.get(Case, case_id)
    if case_record is None or case_record.counselor_id != user.id:
        raise NotFoundError("个案不存在", code="case_not_found")
    if require_active and case_record.status != CaseStatus.ACTIVE.value:
        raise ConflictError("个案已结案，不能新增会谈", code="case_closed")
    return case_record


async def load_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    *,
    populate_existing: bool = False,
) -> Conversation | None:
    """加载会谈及分段/抽取/记录；可选强制刷新身份映射中的旧集合。"""
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.segments),
            selectinload(Conversation.extractions),
            selectinload(Conversation.record),
        )
    )
    if populate_existing:
        stmt = stmt.execution_options(populate_existing=True)
    return await db.scalar(stmt)


async def create_conversation(
    db: AsyncSession,
    *,
    user: User,
    case_id: uuid.UUID,
    payload: ConversationCreate,
    ip: str | None = None,
) -> Conversation:
    """落库会谈全文、分段与规则/LLM 抽取结果；同一事务提交。"""
    await get_owned_case(db, case_id, user, require_active=True)

    if payload.segments is not None:
        segments = normalize_segments(payload.segments)
    else:
        segments = parse_transcript(payload.transcript_text or "")
    if not segments:
        raise AppError("会谈内容为空", code="empty_transcript", status_code=422)

    transcript = (
        payload.transcript_text or render_transcript(segments)
    ).strip()
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        raise AppError(
            "会谈内容超过 100000 字符",
            code="transcript_too_long",
            status_code=422,
        )

    facts, generated_by = await extract_facts(segments, use_llm=True)

    conversation = Conversation(
        case_id=case_id,
        counselor_id=user.id,
        session_date=payload.session_date,
        source="text",
        status=ConversationStatus.EXTRACTED.value,
        consent_confirmed=True,
        transcript_text=transcript,
    )
    db.add(conversation)
    await db.flush()

    segment_models: list[Segment] = []
    for segment in segments:
        model = Segment(
            conversation_id=conversation.id,
            idx=segment["idx"],
            speaker=segment.get("speaker", "unknown"),
            start_ms=segment.get("start_ms"),
            end_ms=segment.get("end_ms"),
            text=segment["text"],
        )
        db.add(model)
        segment_models.append(model)
    await db.flush()

    for fact in facts:
        segment_idx = int(fact["segment_idx"])
        if segment_idx < 0 or segment_idx >= len(segment_models):
            continue
        db.add(
            Extraction(
                conversation_id=conversation.id,
                segment_id=segment_models[segment_idx].id,
                kind=fact["kind"],
                value_json=fact["value"],
                quote=fact["quote"],
                confidence=fact["confidence"],
            )
        )
    await db.flush()

    await record_audit(
        db,
        actor_id=user.id,
        action=AuditAction.CONVERSATION_CREATE.value,
        target_type="conversation",
        target_id=conversation.id,
        meta={
            "case_id": str(case_id),
            "segments": len(segment_models),
            "facts": len(facts),
            "generated_by": generated_by,
        },
        ip=ip,
    )
    await db.commit()
    return await load_conversation(
        db, conversation.id, populate_existing=True
    ) or conversation


async def list_conversations(
    db: AsyncSession,
    *,
    user: User,
    case_id: uuid.UUID,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Conversation], int]:
    """按会谈时间倒序分页返回某个个案的会谈。"""
    await get_owned_case(db, case_id, user)
    total = (
        await db.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.case_id == case_id)
        )
        or 0
    )
    items = (
        await db.scalars(
            select(Conversation)
            .where(Conversation.case_id == case_id)
            .options(
                selectinload(Conversation.segments),
                selectinload(Conversation.extractions),
            )
            .order_by(
                Conversation.session_date.desc(),
                Conversation.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return list(items), total


async def get_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    *,
    user: User,
    ip: str | None = None,
) -> Conversation:
    """返回会谈详情并写查看审计；越权/不存在 404。"""
    conversation = await load_conversation(db, conversation_id)
    if conversation is None:
        raise NotFoundError("会谈不存在", code="conversation_not_found")
    await get_owned_case(db, conversation.case_id, user)

    await record_audit(
        db,
        actor_id=user.id,
        action=AuditAction.CONVERSATION_VIEW.value,
        target_type="conversation",
        target_id=conversation.id,
        meta={"case_id": str(conversation.case_id)},
        ip=ip,
    )
    await db.commit()
    return conversation


async def reextract_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    *,
    user: User,
    use_llm: bool = True,
    ip: str | None = None,
) -> Conversation:
    """删除旧抽取结果后重新抽取；LLM 失败自动回退规则版。"""
    conversation = await load_conversation(db, conversation_id)
    if conversation is None:
        raise NotFoundError("会谈不存在", code="conversation_not_found")
    await get_owned_case(db, conversation.case_id, user)

    segments = [
        {"idx": segment.idx, "speaker": segment.speaker, "text": segment.text}
        for segment in conversation.segments
    ]
    facts, generated_by = await extract_facts(segments, use_llm=use_llm)

    await db.execute(
        delete(Extraction).where(Extraction.conversation_id == conversation.id)
    )
    for fact in facts:
        segment_idx = int(fact["segment_idx"])
        if segment_idx < 0 or segment_idx >= len(conversation.segments):
            continue
        db.add(
            Extraction(
                conversation_id=conversation.id,
                segment_id=conversation.segments[segment_idx].id,
                kind=fact["kind"],
                value_json=fact["value"],
                quote=fact["quote"],
                confidence=fact["confidence"],
            )
        )
    conversation.status = ConversationStatus.EXTRACTED.value

    await record_audit(
        db,
        actor_id=user.id,
        action=AuditAction.CONVERSATION_EXTRACT.value,
        target_type="conversation",
        target_id=conversation.id,
        meta={"facts": len(facts), "generated_by": generated_by},
        ip=ip,
    )
    await db.commit()
    return await load_conversation(
        db, conversation.id, populate_existing=True
    ) or conversation
