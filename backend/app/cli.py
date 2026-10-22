"""管理命令行：创建首个管理员账号。

用法（在 backend/ 下、已配置 DATABASE_URL）：

    python -m app.cli create-admin --email admin@example.com --password 'ChangeMe123' --name 管理员
"""

import argparse
import asyncio

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select

from app.core.roles import Role
from app.core.security import hash_password
from app.db.models import User
from app.db.session import SessionLocal


async def _create_admin(email: str, password: str, name: str) -> None:
    """创建管理员账号；邮箱已存在时退出并提示。"""
    try:
        normalized = str(TypeAdapter(EmailStr).validate_python(email.strip().lower()))
    except ValueError as exc:
        raise SystemExit(f"邮箱格式不正确：{email}") from exc
    if len(password) < 8:
        raise SystemExit("密码至少 8 位")
    async with SessionLocal() as db:
        existing = await db.scalar(select(User.id).where(User.email == normalized))
        if existing is not None:
            raise SystemExit(f"邮箱已存在：{normalized}")
        user = User(
            email=normalized,
            username=name.strip(),
            password_hash=hash_password(password),
            role=Role.ADMIN.value,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"管理员已创建：{normalized}（id={user.id}）")


def main() -> None:
    """解析子命令并执行。"""
    parser = argparse.ArgumentParser(description="own_partner 管理命令")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin = subparsers.add_parser("create-admin", help="创建管理员账号")
    create_admin.add_argument("--email", required=True, help="管理员邮箱")
    create_admin.add_argument("--password", required=True, help="初始密码（至少 8 位）")
    create_admin.add_argument("--name", default="管理员", help="显示名")

    args = parser.parse_args()
    if args.command == "create-admin":
        asyncio.run(_create_admin(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
