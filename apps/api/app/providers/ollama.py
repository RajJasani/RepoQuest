from collections.abc import AsyncIterator
import json
import time
from typing import Any, Optional

import httpx

from app.core.config import get_settings
from app.core.errors import LLMUnavailableError
from app.providers.base import ChatResult, LLMProvider, ModelInfo, Msg


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        base_url: Optional[str] = None,
        chat_model: Optional[str] = None,
        embed_model: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.chat_model = chat_model or settings.CHAT_MODEL
        self.embed_model = embed_model or settings.EMBED_MODEL
        self._external_client = client

    def _get_client(self, timeout: httpx.Timeout) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        return httpx.AsyncClient(timeout=timeout)

    async def chat(
        self,
        messages: list[Msg],
        *,
        schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.2,
    ) -> ChatResult:
        timeout = httpx.Timeout(timeout=120.0, connect=10.0, read=120.0)
        payload: dict[str, Any] = {
            "model": self.chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 8192,
            },
        }
        if schema is not None:
            payload["format"] = schema

        start_time = time.perf_counter()
        try:
            if self._external_client is not None:
                response = await self._external_client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                    )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, httpx.NetworkError, httpx.TimeoutException) as exc:
            raise LLMUnavailableError(
                message=f"Ollama chat service unavailable: {exc}",
                details={"base_url": self.base_url, "model": self.chat_model},
            ) from exc

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        message = data.get("message", {})
        content = message.get("content", "")
        tokens_in = data.get("prompt_eval_count")
        tokens_out = data.get("eval_count")
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
        timeout = httpx.Timeout(timeout=120.0, connect=10.0, read=120.0)
        payload: dict[str, Any] = {
            "model": self.chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": 8192,
            },
        }

        try:
            client = self._external_client or httpx.AsyncClient(timeout=timeout)
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=timeout,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        chunk_data = json.loads(line)
                        msg_chunk = chunk_data.get("message", {}).get("content", "")
                        if msg_chunk:
                            yield msg_chunk
            finally:
                if self._external_client is None:
                    await client.aclose()
        except (httpx.HTTPError, httpx.NetworkError, httpx.TimeoutException) as exc:
            raise LLMUnavailableError(
                message=f"Ollama stream service unavailable: {exc}",
                details={"base_url": self.base_url, "model": self.chat_model},
            ) from exc

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        timeout = httpx.Timeout(timeout=30.0, connect=10.0, read=30.0)
        batch_size = 32
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "model": self.embed_model,
                "input": batch,
            }
            try:
                if self._external_client is not None:
                    response = await self._external_client.post(
                        f"{self.base_url}/api/embed",
                        json=payload,
                        timeout=timeout,
                    )
                else:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(
                            f"{self.base_url}/api/embed",
                            json=payload,
                        )
                response.raise_for_status()
                data = response.json()
            except (httpx.HTTPError, httpx.NetworkError, httpx.TimeoutException) as exc:
                raise LLMUnavailableError(
                    message=f"Ollama embedding service unavailable: {exc}",
                    details={"base_url": self.base_url, "model": self.embed_model},
                ) from exc

            embeddings = data.get("embeddings", [])
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def list_models(self) -> list[ModelInfo]:
        timeout = httpx.Timeout(timeout=30.0, connect=10.0, read=30.0)
        try:
            if self._external_client is not None:
                response = await self._external_client.get(
                    f"{self.base_url}/api/tags",
                    timeout=timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/api/tags",
                    )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, httpx.NetworkError, httpx.TimeoutException) as exc:
            raise LLMUnavailableError(
                message=f"Ollama tags service unavailable: {exc}",
                details={"base_url": self.base_url},
            ) from exc

        raw_models = data.get("models", [])
        result: list[ModelInfo] = []
        for m in raw_models:
            details = m.get("details", {})
            result.append(
                ModelInfo(
                    name=m.get("name", ""),
                    size=m.get("size"),
                    family=details.get("family"),
                    parameter_size=details.get("parameter_size"),
                    modified_at=m.get("modified_at"),
                )
            )
        return result
