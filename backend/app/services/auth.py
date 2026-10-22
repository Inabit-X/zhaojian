"""注册 / 登录业务逻辑（中心版）。

学生可自助注册；咨询师与管理员账号由管理端开通。
"""

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.roles import Role
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserRead


def _to_auth_response(user: User) -> AuthResponse:
    """把用户对象组装成含访问令牌与用户信息的认证响应。"""
    return AuthResponse(
        access_token=create_access_token(user.id),
        user=UserRead.model_validate(user),
    )


def _normalize_phone(value: str | None) -> str | None:
    """去掉手机号中的空格与连字符；空串视为未填写。"""
    if value is None:
        return None
    normalized = value.replace(" ", "").replace("-", "")
    return normalized or None


async def _identifier_taken(
    db: AsyncSession, column: str, value: str | None
) -> bool:
    """查询指定登录标识是否已被占用。"""
    if not value:
        return False
    target = {"email": User.email, "student_no": User.student_no, "phone": User.phone}[column]
    return await db.scalar(select(User.id).where(target == value)) is not None


async def register(db: AsyncSession, payload: RegisterRequest) -> AuthResponse:
    """学生注册并签发访问令牌；标识冲突返回 409，并发冲突回滚后同样返回 409。"""
    email = str(payload.email).strip().lower() if payload.email else None
    student_no = payload.student_no
    phone = _normalize_phone(payload.phone)

    if await _identifier_taken(db, "email", email):
        raise ConflictError("该邮箱已注册", code="email_taken")
    if await _identifier_taken(db, "student_no", student_no):
        raise ConflictError("该学号已注册", code="student_no_taken")
    if await _identifier_taken(db, "phone", phone):
        raise ConflictError("该手机号已注册", code="phone_taken")
    if payload.username and await db.scalar(
        select(User.id).where(User.username == payload.username)
    ):
        raise ConflictError("该用户名已被占用", code="username_taken")

    # 自助注册只产生学生账号；role 不接受客户端传入。
    user = User(
        email=email,
        student_no=student_no,
        phone=phone,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=Role.STUDENT.value,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:  # 并发注册兜底
        await db.rollback()
        raise ConflictError("邮箱、学号、手机号或用户名已被占用", code="identity_taken") from exc
    await db.refresh(user)
    return _to_auth_response(user)


async def login(db: AsyncSession, payload: LoginRequest) -> AuthResponse:
    """校验登录标识与密码并签发访问令牌；凭据错误统一返回 401 以避免账号枚举。"""
    identifier = (payload.identifier or str(payload.email or "")).strip()
    if not identifier:
        raise AuthenticationError("邮箱、学号或手机号不正确", code="invalid_credentials")

    phone = _normalize_phone(identifier)
    user = await db.scalar(
        select(User)
        .where(
            or_(
                User.email == identifier.lower(),
                User.student_no == identifier,
                User.phone == phone,
            )
        )
        .limit(1)
    )
    # 不区分“用户不存在”和“密码错误”，避免账号枚举
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("账号或密码不正确", code="invalid_credentials")
    return _to_auth_response(user)
