from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import get_db
from app.main import create_app
from app.models.core import AuditLog, Repository
from app.models.features import BenchmarkRun, Issue
from app.providers.base import ChatResult, LLMProvider, ModelInfo, Msg
from app.services.benchmark import (
    cancel_benchmark_run,
    run_benchmark_for_model,
)


class FakeBenchmarkProvider(LLMProvider):
    def __init__(self, responses: list[dict], fail_on_call: bool = False):
        self.responses = responses
        self.call_count = 0
        self.fail_on_call = fail_on_call

    async def chat(
        self,
        messages: list[Msg],
        *,
        schema: dict | None = None,
        temperature: float = 0.2,
    ) -> ChatResult:
        if self.fail_on_call:
            raise RuntimeError("Model inference failed unexpectedly")

        resp = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return ChatResult(
            content=json.dumps(resp),
            tokens_in=40,
            tokens_out=25,
            latency_ms=50,
        )

    async def chat_stream(self, messages: list[Msg], *, temperature: float = 0.3):
        yield "token"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    async def list_models(self) -> list[ModelInfo]:
        return []


class MockSessionContext:
    def __init__(self, run_map: dict[uuid.UUID, BenchmarkRun]):
        self.run_map = run_map

    def __call__(self):
        return self

    async def __aenter__(self):
        sess = AsyncMock()

        async def _get(model, rid):
            return self.run_map.get(rid)

        sess.get = AsyncMock(side_effect=_get)

        def _execute(stmt):
            res = MagicMock()
            params = getattr(stmt.compile(), "params", {})
            for rid, r in self.run_map.items():
                if rid in params.values() or str(rid) in params.values() or str(rid) in str(stmt):
                    res.scalar_one_or_none.return_value = r
                    return res
            res.scalar_one_or_none.return_value = None
            return res

        sess.execute = AsyncMock(side_effect=_execute)
        sess.commit = AsyncMock()
        return sess

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_benchmark_accuracy_math_and_metrics():
    """Verify that type accuracy, severity accuracy, json validity and tokens/sec are computed accurately."""
    run_id = uuid.uuid4()
    mock_run = BenchmarkRun(
        id=run_id,
        model="fake-gemma",
        sample_count=2,
        status="running",
        details={},
    )

    # First issue in benchmark_issues.json is expected: bug, P0
    # Second issue is expected: bug, P0
    # Provide: 1st correct (bug, P0), 2nd partial (feature, P0) with all required TriageResult fields
    fake_provider = FakeBenchmarkProvider([
        {
            "type": "bug",
            "severity": "P0",
            "labels": ["bug"],
            "summary": "Fix SQL injection",
            "missing_info": [],
            "duplicates": [],
            "good_first_issue_score": 0,
            "suggested_reply": "Thanks",
            "confidence": 0.95,
        },
        {
            "type": "feature",
            "severity": "P0",
            "labels": [],
            "summary": "Crash fix",
            "missing_info": [],
            "duplicates": [],
            "good_first_issue_score": 0,
            "suggested_reply": "Thanks",
            "confidence": 0.95,
        },
    ])

    ctx = MockSessionContext({run_id: mock_run})
    with patch("app.services.benchmark.get_sessionmaker", return_value=ctx):
        await run_benchmark_for_model(
            run_id=run_id,
            model_name="fake-gemma",
            sample_size=2,
            provider=fake_provider,
        )

    # 1 out of 2 correct types -> 0.5
    # 2 out of 2 correct severities -> 1.0
    # 2 valid json outputs -> 1.0
    assert mock_run.type_accuracy == 0.5
    assert mock_run.severity_accuracy == 1.0
    assert mock_run.json_valid_rate == 1.0
    assert mock_run.status == "done"
    assert mock_run.sample_count == 2
    assert mock_run.avg_latency_ms is not None
    assert mock_run.tokens_per_sec is not None


@pytest.mark.asyncio
async def test_benchmark_cancel_mid_run():
    """Verify that a running benchmark can be cancelled and status updates to cancelled."""
    run_id = uuid.uuid4()
    mock_run = BenchmarkRun(
        id=run_id,
        model="fake-cancel-model",
        sample_count=5,
        status="running",
        details={},
    )

    fake_provider = FakeBenchmarkProvider([
        {
            "type": "bug",
            "severity": "P0",
            "labels": ["bug"],
            "summary": "S1",
            "missing_info": [],
            "duplicates": [],
            "good_first_issue_score": 0,
            "suggested_reply": "R1",
            "confidence": 0.9,
        },
    ])

    cancel_benchmark_run(run_id)

    ctx = MockSessionContext({run_id: mock_run})
    with patch("app.services.benchmark.get_sessionmaker", return_value=ctx):
        await run_benchmark_for_model(
            run_id=run_id,
            model_name="fake-cancel-model",
            sample_size=5,
            provider=fake_provider,
        )

    assert mock_run.status == "cancelled"


@pytest.mark.asyncio
async def test_one_failing_model_does_not_stop_the_rest():
    """Verify that failure in one model marks that run as failed without stopping other model runs."""
    run1_id = uuid.uuid4()
    run2_id = uuid.uuid4()

    run1 = BenchmarkRun(id=run1_id, model="failing-model", sample_count=1, status="running", details={})
    run2 = BenchmarkRun(id=run2_id, model="healthy-model", sample_count=1, status="running", details={})

    failing_provider = FakeBenchmarkProvider([], fail_on_call=True)
    healthy_provider = FakeBenchmarkProvider([
        {
            "type": "bug",
            "severity": "P0",
            "labels": [],
            "summary": "Good",
            "missing_info": [],
            "duplicates": [],
            "good_first_issue_score": 0,
            "suggested_reply": "Thanks",
            "confidence": 0.9,
        },
    ])

    ctx = MockSessionContext({run1_id: run1, run2_id: run2})
    with patch("app.services.benchmark.get_sessionmaker", return_value=ctx):
        await asyncio.gather(
            run_benchmark_for_model(run1_id, "failing-model", sample_size=1, provider=failing_provider),
            run_benchmark_for_model(run2_id, "healthy-model", sample_size=1, provider=healthy_provider),
        )

    assert run1.status == "failed"
    assert "error" in run1.details
    assert run2.status == "done"
    assert run2.type_accuracy == 1.0


@pytest.mark.asyncio
async def test_csv_export_columns_and_route_ordering():
    """Verify CSV export columns match PRD requirements and route is not shadowed by /{id}."""
    app = create_app()

    run_uuid = uuid.uuid4()
    mock_run = BenchmarkRun(
        id=run_uuid,
        model="gemma3:4b",
        sample_count=40,
        type_accuracy=0.875,
        severity_accuracy=0.925,
        json_valid_rate=1.0,
        avg_latency_ms=180,
        tokens_per_sec=42.5,
        status="done",
        created_at=datetime.now(timezone.utc),
    )

    mock_session = AsyncMock()

    def _execute(stmt):
        stmt_str = str(stmt)
        params = getattr(stmt.compile(), "params", {})
        res = MagicMock()
        if "benchmark_runs.created_at DESC" in stmt_str or "ORDER BY benchmark_runs.created_at" in stmt_str:
            res.scalars.return_value.all.return_value = [mock_run]
        elif run_uuid in params.values() or str(run_uuid) in stmt_str:
            res.scalar_one_or_none.return_value = mock_run
        else:
            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.all.return_value = []
        return res

    mock_session.execute = AsyncMock(side_effect=_execute)
    app.dependency_overrides[get_db] = lambda: mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Test CSV export endpoint
        res = await client.get("/api/v1/benchmarks/export.csv")
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        lines = res.text.strip().split("\r\n")
        if len(lines) == 1:
            lines = res.text.strip().split("\n")

        headers = lines[0].split(",")
        expected_cols = [
            "id", "model", "sample_count", "type_accuracy", "severity_accuracy",
            "json_valid_rate", "avg_latency_ms", "tokens_per_sec", "status", "created_at"
        ]
        assert headers == expected_cols
        assert "gemma3:4b" in lines[1]
        assert "0.875" in lines[1]

        # 2. Test route ordering: non-existent UUID returns 404
        res_404 = await client.get("/api/v1/benchmarks/00000000-0000-0000-0000-000000000000")
        assert res_404.status_code == 404

        # 3. Existing UUID returns 200
        res_200 = await client.get(f"/api/v1/benchmarks/{run_uuid}")
        assert res_200.status_code == 200
        assert res_200.json()["model"] == "gemma3:4b"


@pytest.mark.asyncio
async def test_audit_undo_behavior():
    """Verify undo removing applied labels, refusing comments, and handling conflict."""
    app = create_app()

    repo_id = uuid.uuid4()
    mock_repo = Repository(
        id=repo_id,
        owner="demo",
        name="taskboard",
        full_name="demo/taskboard",
        labels=["bug", "good-first-issue"],
    )

    audit_entry = AuditLog(
        id=uuid.uuid4(),
        feature="triage",
        action="approve",
        repo_id=repo_id,
        ref_type="issue",
        ref_id="101",
        undone=False,
        undo_payload={
            "applied_labels": ["good-first-issue"],
            "previous_labels": [],
            "simulated": True,
        },
    )

    comment_audit_entry = AuditLog(
        id=uuid.uuid4(),
        feature="triage",
        action="post_issue_comment",
        repo_id=repo_id,
        ref_type="issue",
        ref_id="101",
        undone=False,
        undo_payload={"comment": "Hello world"},
    )

    mock_issue = Issue(
        id=uuid.uuid4(),
        repo_id=repo_id,
        number=101,
        title="Test issue",
        labels=["good-first-issue"],
        triage_status="applied",
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    async def _mock_get(model, obj_id):
        if model == Repository and obj_id == repo_id:
            return mock_repo
        return None

    mock_session.get = AsyncMock(side_effect=_mock_get)

    def mock_execute(stmt):
        stmt_str = str(stmt)
        params = getattr(stmt.compile(), "params", {})
        param_vals = [str(v) for v in params.values()]
        res = MagicMock()
        if str(audit_entry.id) in param_vals or str(audit_entry.id) in stmt_str:
            res.scalar_one_or_none.return_value = audit_entry
        elif str(comment_audit_entry.id) in param_vals or str(comment_audit_entry.id) in stmt_str:
            res.scalar_one_or_none.return_value = comment_audit_entry
        elif "101" in param_vals or 101 in params.values():
            res.scalar_one_or_none.return_value = mock_issue
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute = AsyncMock(side_effect=mock_execute)
    app.dependency_overrides[get_db] = lambda: mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Successful undo for applied labels
        res = await client.post(f"/api/v1/audit/{audit_entry.id}/undo")
        assert res.status_code == 200
        data = res.json()
        assert data["undone"] is True
        assert "good-first-issue" in data["removed_labels"]
        assert audit_entry.undone is True
        assert mock_issue.labels == []
        assert mock_issue.triage_status == "untriaged"

        # 2. Re-attempting undo returns 409 Conflict
        res_conflict = await client.post(f"/api/v1/audit/{audit_entry.id}/undo")
        assert res_conflict.status_code == 409

        # 3. Refusing comment undo
        res_comment = await client.post(f"/api/v1/audit/{comment_audit_entry.id}/undo")
        assert res_comment.status_code == 400
        err = res_comment.json()
        assert "Comments cannot be un-posted automatically" in err["error"]["message"]


@pytest.mark.asyncio
async def test_model_recommend_endpoint():
    """Verify recommendation logic mapping RAM GB to model sizes."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # < 8 GB
        r1 = await client.get("/api/v1/models/recommend?ram_gb=4")
        assert r1.status_code == 200
        assert r1.json()["recommended_size"] == "1B-2B"

        # 8-16 GB
        r2 = await client.get("/api/v1/models/recommend?ram_gb=12")
        assert r2.status_code == 200
        assert r2.json()["recommended_size"] == "3B-4B"
        assert r2.json()["recommended_model"] == "gemma3:4b"

        # 16-32 GB
        r3 = await client.get("/api/v1/models/recommend?ram_gb=16")
        assert r3.status_code == 200
        assert r3.json()["recommended_size"] == "7B-9B"

        # >= 32 GB
        r4 = await client.get("/api/v1/models/recommend?ram_gb=64")
        assert r4.status_code == 200
        assert r4.json()["recommended_size"] == "14B-32B"


@pytest.mark.asyncio
async def test_create_and_cancel_benchmark_endpoints():
    """Verify POST /benchmarks returns 202 with run_ids and cancel endpoint works."""
    app = create_app()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    run_uuid = uuid.uuid4()
    mock_run = BenchmarkRun(
        id=run_uuid,
        model="llama3.2:3b",
        sample_count=5,
        status="running",
        details={},
        created_at=datetime.now(timezone.utc),
    )

    def _execute(stmt):
        res = MagicMock()
        res.scalar_one_or_none.return_value = mock_run
        return res

    mock_session.execute = AsyncMock(side_effect=_execute)
    app.dependency_overrides[get_db] = lambda: mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with patch("app.routers.benchmark.start_benchmark_task"):
            res = await client.post("/api/v1/benchmarks", json={"models": ["llama3.2:3b"], "sample_size": 5})
            assert res.status_code == 202
            data = res.json()
            assert "run_ids" in data
            assert len(data["run_ids"]) == 1

        # Cancel
        res_cancel = await client.post(f"/api/v1/benchmarks/{run_uuid}/cancel")
        assert res_cancel.status_code == 200
        assert res_cancel.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_audit_list_endpoint():
    """Verify GET /audit returns paginated list of entries."""
    app = create_app()
    mock_session = AsyncMock()

    entry = AuditLog(
        id=uuid.uuid4(),
        feature="chat",
        action="ask_repo",
        undone=False,
        outcome="ok",
        model="gemma3:4b",
        ts=datetime.now(timezone.utc),
    )

    def _execute(stmt):
        stmt_str = str(stmt)
        res = MagicMock()
        if "count" in stmt_str.lower():
            res.scalar_one.return_value = 1
        else:
            res.scalars.return_value.all.return_value = [entry]
        return res

    mock_session.execute = AsyncMock(side_effect=_execute)
    app.dependency_overrides[get_db] = lambda: mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/audit?page=1&page_size=10")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["feature"] == "chat"

