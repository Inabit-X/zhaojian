"""管理端业务：开通咨询师、查询审计。"""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction
from app.core.exceptions import ConflictError
from app.core.roles import Role
from app.core.security import hash_password
from app.db.models import User
from app.schemas.admin import CounselorCreate
from app.services.audit import list_audit_logs, record_audit

__all__ = ["create_counselor", "list_audit_logs", "list_counselors"]


async def create_counselor(
    db: AsyncSession,
    payload: CounselorCreate,
    *,
    actor: User,
    ip: str | None = None,
) -> User:
    """管理员开通咨询师账号，并写入审计。"""
    email = str(payload.email).strip().lower()
    username = payload.username.strip()

    if await db.scalar(select(User.id).where(User.email == email)):
        raise ConflictError("该邮箱已注册", code="email_taken")
    if await db.scalar(select(User.id).where(User.username == username)):
        raise ConflictError("该用户名已被占用", code="username_taken")

    counselor = User(
        email=email,
        username=username,
        password_hash=hash_password(payload.password),
        role=Role.COUNSELOR.value,
    )
    db.add(counselor)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("邮箱或用户名已被占用", code="identity_taken") from exc

    await record_audit(
        db,
        actor_id=actor.id,
        action=AuditAction.COUNSELOR_CREATE.value,
        target_type="user",
        target_id=counselor.id,
        ip=ip,
    )
    await db.commit()
    await db.refresh(counselor)
    return counselor


async def list_counselors(
    db: AsyncSession, *, offset: int = 0, limit: int = 20
) -> tuple[list[User], int]:
    """分页返回咨询师账号。"""
    condition = User.role == Role.COUNSELOR.value
    total = await db.scalar(select(func.count()).select_from(User).where(condition)) or 0
    items = (
        await db.scalars(
            select(User)
            .where(condition)
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return list(items), total
