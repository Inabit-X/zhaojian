"""统一的业务异常，由 main.py 转为稳定的错误响应结构。"""

from typing import Any


class AppError(Exception):
    """业务异常基类：携带 HTTP 状态码、错误码与可选详情。"""

    status_code = 400
    code = "bad_request"
    message = "请求无效"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        """用可选参数覆盖默认的消息、错误码、状态码与详情。"""
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details
        super().__init__(self.message)


class ConflictError(AppError):
    """资源冲突（409）业务异常。"""

    status_code = 409
    code = "conflict"
    message = "资源冲突"


class NotFoundError(AppError):
    """资源不存在（404）业务异常。"""

    status_code = 404
    code = "not_found"
    message = "资源不存在"


class AuthenticationError(AppError):
    """未认证或凭证无效（401）业务异常。"""

    status_code = 401
    code = "unauthorized"
    message = "未认证或凭证无效"


class PermissionDeniedError(AppError):
    """已认证但角色无权执行该操作（403）业务异常。"""

    status_code = 403
    code = "forbidden"
    message = "无权访问该资源"


class ProviderError(AppError):
    """模型服务不可用。"""

    status_code = 503
    code = "provider_unavailable"
    message = "模型服务暂时不可用"
