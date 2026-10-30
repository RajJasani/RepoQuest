from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator


class ChatSessionCreateRequest(BaseModel):
    mode: str = "newcomer"
    language: str = "en"

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in ("newcomer", "expert"):
            raise ValueError("mode must be 'newcomer' or 'expert'")
        return v_clean

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean not in ("en", "hi", "kn", "ta"):
            raise ValueError("language must be one of: en, hi, kn, ta")
        return v_clean


class ChatMessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content must not be empty or whitespace only")
        return v


class CitationItem(BaseModel):
    file: str
    start_line: int
    end_line: int


class ChatMessageResponse(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ChatSessionResponse(BaseModel):
    id: str
    repo_id: str
    mode: str
    language: str
    created_at: datetime


class ChatSessionDetailResponse(ChatSessionResponse):
    messages: list[ChatMessageResponse] = Field(default_factory=list)
