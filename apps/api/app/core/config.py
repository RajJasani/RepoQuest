from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://repoquest:repoquest@db:5432/repoquest"
    APP_SECRET_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    CHAT_MODEL: str = "gemma3:4b"
    EMBED_MODEL: str = "nomic-embed-text"
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_WEBHOOK_SECRET: Optional[str] = None
    CORS_ORIGINS: str = "http://localhost:3000"
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
