"""系统角色定义。"""

from enum import StrEnum


class Role(StrEnum):
    """账号角色；数据库中存字符串值。"""

    STUDENT = "student"
    COUNSELOR = "counselor"
    ADMIN = "admin"
    AUDITOR = "auditor"


ALL_ROLES: tuple[str, ...] = tuple(role.value for role in Role)
