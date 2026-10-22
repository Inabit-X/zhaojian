"""数据权利相关占位模型：仅接口契约，本期返回 501。"""

from pydantic import BaseModel


class DataExportResponse(BaseModel):
    """数据导出响应占位：仅返回提示文案，本期不真正导出。"""

    message: str


class DataDeleteResponse(BaseModel):
    """数据删除响应占位：仅返回提示文案，本期不真正删除。"""

    message: str
