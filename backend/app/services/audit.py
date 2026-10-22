"""审计日志写入与查询（只追加，不提供修改/删除）。"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


async def record_audit(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
    ip: str | None = None,
) -> None:
    """在调用方事务内追加一条审计记录；是否提交由调用方决定。"""
    db.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            meta=meta or {},
            ip=ip,
        )
    )


async def list_audit_logs(
    db: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 20,
    action: str | None = None,
) -> tuple[list[AuditLog], int]:
    """按时间倒序分页查询审计日志，可按 action 精确过滤。"""
    condition = AuditLog.action == action if action else None
    count_stmt = select(func.count()).select_from(AuditLog)
    stmt = select(AuditLog)
    if condition is not None:
        count_stmt = count_stmt.where(condition)
        stmt = stmt.where(condition)
    total = await db.scalar(count_stmt) or 0
    items = (
        await db.scalars(stmt.order_by(AuditLog.id.desc()).offset(offset).limit(limit))
    ).all()
    return list(items), total
