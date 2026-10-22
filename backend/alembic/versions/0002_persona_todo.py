"""persona 占位迁移（本期不建表）

Revision ID: 0002_persona_todo
Revises: 0001_initial
Create Date: 2026-10-19

本期只保存智能体草稿，不做人格推理。后续将新增：

- user_personas
    id, user_id, directness, empathy, challenge, boundaries,
    confidence, source, user_confirmed, created_at, updated_at
- persona_signals
    id, user_id, signal_type(self_report/corpus/behavior),
    payload(jsonb), created_at

实现时必须同时提供：用户可见、可确认、可修改、可关闭的画像接口。
"""

from collections.abc import Sequence

revision: str = "0002_persona_todo"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 故意留空：人格画像属于后续阶段。
    pass


def downgrade() -> None:
    pass
