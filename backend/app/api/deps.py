"""FastAPI 依赖：数据库会话、当前登录用户与角色校验。"""

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.roles import Role
from app.core.security import InvalidTokenError, decode_access_token
from app.db.models import User
from app.db.session import get_db

_bearer_scheme = HTTPBearer(auto_error=False, description="登录接口返回的 JWT")


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """从 Bearer Token 解出当前用户；缺失、无效或已注销统一返回 401。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("缺少 Bearer token", code="missing_token")
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise AuthenticationError("登录已过期，请重新登录", code="invalid_token") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise AuthenticationError("用户不存在或已注销", code="user_not_found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


def require_roles(*roles: Role) -> Callable[[User], Awaitable[User]]:
    """生成角色校验依赖：当前用户角色不在允许集合时返回 403。"""
    allowed = {role.value for role in roles}
    role_names = "/".join(role.value for role in roles)

    async def _dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed:
            raise PermissionDeniedError(
                f"该操作需要角色：{role_names}",
                code="forbidden",
            )
        return current_user

    return _dependency


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
CounselorUser = Annotated[User, Depends(require_roles(Role.COUNSELOR))]
StudentUser = Annotated[User, Depends(require_roles(Role.STUDENT))]
AuditorUser = Annotated[User, Depends(require_roles(Role.AUDITOR))]
CaseViewer = Annotated[User, Depends(require_roles(Role.COUNSELOR, Role.STUDENT))]
AdminOrAuditor = Annotated[User, Depends(require_roles(Role.ADMIN, Role.AUDITOR))]
