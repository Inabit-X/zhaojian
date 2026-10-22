"""个案相关请求/响应模型。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    """管理员创建个案：学生标识 + 接案咨询师。"""

    student_identifier: str = Field(min_length=1, max_length=255)
    counselor_id: uuid.UUID


class CaseRead(BaseModel):
    """个案响应；不包含任何咨询记录内容。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    student_id: uuid.UUID
    counselor_id: uuid.UUID | None
    status: str
    opened_at: datetime
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CaseListResponse(BaseModel):
    """个案分页响应。"""

    items: list[CaseRead]
    total: int
    offset: int
    limit: int
