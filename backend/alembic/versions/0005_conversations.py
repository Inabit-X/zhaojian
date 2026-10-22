"""conversations / segments / extractions / records / record_versions

Revision ID: 0005_conversations
Revises: 0004_drop_legacy
Create Date: 2026-10-21

阶段 2A：文本对话入库、话语分段、事实抽取与四段记录草稿。
语音相关字段（source / start_ms / end_ms）先预留，不做转写。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_conversations"
down_revision: str | None = "0004_drop_legacy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _uuid_pk() -> sa.Column:
    """返回带 gen_random_uuid 默认值的 UUID 主键列。"""
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "conversations",
        _uuid_pk(),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("counselor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source",
            sa.String(length=16),
            server_default=sa.text("'text'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'segmented'"),
            nullable=False,
        ),
        sa.Column(
            "consent_confirmed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("transcript_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('segmented', 'extracted', 'drafted', 'confirmed', 'failed')",
            name="ck_conversations_status",
        ),
        sa.CheckConstraint(
            "source IN ('text', 'audio')",
            name="ck_conversations_source",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_conversations_case_id_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["counselor_id"],
            ["users.id"],
            name="fk_conversations_counselor_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
    )
    op.create_index(
        "ix_conversations_case_created",
        "conversations",
        ["case_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "segments",
        _uuid_pk(),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column(
            "speaker",
            sa.String(length=16),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
        sa.Column("start_ms", sa.Integer(), nullable=True),
        sa.Column("end_ms", sa.Integer(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "speaker IN ('client', 'counselor', 'unknown')",
            name="ck_segments_speaker",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_segments_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_segments"),
        sa.UniqueConstraint(
            "conversation_id",
            "idx",
            name="uq_segments_conversation_idx",
        ),
    )

    op.create_table(
        "extractions",
        _uuid_pk(),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("segment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column(
            "value_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column(
            "confidence",
            sa.Float(),
            server_default=sa.text("0.5"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('presenting_issue', 'event', 'emotion', 'cognition', "
            "'behavior', 'relationship', 'resource', 'intervention', "
            "'homework', 'risk', 'unclear')",
            name="ck_extractions_kind",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_extractions_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["segment_id"],
            ["segments.id"],
            name="fk_extractions_segment_id_segments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_extractions"),
    )
    op.create_index(
        "ix_extractions_conversation_kind",
        "extractions",
        ["conversation_id", "kind"],
    )

    op.create_table(
        "records",
        _uuid_pk(),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("counselor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column(
            "draft_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "confirmed_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "confirmed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed')",
            name="ck_records_status",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["cases.id"],
            name="fk_records_case_id_cases",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_records_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["counselor_id"],
            ["users.id"],
            name="fk_records_counselor_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_records"),
        sa.UniqueConstraint(
            "conversation_id",
            name="uq_records_conversation_id",
        ),
    )
    op.create_index(
        "ix_records_case_created",
        "records",
        ["case_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "record_versions",
        _uuid_pk(),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "content_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("editor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["record_id"],
            ["records.id"],
            name="fk_record_versions_record_id_records",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["editor_id"],
            ["users.id"],
            name="fk_record_versions_editor_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_record_versions"),
        sa.UniqueConstraint(
            "record_id",
            "version",
            name="uq_record_versions_record_version",
        ),
    )


def downgrade() -> None:
    op.drop_table("record_versions")
    op.drop_table("records")
    op.drop_table("extractions")
    op.drop_table("segments")
    op.drop_table("conversations")
