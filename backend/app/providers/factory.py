"""Provider 工厂：按配置选择实现，业务代码不感知具体厂商。"""

from collections.abc import Sequence
from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.providers.base import EmbeddingProvider, LLMProvider
from app.providers.fake import FakeEmbeddingProvider
from app.providers.llm_openai import OpenAICompatLLMProvider
from app.providers.openai_compat import OpenAIEmbeddingProvider


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """按配置返回带缓存的 embedding provider 单例；fake 为默认。"""
    name = settings.embedding_provider.strip().lower()
    if name == "fake":
        return FakeEmbeddingProvider(dimension=settings.embedding_dim)
    if name in {"openai", "openai_compat", "openai-compatible"}:
        if not settings.embedding_api_key:
            raise ProviderError("EMBEDDING_API_KEY 未配置，无法使用远程 embedding")
        return OpenAIEmbeddingProvider(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
            model=settings.embedding_model,
            dimension=settings.embedding_dim,
            batch_size=settings.embedding_batch_size,
            timeout_seconds=settings.embedding_timeout_seconds,
        )
    raise ProviderError(f"未知的 EMBEDDING_PROVIDER: {settings.embedding_provider}")


def clear_provider_cache() -> None:
    """清空 provider 缓存，便于测试或配置变更后重建实例。"""
    get_embedding_provider.cache_clear()
    get_llm_provider.cache_clear()


class PlaceholderLLMProvider(LLMProvider):
    """本期不生成任何内容。"""

    name = "placeholder"

    async def generate(self, messages: Sequence[dict[str, str]], **kwargs: object) -> str:
        """占位实现，调用即抛 NotImplementedError。"""
        raise NotImplementedError("对话生成在后续阶段实现，本期仅保留接口")


@lru_cache
def get_llm_provider() -> LLMProvider:
    """按配置返回 LLM provider；未配置密钥时退回占位实现，由业务层降级。"""
    name = settings.llm_provider.strip().lower()
    if name in {"openai", "openai_compat", "openai-compatible"} and settings.llm_api_key:
        return OpenAICompatLLMProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
    return PlaceholderLLMProvider()
