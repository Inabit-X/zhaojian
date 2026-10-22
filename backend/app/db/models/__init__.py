"""确保所有模型在导入 Base.metadata 前完成注册（Alembic 依赖）。"""

from app.db.models.audit import AuditLog
from app.db.models.case import Case
from app.db.models.conversation import Conversation, Extraction, Segment
from app.db.models.record import Record, RecordVersion
from app.db.models.user import User

__all__ = [
    "AuditLog",
    "Case",
    "Conversation",
    "Extraction",
    "Record",
    "RecordVersion",
    "Segment",
    "User",
]
