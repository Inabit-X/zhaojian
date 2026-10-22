"""对话、话语段与事实抽取的请求/响应模型。"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Speaker = Literal["client", "counselor", "unknown"]

ExtractionKind = Literal[
    "presenting_issue",
    "event",
    "emotion",
    "cognition",
    "behavior",
    "relationship",
    "resource",
    "intervention",
    "homework",
    "risk",
    "unclear",
]


class SegmentInput(BaseModel):
    """手工分段输入；start_ms/end_ms 预留给后续语音对齐。"""

    speaker: Speaker = "unknown"
    text: str = Field(min_length=1, max_length=4000)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")


class ConversationCreate(BaseModel):
    """创建对话：粘贴全文或直接给分段，二选一；必须确认已获知情同意。"""

    session_date: datetime
    consent_confirmed: bool
    transcript_text: str | None = Field(default=None, max_length=100_000)
    segments: list[SegmentInput] | None = Field(default=None, max_length=500)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_input(self) -> "ConversationCreate":
        """校验知情同意、输入二选一、时间时区与未来时间。"""
        if not self.consent_confirmed:
            raise ValueError("必须确认已获得来访者知情同意")
        if (self.transcript_text is None) == (self.segments is None):
            raise ValueError("transcript_text 与 segments 必须且只能提供一个")
        if self.session_date.tzinfo is None or self.session_date.utcoffset() is None:
            raise ValueError("session_date 必须包含时区")
        if self.session_date > datetime.now(UTC) + timedelta(minutes=5):
            raise ValueError("session_date 不能晚于当前时间")
        return self


class SegmentRead(BaseModel):
    """话语段响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    idx: int
    speaker: str
    start_ms: int | None
    end_ms: int | None
    text: str


class ExtractionRead(BaseModel):
    """单条事实抽取响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    segment_id: uuid.UUID
    kind: str
    value_json: dict[str, object]
    quote: str | None
    confidence: float


class ConversationRead(BaseModel):
    """对话列表项；计数由服务层填充。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    counselor_id: uuid.UUID | None
    session_date: datetime
    source: str
    status: str
    consent_confirmed: bool
    created_at: datetime
    updated_at: datetime
    segment_count: int = 0
    extraction_count: int = 0


class ConversationDetail(ConversationRead):
    """对话详情：包含全部分段、抽取结果与关联记录 id。"""

    segments: list[SegmentRead] = Field(default_factory=list)
    extractions: list[ExtractionRead] = Field(default_factory=list)
    record_id: uuid.UUID | None = None


class ConversationListResponse(BaseModel):
    """对话分页响应。"""

    items: list[ConversationRead]
    total: int
    offset: int
    limit: int


class ConversationExtractRequest(BaseModel):
    """重新抽取的选项；use_llm=false 时只用规则版。"""

    use_llm: bool = True

    model_config = ConfigDict(extra="forbid")
