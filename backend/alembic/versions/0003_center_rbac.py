"""center rbac: users 角色化 + cases + audit_logs

Revision ID: 0003_center_rbac
Revises: 0002_persona_todo
Create Date: 2026-10-19

阶段 1（中心版）迁移：
- users.email 放开为可空；新增 role / student_no / phone
- 新建 cases（个案归属与分配）
- 新建 audit_logs（只追加审计）

不触碰 events / event_chunks / agent_drafts；旧账号 role 回填为 student。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_center_rbac"
down_revision: str | None = "0002_persona_todo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users：放开 email，增加角色与学号/手机号
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=16),
            server_default=sa.text("'student'"),
            nullable=False,
        ),
    )
    op.add_column("users", sa.Column("student_no", sa.String(length=32), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))
    op.create_unique_constraint("uq_users_student_no", "users", ["student_no"])
    op.create_unique_constraint("uq_users_phone", "users", ["phone"])
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('student', 'counselor', 'admin', 'auditor')",
    )

    # 2. cases：个案归属
    op.create_table(
        "cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("counselor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
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
            "status IN ('active', 'closed', 'archived')",
            name="ck_cases_status",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            name="fk_cases_student_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["counselor_id"],
            ["users.id"],
            name="fk_cases_counselor_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cases"),
    )
    op.create_index("ix_cases_counselor_status", "cases", ["counselor_id", "status"])
    op.create_index("ix_cases_student", "cases", ["student_id"])

    # 3. audit_logs：只追加
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_audit_logs_actor_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_logs"),
    )
    op.create_index(
        "ix_audit_logs_actor_created",
        "audit_logs",
        ["actor_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "ix_audit_logs_target",
        "audit_logs",
        ["target_type", "target_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("cases")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_constraint("uq_users_student_no", "users", type_="unique")
    op.drop_constraint("uq_users_phone", "users", type_="unique")
    op.drop_column("users", "phone")
    op.drop_column("users", "student_no")
    op.drop_column("users", "role")
    # 若已存在无邮箱账号，此步会失败：仅开发环境回滚。
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(length=255),
        nullable=False,
    )
