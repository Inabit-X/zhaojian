from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.db.models import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="学生注册并直接登录",
)
async def register(payload: RegisterRequest, db: DbSession) -> AuthResponse:
    """学生注册并直接签发 JWT；邮箱/学号/手机号冲突返回 409。"""
    return await auth_service.register(db, payload)


@router.post("/login", response_model=AuthResponse, summary="邮箱/学号/手机号 + 密码登录")
async def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    """校验登录标识与密码后签发 JWT；凭证错误返回 401。"""
    return await auth_service.login(db, payload)


@router.get("/me", response_model=UserRead, summary="当前用户")
async def me(current_user: CurrentUser) -> User:
    """返回当前已登录用户的信息。"""
    return current_user


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="登出（客户端清除令牌）",
)
async def logout(_: CurrentUser) -> Response:
    """无状态 JWT 无法在服务端失效，返回 204，由客户端删除本地令牌。"""
    return Response(status_code=status.HTTP_204_NO_CONTENT)
