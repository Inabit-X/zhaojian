"""密码哈希与 JWT 签发/校验。"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

ALGORITHM = "HS256"

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """用 Argon2id 生成密码哈希。"""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否匹配，异常时返回 False。"""
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        # 损坏或未知格式的哈希一律视为校验失败，不向调用方泄露细节
        return False


def create_access_token(user_id: uuid.UUID) -> str:
    """为用户 ID 签发带过期时间的 HS256 访问令牌。"""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


class InvalidTokenError(Exception):
    """JWT 无效、过期或缺少 subject。"""


def decode_access_token(token: str) -> uuid.UUID:
    """解码并校验访问令牌，返回其中的用户 ID。"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if not subject:
            raise InvalidTokenError("token 缺少 sub")
        return uuid.UUID(subject)
    except (jwt.PyJWTError, ValueError) as exc:
        raise InvalidTokenError("token 无效或已过期") from exc
