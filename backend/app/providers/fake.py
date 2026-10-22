"""确定性 fake embedding：仅用于开发/测试，不具备语义相似性。

同一文本必然得到同一向量，可用于验证写入、维度与检索链路的连通性。
"""

import hashlib
import math
import re
from collections.abc import Sequence

from app.providers.base import EmbeddingProvider

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+|[\u4e00-\u9fa5]")


class FakeEmbeddingProvider(EmbeddingProvider):
    """基于哈希的确定性 embedding 实现，同一文本恒定得到同一向量。"""

    name = "fake"

    def __init__(self, dimension: int = 1536) -> None:
        """初始化并允许覆盖向量维度，默认 1536。"""
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        """把单条文本按词元哈希累加到固定维度并做 L2 归一化，返回稠密向量。"""
        vector = [0.0] * self.dimension
        tokens = _TOKEN_RE.findall(text.lower()) or [text]
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            vector[0] = 1.0
            return vector
        return [value / norm for value in vector]

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """逐条生成确定性向量，返回顺序与输入一致。"""
        return [self._embed(text) for text in texts]
