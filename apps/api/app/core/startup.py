import logging
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_sessionmaker
from app.core.security import validate_secret_key
from app.models.core import Profile, Setting
from app.providers.factory import get_provider

logger = logging.getLogger("app.core.startup")

# Global health state for embedding dimension check
_embedding_health: dict[str, Any] = {
    "checked": False,
    "ok": True,
    "dimension": 768,
    "warning": None,
}


def get_embedding_health() -> dict[str, Any]:
    return _embedding_health


async def ensure_seed_data(session: AsyncSession) -> None:
    """Ensures the single settings row (id 1) and one profile row exist."""
    # 1. Check settings row id=1
    stmt = select(Setting).where(Setting.id == 1)
    result = await session.execute(stmt)
    setting_row = result.scalar_one_or_none()
    if setting_row is None:
        logger.info("Initializing default settings row (id=1)...")
        setting_row = Setting(id=1)
        session.add(setting_row)

    # 2. Check profile row
    stmt_prof = select(Profile).limit(1)
    res_prof = await session.execute(stmt_prof)
    profile_row = res_prof.scalar_one_or_none()
    if profile_row is None:
        logger.info("Initializing default profile row...")
        profile_row = Profile(
            display_name="Contributor",
            skills=[],
            level="beginner",
        )
        session.add(profile_row)

    await session.commit()


async def check_embedding_dimension(session: Optional[AsyncSession] = None) -> None:
    """
    Checks that the configured embedding model produces 768-dimensional vectors.
    If not, logs a clear warning and marks health status as warning/degraded.
    """
    global _embedding_health
    try:
        provider = await get_provider(session)
        embeddings = await provider.embed(["dimension check probe"])
        if embeddings and len(embeddings) > 0:
            dim = len(embeddings[0])
            _embedding_health["checked"] = True
            _embedding_health["dimension"] = dim
            if dim != 768:
                warn_msg = (
                    f"Configured embedding model '{provider.embed_model}' returned {dim} dimensions, "
                    f"but 768 dimensions are required by the pgvector database schema. "
                    f"A full re-index will be required."
                )
                logger.warning("STARTUP WARNING: %s", warn_msg)
                _embedding_health["ok"] = False
                _embedding_health["warning"] = warn_msg
            else:
                _embedding_health["ok"] = True
                _embedding_health["warning"] = None
    except Exception as exc:
        logger.warning("Embedding dimension check could not reach Ollama: %s", exc)
        _embedding_health["checked"] = False
        _embedding_health["ok"] = None
        _embedding_health["warning"] = f"Ollama not reachable: {exc}"


async def run_startup() -> None:
    """Orchestrates all startup checks and seed initialization."""
    # 1. Validate APP_SECRET_KEY
    validate_secret_key()

    # 2. Ensure seed rows in DB
    try:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            await ensure_seed_data(session)
            # 3. Check embedding dimension
            await check_embedding_dimension(session)
    except Exception as exc:
        logger.warning("Database unavailable during startup; deferred seed checks: %s", exc)
        # Attempt embedding dimension check without DB
        await check_embedding_dimension(None)
