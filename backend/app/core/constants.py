"""业务常量：状态、角色相关枚举与审计动作名。"""

from enum import StrEnum


class CaseStatus(StrEnum):
    """个案状态。"""

    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ConversationStatus(StrEnum):
    """对话处理状态：分段 → 抽取 → 起草 → 确认。"""

    SEGMENTED = "segmented"
    EXTRACTED = "extracted"
    DRAFTED = "drafted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class SegmentSpeaker(StrEnum):
    """话语段说话人。"""

    CLIENT = "client"
    COUNSELOR = "counselor"
    UNKNOWN = "unknown"


class ExtractionKind(StrEnum):
    """事实抽取的固定类别；与数据库 CHECK 约束保持一致。"""

    PRESENTING_ISSUE = "presenting_issue"
    EVENT = "event"
    EMOTION = "emotion"
    COGNITION = "cognition"
    BEHAVIOR = "behavior"
    RELATIONSHIP = "relationship"
    RESOURCE = "resource"
    INTERVENTION = "intervention"
    HOMEWORK = "homework"
    RISK = "risk"
    UNCLEAR = "unclear"


class RecordStatus(StrEnum):
    """咨询记录状态：草稿 / 已确认。"""

    DRAFT = "draft"
    CONFIRMED = "confirmed"


class AuditAction(StrEnum):
    """审计动作名，统一在此定义避免拼写漂移。"""

    COUNSELOR_CREATE = "counselor.create"
    CASE_CREATE = "case.create"
    CASE_VIEW = "case.view"
    CONVERSATION_CREATE = "conversation.create"
    CONVERSATION_VIEW = "conversation.view"
    CONVERSATION_EXTRACT = "conversation.extract"
    RECORD_DRAFT = "record.draft"
    RECORD_VIEW = "record.view"
    RECORD_UPDATE = "record.update"
    RECORD_CONFIRM = "record.confirm"
