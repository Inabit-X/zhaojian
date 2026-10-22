"""个案业务：创建、按角色过滤查询、查看留痕。

权限原则：
- 咨询师只能访问 counselor_id 等于自己的个案；
- 学生只能访问 student_id 等于自己的个案；
- 管理员/审计员不通过本模块读取个案内容。
越权访问统一抛 404，避免泄露个案是否存在。
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AuditAction, CaseStatus
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.roles import Role
from app.db.models import Case, User
from app.schemas.case import CaseCreate
from app.services.audit import record_audit

__all__ = ["create_case", "get_case", "list_cases"]


def _normalize_phone(value: str) -> str:
    """去掉手机号中的空格与连字符。"""
    return value.replace(" ", "").replace("-", "")


async def _find_user_by_identifier(db: AsyncSession, identifier: str) -> User | None:
    """按邮箱/学号/手机号查找账号，返回第一条匹配。"""
    value = identifier.strip()
    return await db.scalar(
        select(User)
        .where(
            or_(
                User.email == value.lower(),
                User.student_no == value,
                User.phone == _normalize_phone(value),
            )
        )
        .limit(1)
    )


async def create_case(
    db: AsyncSession,
    payload: CaseCreate,
    *,
    actor: User,
    ip: str | None = None,
) -> Case:
    """管理员创建个案并分配咨询师；学生与咨询师角色必须匹配。"""
    student = await _find_user_by_identifier(db, payload.student_identifier)
    if student is None or student.role != Role.STUDENT.value:
        raise NotFoundError("学生账号不存在", code="student_not_found")

    counselor = await db.get(User, payload.counselor_id)
    if counselor is None or counselor.role != Role.COUNSELOR.value:
        raise NotFoundError("咨询师账号不存在", code="counselor_not_found")

    case_record = Case(
        student_id=student.id,
        counselor_id=counselor.id,
        status=CaseStatus.ACTIVE.value,
    )
    db.add(case_record)
    await db.flush()

    await record_audit(
        db,
        actor_id=actor.id,
        action=AuditAction.CASE_CREATE.value,
        target_type="case",
        target_id=case_record.id,
        meta={"counselor_id": str(counselor.id)},
        ip=ip,
    )
    await db.commit()
    await db.refresh(case_record)
    return case_record


def _visibility_condition(user: User):
    """返回当前角色可见个案的 SQL 条件；不可见角色直接 403。"""
    if user.role == Role.COUNSELOR.value:
        return Case.counselor_id == user.id
    if user.role == Role.STUDENT.value:
        return Case.student_id == user.id
    raise PermissionDeniedError("该角色无权查看个案", code="forbidden")


async def list_cases(
    db: AsyncSession, *, user: User, offset: int = 0, limit: int = 20
) -> tuple[list[Case], int]:
    """按角色可见范围分页返回个案。"""
    condition = _visibility_condition(user)
    total = await db.scalar(select(func.count()).select_from(Case).where(condition)) or 0
    items = (
        await db.scalars(
            select(Case)
            .where(condition)
            .order_by(Case.opened_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    return list(items), total


async def get_case(
    db: AsyncSession,
    case_id: uuid.UUID,
    *,
    user: User,
    ip: str | None = None,
) -> Case:
    """返回个案详情；越权或不存在均返回 404，并记录查看审计。"""
    case_record = await db.get(Case, case_id)
    if case_record is None:
        raise NotFoundError("个案不存在", code="case_not_found")

    if user.role == Role.COUNSELOR.value:
        allowed = case_record.counselor_id == user.id
    elif user.role == Role.STUDENT.value:
        allowed = case_record.student_id == user.id
    else:
        raise PermissionDeniedError("该角色无权查看个案", code="forbidden")

    if not allowed:
        raise NotFoundError("个案不存在", code="case_not_found")

    await record_audit(
        db,
        actor_id=user.id,
        action=AuditAction.CASE_VIEW.value,
        target_type="case",
        target_id=case_record.id,
        ip=ip,
    )
    await db.commit()
    return case_record
