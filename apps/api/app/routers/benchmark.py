from __future__ import annotations

import csv
import io
import logging
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.features import BenchmarkRun
from app.schemas.benchmark import (
    BenchmarkCreateRequest,
    BenchmarkCreateResponse,
    BenchmarkRunResponse,
)
from app.services.benchmark import (
    cancel_benchmark_run,
    load_benchmark_issues,
    start_benchmark_task,
)

logger = logging.getLogger("app.routers.benchmark")

router = APIRouter(prefix="/benchmarks", tags=["benchmark"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=BenchmarkCreateResponse)
async def create_benchmarks(
    payload: BenchmarkCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkCreateResponse:
    """Enqueues benchmark runs for each specified model."""
    all_issues = load_benchmark_issues()
    total_available = len(all_issues)
    sample_count = min(payload.sample_size, total_available) if payload.sample_size else total_available

    run_ids: list[str] = []
    runs_to_start: list[tuple[uuid.UUID, str]] = []

    for model_name in payload.models:
        clean_model = model_name.strip()
        if not clean_model:
            continue
        run_id = uuid.uuid4()
        run_record = BenchmarkRun(
            id=run_id,
            model=clean_model,
            sample_count=sample_count,
            status="running",
            details={
                "completed": 0,
                "total": sample_count,
                "type_correct": 0,
                "severity_correct": 0,
                "json_valid_count": 0,
                "running_type_accuracy": 0.0,
                "running_severity_accuracy": 0.0,
            },
        )
        db.add(run_record)
        run_ids.append(str(run_id))
        runs_to_start.append((run_id, clean_model))

    await db.commit()

    # Start background execution for each model independently
    for r_id, m_name in runs_to_start:
        start_benchmark_task(
            run_id=r_id,
            model_name=m_name,
            sample_size=payload.sample_size,
        )

    return BenchmarkCreateResponse(run_ids=run_ids)


@router.get("/export.csv")
async def export_benchmarks_csv(db: AsyncSession = Depends(get_db)) -> Response:
    """Exports all benchmark runs as CSV format. Declared before /{id} route to avoid shadowing."""
    stmt = select(BenchmarkRun).order_by(BenchmarkRun.created_at.desc())
    res = await db.execute(stmt)
    runs = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "model",
        "sample_count",
        "type_accuracy",
        "severity_accuracy",
        "json_valid_rate",
        "avg_latency_ms",
        "tokens_per_sec",
        "status",
        "created_at",
    ])

    for r in runs:
        writer.writerow([
            str(r.id),
            r.model,
            r.sample_count,
            r.type_accuracy if r.type_accuracy is not None else "",
            r.severity_accuracy if r.severity_accuracy is not None else "",
            r.json_valid_rate if r.json_valid_rate is not None else "",
            r.avg_latency_ms if r.avg_latency_ms is not None else "",
            r.tokens_per_sec if r.tokens_per_sec is not None else "",
            r.status,
            r.created_at.isoformat() if r.created_at else "",
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="benchmarks.csv"',
        },
    )


@router.get("", response_model=list[BenchmarkRunResponse])
async def list_benchmarks(
    model: Optional[str] = Query(None, description="Filter by model name"),
    db: AsyncSession = Depends(get_db),
) -> list[BenchmarkRunResponse]:
    """Returns a list of all benchmark runs ordered by creation timestamp."""
    stmt = select(BenchmarkRun).order_by(BenchmarkRun.created_at.desc())
    if model:
        stmt = stmt.where(BenchmarkRun.model == model.strip())
    res = await db.execute(stmt)
    runs = res.scalars().all()
    return [BenchmarkRunResponse.model_validate(r) for r in runs]


@router.get("/{id}", response_model=BenchmarkRunResponse)
async def get_benchmark(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkRunResponse:
    """Returns details and live progress for a single benchmark run."""
    try:
        run_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(message=f"Invalid benchmark ID '{id}'")

    stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_uuid)
    res = await db.execute(stmt)
    run_record = res.scalar_one_or_none()
    if not run_record:
        raise NotFoundError(message=f"Benchmark run '{id}' not found")

    return BenchmarkRunResponse.model_validate(run_record)


@router.post("/{id}/cancel", response_model=BenchmarkRunResponse)
async def cancel_benchmark(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> BenchmarkRunResponse:
    """Cancels a running benchmark."""
    try:
        run_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(message=f"Invalid benchmark ID '{id}'")

    stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_uuid)
    res = await db.execute(stmt)
    run_record = res.scalar_one_or_none()
    if not run_record:
        raise NotFoundError(message=f"Benchmark run '{id}' not found")

    cancel_benchmark_run(run_uuid)
    run_record.status = "cancelled"
    await db.commit()
    await db.refresh(run_record)

    return BenchmarkRunResponse.model_validate(run_record)
