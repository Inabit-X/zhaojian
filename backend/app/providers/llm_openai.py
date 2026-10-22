"""OpenAI 兼容 Chat Completions provider。"""

from collections.abc import Sequence
from typing import Any

import httpx

from app.core.exceptions import ProviderError
from app.providers.base import LLMProvider


class OpenAICompatLLMProvider(LLMProvider):
    """调用 {base_url}/chat/completions 的最小实现，兼容校内代理。"""

    name = "openai_compat"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60.0,
    ) -> None:
        """保存端点、密钥与模型名；不发起网络请求。"""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate(
        self, messages: Sequence[dict[str, str]], **kwargs: Any
    ) -> str:
        """调用 Chat Completions 并返回首条文本；失败统一转为 ProviderError。"""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": list(messages),
            "temperature": kwargs.get("temperature", 0.2),
        }
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise ProviderError("LLM 服务连接失败") from exc

        if response.status_code >= 400:
            raise ProviderError(
                f"LLM 服务返回 {response.status_code}",
                details={"status": response.status_code},
            )

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise ProviderError("LLM 响应格式不符合预期") from exc

        if not isinstance(content, str) or not content.strip():
            raise ProviderError("LLM 返回空内容")
        return content
