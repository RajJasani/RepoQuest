from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.core import Setting
from app.providers.ollama import OllamaProvider


def create_provider_from_settings(settings_row: Setting) -> OllamaProvider:
    """Builds an OllamaProvider configured from a database Setting model row."""
    return OllamaProvider(
        base_url=settings_row.ollama_base_url,
        chat_model=settings_row.chat_model,
        embed_model=settings_row.embed_model,
    )


async def get_provider(db: Optional[AsyncSession] = None) -> OllamaProvider:
    """
    Builds an OllamaProvider using settings from the database (row id=1),
    falling back to application config if database is unavailable.
    """
    if db is not None:
        try:
            stmt = select(Setting).where(Setting.id == 1)
            result = await db.execute(stmt)
            settings_row = result.scalar_one_or_none()
            if settings_row is not None:
                return create_provider_from_settings(settings_row)
        except Exception:
            pass

    app_settings = get_settings()
    return OllamaProvider(
        base_url=app_settings.OLLAMA_BASE_URL,
        chat_model=app_settings.CHAT_MODEL,
        embed_model=app_settings.EMBED_MODEL,
    )
