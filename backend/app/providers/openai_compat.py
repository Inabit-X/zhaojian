"""OpenAI 兼容 /embeddings 客户端（OpenAI、vLLM、Ollama 兼容网关等）。"""

from collections.abc import Sequence

import httpx

from app.core.exceptions import ProviderError
from app.providers.base import EmbeddingProvider


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """通过 OpenAI 兼容 /embeddings 接口调用远程 embedding 服务。"""

    name = "openai"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        dimension: int = 1536,
        batch_size: int = 64,
        timeout_seconds: float = 30.0,
    ) -> None:
        """保存服务地址、密钥、模型、维度、批大小与超时配置。"""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds

    async def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """分批调用 /embeddings 并按 index 排序还原顺序；HTTP、数量或维度异常抛 ProviderError。"""
        if not texts:
            return []
        vectors: list[list[float]] = []
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            for start in range(0, len(texts), self.batch_size):
                batch = list(texts[start : start + self.batch_size])
                try:
                    response = await client.post(
                        f"{self.base_url}/embeddings",
                        json={"model": self.model, "input": batch},
                        headers=headers,
                    )
                    response.raise_for_status()
                    payload = response.json()
                except (httpx.HTTPError, ValueError) as exc:
                    raise ProviderError("Embedding 服务调用失败") from exc

                data = sorted(payload.get("data", []), key=lambda item: item.get("index", 0))
                if len(data) != len(batch):
                    raise ProviderError("Embedding 服务返回数量与请求不一致")
                for item in data:
                    vector = item.get("embedding")
                    if not isinstance(vector, list) or len(vector) != self.dimension:
                        raise ProviderError(
                            f"Embedding 维度不匹配，期望 {self.dimension}"
                        )
                    vectors.append([float(value) for value in vector])
        return vectors

    async def health(self) -> bool:
        """用一条探活文本调用接口，成功返回 True，失败返回 False。"""
        try:
            await self.embed_texts(["ping"])
        except ProviderError:
            return False
        return True
