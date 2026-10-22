"""咨询记录业务：生成草稿、编辑、确认与修改率。

草稿只允许在 draft 状态修改；确认后内容冻结，重开需新建会谈记录。
"""

import json
import uuid
from datetime import UTC, datetime
from difflib import SequenceMatcher

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import AuditAction, ConversationStatus, RecordStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.db.models import Conversation, Record, RecordVersion, User
from app.schemas.record import RecordRead, RecordSections
from app.services.audit import record_audit
from app.services.conversations import get_owned_case
from app.services.record_template import generate_sections


async def _load_record(
    db: AsyncSession, record_id: uuid.UUID
) -> Record | None:
    """按 id 加载记录。"""
    return await db.get(Record, record_id)


async def _version_count(db: AsyncSession, record_id: uuid.UUID) -> int:
    """返回记录的版本总数。"""
    return (
        await db.scalar(
            select(func.count())
            .select_from(RecordVersion)
            .where(RecordVersion.record_id == record_id)
        )
        or 0
    )


async def _next_version(db: AsyncSession, record_id: uuid.UUID) -> int:
    """返回下一个版本号（当前最大值 + 1）。"""
    current = (
        await db.scalar(
            select(func.max(RecordVersion.version)).where(
                RecordVersion.record_id == record_id
            )
        )
        or 0
    )
    return int(current) + 1


def _sections_from_json(data: dict | None) -> RecordSections:
    """兼容 {sections: {...}} 与直接四段两种存储格式。"""
    if not isinstance(data, dict):
        return RecordSections()
    raw = data.get("sections") if isinstance(data.get("sections"), dict) else data
    try:
        return RecordSections.model_validate(raw)
    except ValidationError:
        return RecordSections()


def _content_text(sections: RecordSections) -> str:
    """把四段拼成用于比较的文本。"""
    return "\n".join(
        [
            sections.presenting,
            sections.observations,
            sections.formulation,
            sections.plan,
        ]
    )


async def _change_rate(
    db: AsyncSession, record_id: uuid.UUID
) -> float | None:
    """用最近两版内容的差异比例近似修改率；不足两版返回 None。"""
    versions = (
        await db.scalars(
            select(RecordVersion)
            .where(RecordVersion.record_id == record_id)
            .order_by(RecordVersion.version.desc())
            .limit(2)
        )
    ).all()
    if len(versions) < 2:
        return None
    newer = json.dumps(versions[0].content_json, ensure_ascii=False, sort_keys=True)
    older = json.dumps(versions[1].content_json, ensure_ascii=False, sort_keys=True)
    ratio = SequenceMatcher(None, older, newer).ratio()
    return round(1 - ratio, 4)


def build_record_read(
    record: Record,
    *,
    version_count: int,
    change_rate: float | None = None,
) -> RecordRead:
    """把 ORM 记录转成响应模型，确认后优先展示确认稿。"""
    source = record.confirmed_json or record.draft_json
    generated_by = None
    if isinstance(record.draft_json, dict):
        generated_by = record.draft_json.get("generated_by")
        if record.status == RecordStatus.CONFIRMED.value:
            generated_by = "confirmed"
    return RecordRead(
        id=record.id,
        case_id=record.case_id,
        conversation_id=record.conversation_id,
        status=record.status,
        sections=_sections_from_json(source),
        generated_by=generated_by,
        version_count=version_count,
        change_rate=change_rate,
        created_at=record.created_at,
        updated_at=record.updated_at,
        confirmed_at=record.confirmed_at,
    )


async def draft_record(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    *,
    user: User,
    use_llm: bool = True,
    ip: str | None = None,
) -> RecordRead:
    """为会谈生成或重新生成四段草稿，并写一个版本快照。"""
    conversation = await db.scalar(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(
            selectinload(Conversation.extractions),
            selectinload(Conversation.record),
        )
    )
    if conversation is None:
        raise NotFoundError("会谈不存在", code="conversation_not_found")
    await get_owned_case(db, conversation.case_id, user)

    if (
        conversation.record is not None
        and conversation.record.status == RecordStatus.CONFIRMED.value
    ):
        raise ConflictError("记录已确认，不能重新生成", code="record_confirmed")

    facts = [
        {"kind": item.kind, "quote": item.quote, "value": item.value_json}
        for item in conversation.extractions
    ]
    sections, generated_by = await generate_sections(facts, use_llm=use_llm)
    content = {"sections": sections, "generated_by": generated_by}

    if conversation.record is None:
        record = Record(
            case_id=conversation.case_id,
            conversation_id=conversation.id,
            counselor_id=user.id,
            status=RecordStatus.DRAFT.value,
            draft_json=content,
        )
        db.add(record)
        await db.flush()
    else:
        record = conversation.record
        record.draft_json = content
        record.counselor_id = user.id
        await db.flush()

    version = await _next_version(db, record.id)
    db.add(
        RecordVersion(
            record_id=record.id,
            version=version,
            content_json=content,
            editor_id=user.id,
        )
    )
    conversation.status = ConversationStatus.DRAFTED.value

    await record_audit(
        db,
        actor_id=user.id,
        action=AuditAction.RECORD_DRAFT.value,
        target_type="record",
        target_id=record.id,
        meta={"version": version, "generated_by": generated_by},
        ip=ip,
    )
    await db.commit()
    await db.refresh(record)
    return build_record_read(
        record,
        version_count=await _version_count(db, record.id),
    )


async def get_record(
    db: AsyncSession,
    record_id: uuid.UUID,
    *,
    user: User,
    ip: str | None = None,
) -> RecordRead:
    """返回记录详情与版本数/修改率，并写查看审计。"""
    record = await _load_record(db, record_id)
    if record is None:
        raise NotFoundError("记录不存在", code="record_not_found")
    await get_owned_case(db, record.case_id, user)

    version_count = await _version_count(db, record.id)
    change_rate = await _change_rate(db, record.id)
    result = build_record_read(
        record, version_count=version_count, change_rate=change_rate
    )

    await record_audit(
        db,
        actor_id=user.id,
        action=AuditAction.RECORD_VIEW.value,
        target_type="record",
        target_id=record.id,
        ip=ip,
    )
    await db.commit()
    return result


async def update_record(
    db: AsyncSession,
    record_id: uuid.UUID,
    *,
    user: User,
    sections: RecordSections,
    ip: str | None = None,
) -> RecordRead:
    """咨询师编辑草稿并写新版本；已确认记录拒绝修改。"""
    record = await _load_record(db, record_id)
    if record is None:
        raise NotFoundError("记录不存在", code="record_not_found")
    await get_owned_case(db, record.case_id, user)

    if record.status != RecordStatus.DRAFT.value:
        raise ConflictError("记录已确认，不能修改", code="record_confirmed")

    content = {"sections": sections.model_dump(), "generated_by": "manual"}
    record.draft_json = content
    version = await _next_version(db, record.id)
    db.add(
        RecordVersion(
            record_id=record.id,
            version=version,
            content_json=content,
            editor_id=user.id,
        )
    )

    await record_audit(
        db,
        actor_id=user.id,
        action=AuditAction.RECORD_UPDATE.value,
        target_type="record",
        target_id=record.id,
        meta={"version": version},
        ip=ip,
    )
    await db.commit()
    await db.refresh(record)
    return build_record_read(
        record,
        version_count=await _version_count(db, record.id),
        change_rate=await _change_rate(db, record.id),
    )


async def confirm_record(
    db: AsyncSession,
    record_id: uuid.UUID,
    *,
    user: User,
    ip: str | None = None,
) -> RecordRead:
    """把草稿固化为确认稿，同步会谈状态并写版本。"""
    record = await _load_record(db, record_id)
    if record is None:
        raise NotFoundError("记录不存在", code="record_not_found")
    await get_owned_case(db, record.case_id, user)

    if record.status == RecordStatus.CONFIRMED.value:
        raise ConflictError("记录已确认", code="record_already_confirmed")

    sections = _sections_from_json(record.draft_json)
    confirmed = sections.model_dump()
    record.status = RecordStatus.CONFIRMED.value
    record.confirmed_json = confirmed
    record.confirmed_at = datetime.now(UTC)

    version = await _next_version(db, record.id)
    content = {"sections": confirmed, "generated_by": "confirmed"}
    db.add(
        RecordVersion(
            record_id=record.id,
            version=version,
            content_json=content,
            editor_id=user.id,
        )
    )

    conversation = await db.get(Conversation, record.conversation_id)
    if conversation is not None:
        conversation.status = ConversationStatus.CONFIRMED.value

    await record_audit(
        db,
        actor_id=user.id,
        action=AuditAction.RECORD_CONFIRM.value,
        target_type="record",
        target_id=record.id,
        meta={"version": version},
        ip=ip,
    )
    await db.commit()
    await db.refresh(record)
    return build_record_read(
        record,
        version_count=await _version_count(db, record.id),
        change_rate=await _change_rate(db, record.id),
    )


def _sections_text(sections: RecordSections) -> str:
    """调试辅助：返回四段文本，便于日志或测试断言。"""
    return _content_text(sections)
