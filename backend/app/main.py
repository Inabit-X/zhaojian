"""FastAPI 应用入口：中间件、异常映射、路由挂载。"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.db.session import engine

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("own_partner")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动时记录运行环境，关闭时释放数据库连接池。"""
    logger.info("own_partner 启动，env=%s", settings.app_env)
    yield
    await engine.dispose()


app = FastAPI(
    title="own_partner API（心理中心版）",
    description=(
        "「照见」高校心理中心临床文书与随访支持系统 MVP。\n\n"
        "非医疗产品：不提供心理诊断或治疗决策，不替代咨询师判断。"
    ),
    version="0.2.0",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_body(code: str, message: str, details: object | None = None) -> dict:
    """组装统一错误响应体，details 缺省时仍保留该字段。"""
    return {"code": code, "message": message, "details": details}


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """把业务异常 AppError 映射为统一 JSON 错误，状态码取自异常本身。"""
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(exc.code, exc.message, exc.details),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    """把请求参数校验错误裁剪为 loc/msg/type 后返回 422，避免泄露内部对象。"""
    # 只回传稳定字段，避免 ctx 中的异常对象无法 JSON 序列化
    details = [
        {
            "loc": list(error.get("loc", [])),
            "msg": error.get("msg", ""),
            "type": error.get("type", ""),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=_error_body("validation_error", "请求参数校验失败", details),
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """把 HTTPException 统一成错误体，兼容 detail 为 {code,message,details} 的写法。"""
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail:
        body = _error_body(
            str(detail.get("code")),
            str(detail.get("message", "")),
            detail.get("details"),
        )
    else:
        body = _error_body("http_error", str(detail))
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """兜底未捕获异常：记录堆栈，对外只返回通用 500 文案。"""
    logger.exception("未处理异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_body("internal_error", "服务内部错误"),
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """根路径返回服务名、版本与免责声明，同时可用于探活。"""
    return {
        "service": "own_partner",
        "version": "0.2.0",
        "disclaimer": "非医疗产品，不提供心理诊断或治疗，不替代专业帮助。",
    }


app.include_router(api_router)
