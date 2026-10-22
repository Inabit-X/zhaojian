"""会谈创建与记录编辑的 schema 校验测试。"""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.conversation import ConversationCreate, SegmentInput
from app.schemas.record import RecordSections, RecordUpdateRequest


def test_conversation_requires_consent() -> None:
    """未确认知情同意不得入库。"""
    with pytest.raises(ValidationError):
        ConversationCreate(
            session_date=datetime.now(UTC),
            consent_confirmed=False,
            transcript_text="来访者：你好",
        )


def test_conversation_requires_text_or_segments() -> None:
    """全文与手工分段至少提供一个。"""
    with pytest.raises(ValidationError):
        ConversationCreate(
            session_date=datetime.now(UTC), consent_confirmed=True
        )


def test_conversation_rejects_naive_datetime() -> None:
    """会谈时间必须带时区。"""
    with pytest.raises(ValidationError):
        ConversationCreate(
            session_date=datetime(2026, 1, 1),
            consent_confirmed=True,
            transcript_text="来访者：你好",
        )


def test_conversation_accepts_manual_segments() -> None:
    """手工分段路径应可用。"""
    payload = ConversationCreate(
        session_date=datetime.now(UTC),
        consent_confirmed=True,
        segments=[SegmentInput(speaker="client", text="你好")],
    )
    assert payload.transcript_text is None
    assert payload.segments is not None


def test_record_update_requires_a_section() -> None:
    """空 PATCH 无意义，应被拒绝。"""
    with pytest.raises(ValidationError):
        RecordUpdateRequest()


def test_record_sections_forbid_extra_fields() -> None:
    """四段结构之外不允许夹带字段。"""
    with pytest.raises(ValidationError):
        RecordSections(
            presenting="a",
            observations="b",
            formulation="c",
            plan="d",
            extra="x",
        )
