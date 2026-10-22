"""Provider 抽象：本期只要求 Embedding，LLM 仅占位。

业务层只依赖本文件的接口，方便替换为任意 OpenAI 兼容服务。
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence


class EmbeddingProvider(ABC):
    """Embedding 提供方接口：批量把文本转成等长向量。"""

    name: str = "base"
    dimension: int = 1536

    @abstractmethod
    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """批量向量化，返回顺序与输入一致、维度为 dimension 的向量。"""
        raise NotImplementedError

    async def health(self) -> bool:
        """探活接口，默认视为健康，返回布尔值。"""
        return True


class LLMProvider(ABC):
    """对话/生成能力占位。本期不调用。"""

    name: str = "base"

    @abstractmethod
    async def generate(self, messages: Sequence[dict[str, str]], **kwargs: object) -> str:
        """抽象生成方法，接收消息列表并返回生成的文本。"""
        raise NotImplementedError
