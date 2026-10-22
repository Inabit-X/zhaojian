"""咨询记录与版本留痕（阶段 2A）。

一场对话对应一条记录：draft_json 保存四段草稿，confirmed_json 保存咨询师确认稿；
每次保存/确认都写一条 record_versions，用于计算修改率。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import RecordStatus
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.db.models.conversation import Conversation


class Record(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """一次咨询记录：草稿 → 编辑 → 确认。"""

    __tablename__ = "records"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'confirmed')", name="ck_records_status"),
        UniqueConstraint("conversation_id", name="uq_records_conversation_id"),
        Index("ix_records_case_created", "case_id", text("created_at DESC")),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    counselor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=RecordStatus.DRAFT.value,
        server_default=text("'draft'"),
    )
    draft_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    confirmed_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="record")

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        """返回便于调试的记录标识字符串。"""
        return f"<Record id={self.id} status={self.status}>"


class RecordVersion(UUIDPrimaryKeyMixin, Base):
    """记录内容的不可变版本快照；version 在记录内从 1 递增。"""

    __tablename__ = "record_versions"
    __table_args__ = (
        UniqueConstraint("record_id", "version", name="uq_record_versions_record_version"),
    )

    record_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("records.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    editor_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        """返回便于调试的版本标识字符串。"""
        return f"<RecordVersion record_id={self.record_id} version={self.version}>"


__all__ = ["Record", "RecordStatus", "RecordVersion"]
