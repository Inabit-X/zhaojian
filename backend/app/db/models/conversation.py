"""对话与话语段、事实抽取模型（阶段 2A，仅文本）。

数据链路：conversation 1—N segment 1—N extraction。
原文 transcript_text 属于敏感数据，本期仅存库，不做加密（见 TODO）。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ConversationStatus, ExtractionKind, SegmentSpeaker
from app.db.base import Base
from app.db.mixins import CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.record import Record


class Conversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """一次咨询对话（本期为文本粘贴，语音转写后续接入）。"""

    __tablename__ = "conversations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('segmented', 'extracted', 'drafted', 'confirmed', 'failed')",
            name="ck_conversations_status",
        ),
        CheckConstraint("source IN ('text', 'audio')", name="ck_conversations_source"),
        Index(
            "ix_conversations_case_created",
            "case_id",
            text("created_at DESC"),
        ),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    counselor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    session_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="text",
        server_default=text("'text'"),
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ConversationStatus.SEGMENTED.value,
        server_default=text("'segmented'"),
    )
    consent_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)

    segments: Mapped[list[Segment]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Segment.idx",
    )
    extractions: Mapped[list[Extraction]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    record: Mapped["Record | None"] = relationship(
        back_populates="conversation",
        uselist=False,
        passive_deletes=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        """返回便于调试的对话标识字符串。"""
        return f"<Conversation id={self.id} case_id={self.case_id} status={self.status}>"


class Segment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """按说话人切分后的话语段；idx 在对话内从 0 递增。"""

    __tablename__ = "segments"
    __table_args__ = (
        CheckConstraint(
            "speaker IN ('client', 'counselor', 'unknown')",
            name="ck_segments_speaker",
        ),
        UniqueConstraint("conversation_id", "idx", name="uq_segments_conversation_idx"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=SegmentSpeaker.UNKNOWN.value,
        server_default=text("'unknown'"),
    )
    start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    conversation: Mapped[Conversation] = relationship(back_populates="segments")

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        """返回便于调试的话语段标识字符串。"""
        return f"<Segment id={self.id} idx={self.idx} speaker={self.speaker}>"


class Extraction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """从单个话语段抽取的一条事实；quote 必须来自该段原文。"""

    __tablename__ = "extractions"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('presenting_issue', 'event', 'emotion', 'cognition', "
            "'behavior', 'relationship', 'resource', 'intervention', "
            "'homework', 'risk', 'unclear')",
            name="ck_extractions_kind",
        ),
        Index("ix_extractions_conversation_kind", "conversation_id", "kind"),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        server_default=text("0.5"),
    )

    conversation: Mapped[Conversation] = relationship(back_populates="extractions")
    segment: Mapped[Segment] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        """返回便于调试的抽取标识字符串。"""
        return f"<Extraction id={self.id} kind={self.kind}>"


__all__ = [
    "Conversation",
    "Extraction",
    "ExtractionKind",
    "Segment",
    "SegmentSpeaker",
]
