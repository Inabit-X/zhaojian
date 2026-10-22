from __future__ import annotations

from sqlalchemy import CheckConstraint, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.roles import Role
from app.db.base import Base
from app.db.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """用户账号：支持邮箱/学号/手机号登录，密码只存 Argon2 哈希。

    旧版账号迁移后 role 统一为 student；咨询师与管理员由中心开通。
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'counselor', 'admin', 'auditor')",
            name="ck_users_role",
        ),
    )

    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    student_no: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)
    username: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=Role.STUDENT.value,
        server_default=text("'student'"),
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试辅助
        """返回便于调试的用户标识字符串。"""
        return f"<User id={self.id} email={self.email} role={self.role}>"
