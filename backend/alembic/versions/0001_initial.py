"""init: users / events / event_chunks / agent_drafts

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-19

本期只建立最小数据模型：
- users：注册登录
- events：用户事件原始层
- event_chunks：事件切片与向量（pgvector）
- agent_drafts：智能体草稿/模板配置

人格画像表、摘要层表、对话表均不在本期，见 0002 占位迁移与 docs/todo.md。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    op.create_table(
        "events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("thought", sa.Text(), nullable=True),
        sa.Column("emotion", sa.String(length=32), nullable=True),
        sa.Column("emotion_intensity", sa.SmallInteger(), nullable=True),
        sa.Column("behavior", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(raw_text) BETWEEN 1 AND 20000",
            name="ck_events_raw_text_length",
        ),
        sa.CheckConstraint(
            "emotion_intensity IS NULL OR (emotion_intensity BETWEEN 0 AND 10)",
            name="ck_events_emotion_intensity",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_events_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
    )
    op.create_index(
        "ix_events_user_occurred",
        "events",
        ["user_id", sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_events_user_created",
        "events",
        ["user_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "event_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["events.id"],
            name="fk_event_chunks_event_id_events",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_event_chunks_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_event_chunks"),
        sa.UniqueConstraint(
            "event_id",
            "chunk_index",
            name="uq_event_chunks_event_chunk",
        ),
    )
    op.create_index("ix_event_chunks_user", "event_chunks", ["user_id"])
    # 语义检索落地时再建 HNSW 索引，避免本期写入期的无谓成本。

    op.create_table(
        "agent_drafts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "persona_desc",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False,
        ),
        sa.Column(
            "style_params",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text(
                """'{"directness": 0.5, "empathy": 0.5, "challenge": 0.3, "boundaries": 0.5}'::jsonb"""
            ),
            nullable=False,
        ),
        sa.Column(
            "memory_scope",
            sa.String(length=32),
            server_default=sa.text("'all_events'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
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
        sa.CheckConstraint("status = 'draft'", name="ck_agent_drafts_status_draft"),
        sa.CheckConstraint(
            "memory_scope IN ('all_events', 'recent_90d', 'recent_30d', 'none')",
            name="ck_agent_drafts_memory_scope",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_agent_drafts_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_agent_drafts"),
    )
    op.create_index(
        "ix_agent_drafts_user_created",
        "agent_drafts",
        ["user_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_table("agent_drafts")
    op.drop_table("event_chunks")
    op.drop_table("events")
    op.drop_table("users")
    # 不删除 vector 扩展：可能被其他 schema 使用。
