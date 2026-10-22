from fastapi import APIRouter, status

from app.api.deps import CurrentUser
from app.core.exceptions import AppError

router = APIRouter(prefix="/privacy", tags=["privacy"])

_NOT_IMPLEMENTED = dict(
    code="not_implemented",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
)


@router.get(
    "/export",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="占位：导出我的全部数据",
)
async def export_my_data(current_user: CurrentUser) -> None:
    """数据导出占位：本期未实现，固定返回 501。"""
    raise AppError("数据导出属于后续阶段，接口已预留", **_NOT_IMPLEMENTED)


@router.delete(
    "/data",
    status_code=status.HTTP_501_NOT_IMPLEMENTED,
    summary="占位：删除我的全部数据",
)
async def delete_my_data(current_user: CurrentUser) -> None:
    """数据删除占位：本期未实现，固定返回 501。"""
    raise AppError("账号与数据删除属于后续阶段，接口已预留", **_NOT_IMPLEMENTED)
