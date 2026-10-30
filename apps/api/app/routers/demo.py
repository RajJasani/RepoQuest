from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.routers.system import get_provider
from app.services.demo import load_demo_data

logger = logging.getLogger("app.routers.demo")

router = APIRouter(prefix="", tags=["demo"])


@router.post("/demo/load")
async def load_demo_repo(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Loads and indexes the bundled demo repository demo/taskboard 100% offline.
    Loads 25 issues and 20 PRs with embeddings.
    """
    provider = await get_provider(db)
    result = await load_demo_data(session=db, provider=provider)
    return result

