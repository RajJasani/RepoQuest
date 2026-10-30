from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict


class AuditItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    ts: datetime
    feature: str
    repo_id: Optional[uuid.UUID] = None
    ref_type: Optional[str] = None
    ref_id: Optional[str] = None
    action: str
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: Optional[int] = None
    outcome: str
    undo_payload: Optional[dict[str, Any]] = None
    undone: bool


class AuditListResponse(BaseModel):
    items: list[AuditItemResponse]
    total: int
    page: int
    page_size: int
    pages: int


class AuditUndoResponse(BaseModel):
    status: str
    message: str
    removed_labels: list[str]
    undone: bool
