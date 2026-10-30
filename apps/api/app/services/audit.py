from __future__ import annotations

import logging
from typing import Any, Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import AuditLog

logger = logging.getLogger("app.services.audit")


async def record_audit(
    session: AsyncSession,
    feature: str,
    action: str,
    repo_id: Optional[uuid.UUID] = None,
    ref_type: Optional[str] = None,
    ref_id: Optional[str] = None,
    model: Optional[str] = None,
    prompt_version: Optional[str] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    latency_ms: Optional[int] = None,
    outcome: str = "ok",
    undo_payload: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """
    Persists an audit log entry for actions performed by users or AI agents.
    Tracks feature, repository, target reference, action, telemetry, and undo payloads.
    """
    entry = AuditLog(
        id=uuid.uuid4(),
        feature=feature,
        action=action,
        repo_id=repo_id,
        ref_type=ref_type,
        ref_id=str(ref_id) if ref_id is not None else None,
        model=model,
        prompt_version=prompt_version,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        outcome=outcome,
        undo_payload=undo_payload,
        undone=False,
    )
    session.add(entry)
    try:
        await session.flush()
    except Exception as exc:
        logger.warning("Failed to flush audit log entry: %s", exc)

    return entry

