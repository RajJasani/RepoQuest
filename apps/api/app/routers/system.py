import asyncio
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db, get_engine
from app.core.startup import get_embedding_health
from app.providers.factory import get_provider

router = APIRouter(tags=["system"])


@router.get("/health")
async def get_health(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    # 1. DB check
    db_status = "ok"
    try:
        engine = get_engine()

        async def _check_db() -> None:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(_check_db(), timeout=2.0)
    except Exception:
        db_status = "down"

    # 2. Ollama check using configured base URL
    ollama_status = "ok"
    try:
        provider = await get_provider(db)

        async def _check_ollama() -> None:
            await provider.list_models()

        await asyncio.wait_for(_check_ollama(), timeout=2.0)
    except Exception:
        ollama_status = "down"

    # 3. Embedding dimension status
    emb_health = get_embedding_health()
    emb_ok = emb_health.get("ok")
    emb_warning = emb_health.get("warning")

    # Overall status
    if db_status == "ok" and ollama_status == "ok" and emb_ok is not False:
        overall_status = "ok"
    else:
        overall_status = "degraded"

    result: dict[str, Any] = {
        "status": overall_status,
        "db": db_status,
        "ollama": ollama_status,
    }

    if emb_ok is not None:
        result["embedding_dimension_ok"] = emb_ok
    if emb_warning:
        result["embedding_dimension_warning"] = emb_warning

    return result


@router.get("/models")
async def get_models(db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    provider = await get_provider(db)
    models = await provider.list_models()
    return [
        {
            "name": m.name,
            "size": m.size,
            "family": m.family,
            "parameter_size": m.parameter_size,
            "modified_at": m.modified_at,
        }
        for m in models
    ]
