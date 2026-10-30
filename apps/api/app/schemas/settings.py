from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


class SettingsResponse(BaseModel):
    ollama_base_url: str
    chat_model: str
    embed_model: str
    triage_mode: Literal["suggest", "auto"]
    spam_threshold: int = Field(ge=0, le=100)
    language: Literal["en", "hi", "kn", "ta"]
    offline_mode: bool
    has_github_token: bool
    updated_at: datetime


class SettingsUpdateRequest(BaseModel):
    ollama_base_url: Optional[str] = None
    chat_model: Optional[str] = None
    embed_model: Optional[str] = None
    triage_mode: Optional[Literal["suggest", "auto"]] = None
    spam_threshold: Optional[int] = Field(default=None, ge=0, le=100)
    language: Optional[Literal["en", "hi", "kn", "ta"]] = None
    offline_mode: Optional[bool] = None

    @field_validator("ollama_base_url")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            if not (v_clean.startswith("http://") or v_clean.startswith("https://")):
                raise ValueError("ollama_base_url must start with http:// or https://")
            return v_clean
        return v

    @field_validator("chat_model", "embed_model")
    @classmethod
    def validate_model_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_clean = v.strip()
            if not v_clean:
                raise ValueError("Model name cannot be empty")
            return v_clean
        return v
