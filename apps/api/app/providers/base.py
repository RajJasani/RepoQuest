from collections.abc import AsyncIterator
from typing import Any, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class Msg(BaseModel):
    role: str
    content: str


class ChatResult(BaseModel):
    content: str
    tokens_in: Optional[int] = Field(default=None)
    tokens_out: Optional[int] = Field(default=None)
    latency_ms: Optional[int] = Field(default=None)
    model: Optional[str] = Field(default=None)


class ModelInfo(BaseModel):
    name: str
    size: Optional[int] = Field(default=None)
    family: Optional[str] = Field(default=None)
    parameter_size: Optional[str] = Field(default=None)
    modified_at: Optional[str] = Field(default=None)


@runtime_checkable
class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[Msg],
        *,
        schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.2,
    ) -> ChatResult:
        ...

    async def chat_stream(
        self,
        messages: list[Msg],
        *,
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    async def list_models(self) -> list[ModelInfo]:
        ...
