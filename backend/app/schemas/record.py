"""咨询记录（四段）请求/响应模型。"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RecordSections(BaseModel):
    """四段式记录：主诉与背景、观察、个案概念化、计划。"""

    presenting: str = Field(default="", max_length=5000)
    observations: str = Field(default="", max_length=5000)
    formulation: str = Field(default="", max_length=5000)
    plan: str = Field(default="", max_length=5000)

    model_config = ConfigDict(extra="forbid")


class RecordDraftRequest(BaseModel):
    """生成草稿的选项；use_llm=false 时强制使用规则模板。"""

    use_llm: bool = True

    model_config = ConfigDict(extra="forbid")


class RecordUpdateRequest(BaseModel):
    """咨询师编辑草稿；只允许替换四段文本。"""

    sections: RecordSections

    model_config = ConfigDict(extra="forbid")


class RecordRead(BaseModel):
    """记录响应：sections 来自 draft_json / confirmed_json 的规范化结果。"""

    id: uuid.UUID
    case_id: uuid.UUID
    conversation_id: uuid.UUID
    status: str
    sections: RecordSections
    generated_by: str | None = None
    version_count: int = 0
    change_rate: float | None = None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
