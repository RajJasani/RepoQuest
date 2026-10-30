from collections.abc import AsyncIterator
import time
from typing import Any, Optional

import httpx

from app.core.errors import LLMUnavailableError
from app.providers.base import ChatResult, LLMProvider, ModelInfo, Msg


class OpenAICompatProvider(LLMProvider):
    """Disabled-by-default OpenAI-compatible provider implementation."""

    def __init__(
        self,
        base_url: str = "https://api.openai.com/v1",
        api_key: Optional[str] = None,
        chat_model: str = "gpt-4o-mini",
        embed_model: str = "text-embedding-3-small",
        enabled: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.enabled = enabled

    def _check_enabled(self) -> None:
        if not self.enabled:
            raise LLMUnavailableError(
                message="OpenAI compatible provider is disabled by default",
                details={"provider": "openai_compat", "enabled": False},
            )

    async def chat(
        self,
        messages: list[Msg],
        *,
        schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.2,
    ) -> ChatResult:
        self._check_enabled()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload: dict[str, Any] = {
            "model": self.chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": schema, "strict": True},
            }

        start_time = time.perf_counter()
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, httpx.NetworkError) as exc:
                raise LLMUnavailableError(f"OpenAI chat service error: {exc}") from exc

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens")
        tokens_out = usage.get("completion_tokens")
        model = data.get("model", self.chat_model)

        return ChatResult(
            content=content,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            model=model,
        )

    async def chat_stream(
        self,
        messages: list[Msg],
        *,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        self._check_enabled()
        # Stub async generator when disabled/enabled
        if False:
            yield ""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self._check_enabled()
        if not texts:
            return []
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.embed_model, "input": texts}
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, httpx.NetworkError) as exc:
                raise LLMUnavailableError(f"OpenAI embed service error: {exc}") from exc

        data_items = data.get("data", [])
        return [item.get("embedding", []) for item in data_items]

    async def list_models(self) -> list[ModelInfo]:
        self._check_enabled()
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, httpx.NetworkError) as exc:
                raise LLMUnavailableError(f"OpenAI models service error: {exc}") from exc

        items = data.get("data", [])
        return [ModelInfo(name=item.get("id", "")) for item in items]
