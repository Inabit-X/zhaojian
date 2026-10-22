"""应用配置：全部来自环境变量 / .env，禁止在代码中硬编码密钥。"""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "please-change-me-to-a-random-64-hex-string"


class Settings(BaseSettings):
    """应用配置：从环境变量与 .env 读取，并在启动期做安全校验。"""

    model_config = SettingsConfigDict(
        # 本地在 backend/ 下运行时读父级根 .env；容器内由 compose 注入环境变量
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # 应用
    app_name: str = "own_partner"
    app_env: str = "development"
    debug: bool = False
    secret_key: str = DEFAULT_SECRET
    access_token_expire_minutes: int = 60 * 24
    # 逗号分隔；在 property 中拆分，避免 pydantic-settings 对 list 的 JSON 解析要求
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    # 数据库
    database_url: str = (
        "postgresql+asyncpg://own_partner:own_partner_dev@localhost:5432/own_partner"
    )

    # Embedding provider
    embedding_provider: str = "fake"
    embedding_dim: int = 1536
    embedding_model: str = "text-embedding-3-small"
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = ""
    embedding_batch_size: int = 64
    embedding_timeout_seconds: float = 30.0

    # LLM provider（本期不调用，仅占位）
    llm_provider: str = "openai_compat"
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 60.0

    # 切片
    chunk_size: int = Field(default=400, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0)
    max_chunks_per_event: int = Field(default=100, ge=1)

    # 可选异步任务（本期不启用）
    redis_url: str = "redis://localhost:6379/0"

    # 测试
    test_database_url: str = (
        "postgresql+asyncpg://own_partner:own_partner_dev@localhost:5432/own_partner_test"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """把逗号分隔的 CORS 配置解析成来源列表。"""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def docs_enabled(self) -> bool:
        """判断当前环境是否开放 OpenAPI 文档。"""
        return self.app_env != "production" or self.debug

    @model_validator(mode="after")
    def _validate_security(self) -> "Settings":
        """校验生产密钥、切片重叠与向量维度等启动期约束。"""
        if self.app_env == "production" and self.secret_key == DEFAULT_SECRET:
            raise ValueError("生产环境必须通过 SECRET_KEY 设置独立的随机密钥")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP 必须小于 CHUNK_SIZE")
        if self.embedding_dim != 1536:
            raise ValueError("embedding_dim 固定为 1536，与阶段 3 档案摘要向量列保持一致")
        return self


@lru_cache
def get_settings() -> Settings:
    """返回进程内缓存的应用配置单例。"""
    return Settings()


settings = get_settings()
