"""测试夹具。

纯单元测试不依赖 PostgreSQL；RBAC/个案集成测试使用 db_client + db_session，
需要 TEST_DATABASE_URL（默认取 settings.test_database_url），数据库不可用时自动 skip。
"""

import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401  确保所有模型注册到 Base.metadata
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or settings.test_database_url
# 集成测试会重建测试库 schema，必须显式开启，避免默认命令误连数据库
RUN_DB_TESTS = os.getenv("RUN_DB_TESTS") == "1"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest.fixture
async def db_engine():
    """创建测试库引擎；未显式开启或连不上时 skip，而不是让整套测试失败。"""
    if not RUN_DB_TESTS:
        pytest.skip("未设置 RUN_DB_TESTS=1，跳过数据库集成测试")
    engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("TEST_DATABASE_URL 不可用，跳过集成测试")
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncIterator[AsyncSession]:
    """每个测试重建 schema，提供独立会话；表结构来自 ORM 元数据。

    先整库重建 public schema，避免历史库残留的旧表（events 等）通过外键
    阻塞 `drop_all`。
    """
    async with db_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as session:
        yield session


@pytest.fixture
async def db_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """使用测试会话的 HTTP 客户端；请求内 commit 对测试可见。"""

    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
            yield async_client
    finally:
        app.dependency_overrides.pop(get_db, None)
