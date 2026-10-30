from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest

from app.models.core import Job
from app.worker import process_next_job, recover_stuck_jobs


@pytest.mark.asyncio
async def test_recover_stuck_jobs():
    session = AsyncMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 3
    session.execute.return_value = mock_cursor

    count = await recover_stuck_jobs(session)
    assert count == 3
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_next_job_success():
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        kind="index_repo",
        payload={"repo_id": str(uuid.uuid4())},
        status="queued",
        attempts=0,
        run_after=datetime.now(timezone.utc) - timedelta(seconds=1),
        created_at=datetime.now(timezone.utc),
    )

    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "from jobs" in stmt_str:
            mock_result.scalar_one_or_none.return_value = job
        return mock_result

    session.execute.side_effect = mock_execute
    session.commit.return_value = None

    class MockSessionMaker:
        def __call__(self):
            return self

        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch("app.worker.IndexerService") as mock_indexer_cls:
        mock_indexer = AsyncMock()
        mock_indexer.index_repository.return_value = None
        mock_indexer_cls.return_value = mock_indexer

        processed = await process_next_job(MockSessionMaker())

        assert processed is True
        assert job.status == "done"
        assert job.attempts == 1
        assert job.finished_at is not None
        assert job.error is None
        mock_indexer.index_repository.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_next_job_failure():
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        kind="index_repo",
        payload={"repo_id": str(uuid.uuid4())},
        status="queued",
        attempts=0,
        run_after=datetime.now(timezone.utc) - timedelta(seconds=1),
        created_at=datetime.now(timezone.utc),
    )

    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "from jobs" in stmt_str:
            mock_result.scalar_one_or_none.return_value = job
        return mock_result

    session.execute.side_effect = mock_execute
    session.commit.return_value = None

    class MockSessionMaker:
        def __call__(self):
            return self

        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    with patch("app.worker.IndexerService") as mock_indexer_cls:
        mock_indexer = AsyncMock()
        mock_indexer.index_repository.side_effect = RuntimeError("Indexing crashed")
        mock_indexer_cls.return_value = mock_indexer

        processed = await process_next_job(MockSessionMaker())

        assert processed is True
        assert job.status == "failed"
        assert job.attempts == 1
        assert "Indexing crashed" in job.error
        assert job.finished_at is not None
