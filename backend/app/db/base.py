"""声明式基类与统一约束命名约定。

命名约定保证 Alembic autogenerate 与手写迁移的约束名一致。
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    # CheckConstraint 必须显式命名，名称即最终名称（避免出现 ck_events_ck_events_* 双前缀）
    "ck": "%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """声明式基类：为所有模型提供统一的约束命名约定。"""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
