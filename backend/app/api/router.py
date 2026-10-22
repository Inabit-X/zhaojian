"""汇总 /api/v1 下各业务路由。"""

from fastapi import APIRouter

from app.api.routes import (
    admin,
    auth,
    cases,
    conversations,
    health,
    privacy,
    records,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(cases.router)
api_router.include_router(conversations.router)
api_router.include_router(records.router)
api_router.include_router(privacy.router)
