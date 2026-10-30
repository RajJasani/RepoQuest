from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Optional
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db import get_sessionmaker
from app.models.core import Job, Repository, Setting
from app.models.features import Issue
from app.providers.factory import get_provider
from app.services.indexer import IndexerService
from app.services.triage import triage_issue

logger = logging.getLogger("app.worker")

_worker_task: Optional[asyncio.Task[None]] = None
_should_run: bool = True


async def recover_stuck_jobs(session: AsyncSession) -> int:
    """
    Finds jobs stuck in 'running' for more than 10 minutes and resets them to 'queued'.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    stmt = (
        update(Job)
        .where(
            Job.status == "running",
            (Job.started_at <= cutoff) | (Job.started_at.is_(None)),
        )
        .values(status="queued")
    )
    res = await session.execute(stmt)
    await session.commit()
    return int(res.rowcount or 0)


async def process_next_job(sessionmaker: async_sessionmaker[AsyncSession]) -> bool:
    """
    Fetches and processes the next queued job using SELECT ... FOR UPDATE SKIP LOCKED.
    Returns True if a job was found and processed, False if queue was empty.
    """
    now = datetime.now(timezone.utc)
    job_id: Optional[uuid.UUID] = None
    job_kind: Optional[str] = None
    job_payload: dict[str, Any] = {}

    async with sessionmaker() as session:
        try:
            stmt = (
                select(Job)
                .where(Job.status == "queued", Job.run_after <= now)
                .order_by(Job.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if job is None:
                return False

            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.attempts += 1
            job_id = job.id
            job_kind = job.kind
            job_payload = dict(job.payload) if job.payload else {}
            await session.commit()
        except Exception as exc:
            # Handles engines without FOR UPDATE support or transient errors
            logger.debug("Failed to acquire job lock: %s", exc)
            return False

    # Execute job outside the lock
    job_error: Optional[str] = None
    try:
        if job_kind == "index_repo":
            repo_id = job_payload.get("repo_id")
            token_enc = job_payload.get("token_enc")
            indexer = IndexerService(sessionmaker=sessionmaker)
            await indexer.index_repository(repo_id=str(repo_id), token_enc=token_enc)
        elif job_kind == "triage_issue":
            issue_id_str = job_payload.get("issue_id")
            async with sessionmaker() as session:
                stmt_iss = select(Issue).where(Issue.id == uuid.UUID(issue_id_str))
                res_iss = await session.execute(stmt_iss)
                issue_obj = res_iss.scalar_one_or_none()
                if issue_obj:
                    stmt_repo = select(Repository).where(Repository.id == issue_obj.repo_id)
                    res_repo = await session.execute(stmt_repo)
                    repo_obj = res_repo.scalar_one_or_none()

                    stmt_set = select(Setting).where(Setting.id == 1)
                    res_set = await session.execute(stmt_set)
                    set_obj = res_set.scalar_one_or_none()

                    provider = await get_provider(session)
                    await triage_issue(
                        session=session,
                        issue=issue_obj,
                        repo=repo_obj,
                        provider=provider,
                        settings_row=set_obj,
                    )
        else:
            logger.warning("Unrecognized job kind '%s' for job %s", job_kind, job_id)
            job_error = f"Unrecognized job kind: {job_kind}"
    except Exception as exc:
        logger.exception("Error executing job %s (%s): %s", job_id, job_kind, exc)
        job_error = str(exc)

    # Record completion
    async with sessionmaker() as session:
        stmt = select(Job).where(Job.id == job_id)
        res = await session.execute(stmt)
        job = res.scalar_one_or_none()
        if job:
            job.finished_at = datetime.now(timezone.utc)
            if job_error:
                job.status = "failed"
                job.error = job_error
            else:
                job.status = "done"
            await session.commit()

    return True


async def run_worker_loop(
    poll_interval: float = 1.0,
    sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None,
) -> None:
    """Continuous polling loop for jobs."""
    sm = sessionmaker or get_sessionmaker()
    logger.info("Worker loop started with poll_interval=%.1fs", poll_interval)
    while _should_run:
        try:
            processed = await process_next_job(sm)
            if not processed:
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            logger.info("Worker loop cancelled, shutting down")
            break
        except Exception as exc:
            logger.error("Unexpected error in worker loop: %s", exc)
            await asyncio.sleep(poll_interval)


async def start_worker(
    sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None,
) -> None:
    """Starts the background worker and recovers stuck jobs."""
    global _worker_task, _should_run
    _should_run = True
    sm = sessionmaker or get_sessionmaker()

    # Recover stuck jobs
    try:
        async with sm() as session:
            recovered = await recover_stuck_jobs(session)
            if recovered > 0:
                logger.info("Recovered %d stuck jobs back to 'queued'", recovered)
    except Exception as exc:
        logger.warning("Could not recover stuck jobs at startup (DB might be down): %s", exc)

    # Start worker loop task
    _worker_task = asyncio.create_task(run_worker_loop(sessionmaker=sm))


async def stop_worker() -> None:
    """Gracefully stops the worker background task."""
    global _worker_task, _should_run
    _should_run = False
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
    logger.info("Worker stopped")
