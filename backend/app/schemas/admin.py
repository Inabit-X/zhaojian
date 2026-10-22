"""管理端请求/响应模型：咨询师开通与审计日志。"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.auth import UserRead


class CounselorCreate(BaseModel):
    """管理员开通咨询师账号。"""

    email: EmailStr
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class CounselorListResponse(BaseModel):
    """咨询师分页响应。"""

    items: list[UserRead]
    total: int
    offset: int
    limit: int


class AuditLogRead(BaseModel):
    """审计日志响应；数据库列名为 metadata，ORM 属性名为 meta。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: uuid.UUID | None
    action: str
    target_type: str | None
    target_id: uuid.UUID | None
    metadata: dict[str, Any] = Field(validation_alias="meta")
    ip: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """审计日志分页响应。"""

    items: list[AuditLogRead]
    total: int
    offset: int
    limit: int
