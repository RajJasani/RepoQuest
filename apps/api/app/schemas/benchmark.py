from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class BenchmarkCreateRequest(BaseModel):
    models: list[str] = Field(..., min_length=1, description="List of model names to benchmark")
    sample_size: Optional[int] = Field(None, ge=1, le=100, description="Optional sample size cap")


class BenchmarkCreateResponse(BaseModel):
    run_ids: list[str]


class BenchmarkRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model: str
    sample_count: int
    type_accuracy: Optional[float] = None
    severity_accuracy: Optional[float] = None
    json_valid_rate: Optional[float] = None
    avg_latency_ms: Optional[int] = None
    tokens_per_sec: Optional[float] = None
    details: Optional[dict[str, Any]] = None
    status: str
    created_at: Optional[datetime] = None
