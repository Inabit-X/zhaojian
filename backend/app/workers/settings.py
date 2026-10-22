"""ARQ worker 占位。

启用方式：docker compose --profile async up -d
本期不依赖 Redis；任务函数保留签名，后续补实现。
"""


async def ping(ctx: dict) -> str:  # pragma: no cover - 手工验证用
    """返回 pong，供手工验证 worker 存活。"""
    return "pong"


class WorkerSettings:
    """ARQ worker 配置：注册任务函数并按需懒加载 Redis 连接。"""

    functions = [ping]
    # 延迟导入，避免未安装 arq 时影响主应用
    try:
        from arq.connections import RedisSettings

        from app.core.config import settings

        redis_settings = RedisSettings.from_dsn(settings.redis_url)
    except ImportError:  # pragma: no cover
        redis_settings = None
