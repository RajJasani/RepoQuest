import asyncio
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.core.db import get_engine

router = APIRouter(tags=["system"])


@router.get("/health")
async def get_health() -> dict[str, Any]:
    db_status = "ok"
    try:
        engine = get_engine()

        async def _check_db() -> None:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(_check_db(), timeout=2.0)
    except Exception:
        db_status = "down"

    overall_status = "ok" if db_status == "ok" else "degraded"
    return {
        "status": overall_status,
        "db": db_status,
        "ollama": "unknown",
    }
