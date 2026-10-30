from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
import respx

from app.core.db import get_db
from app.main import create_app
from app.models.core import Repository, Setting
from app.models.features import Issue, IssueAnalysis


@pytest.fixture
def mock_repo():
    return Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        default_branch="main",
        labels=["bug", "enhancement"],
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_issue(mock_repo):
    return Issue(
        id=uuid.uuid4(),
        repo_id=mock_repo.id,
        number=42,
        title="Sample Bug",
        body="App crashes on click",
        state="open",
        author="alice",
        html_url="https://github.com/octocat/Hello-World/issues/42",
        labels=["bug"],
        triage_status="suggested",
        created_at_gh=datetime.now(timezone.utc),
        updated_at_gh=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_analysis(mock_issue):
    return IssueAnalysis(
        id=uuid.uuid4(),
        issue_id=mock_issue.id,
        type="bug",
        severity="P1",
        labels=["bug"],
        summary="Crash issue",
        missing_info=["logs"],
        duplicates=[],
        good_first_issue_score=10,
        suggested_reply="Thanks for reporting!",
        confidence=0.9,
        model="gemma3:4b",
        prompt_version="v1",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def app_with_db(mock_repo, mock_issue, mock_analysis):
    app = create_app()
    session = AsyncMock()

    settings_row = Setting(id=1, github_token_enc=None)

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "from settings" in stmt_str:
            mock_result.scalar_one_or_none.return_value = settings_row
        elif "count" in stmt_str:
            mock_result.scalar.return_value = 1
        elif "from repositories" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_repo
        elif "from issues" in stmt_str:
            if "order by" in stmt_str and "limit" in stmt_str:
                mock_result.scalars.return_value.all.return_value = [mock_issue]
            else:
                mock_result.scalar_one_or_none.return_value = mock_issue
        elif "from issue_analyses" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_analysis
        else:
            mock_result.scalar_one_or_none.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    session.execute.side_effect = mock_execute
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return app, session, mock_repo, mock_issue, mock_analysis


@pytest.mark.asyncio
async def test_list_repo_issues_pagination_validation(app_with_db):
    app, _, mock_repo, _, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # page < 1 must be 422
        resp = await client.get(f"/api/v1/repos/{mock_repo.id}/issues?page=0")
        assert resp.status_code == 422

        # page_size > 100 must be 422
        resp = await client.get(f"/api/v1/repos/{mock_repo.id}/issues?page_size=101")
        assert resp.status_code == 422

        # page_size < 1 must be 422
        resp = await client.get(f"/api/v1/repos/{mock_repo.id}/issues?page_size=0")
        assert resp.status_code == 422

        # Valid pagination
        resp = await client.get(f"/api/v1/repos/{mock_repo.id}/issues?page=1&page_size=20")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["number"] == 42
        assert data["items"][0]["analysis"]["type"] == "bug"


@pytest.mark.asyncio
async def test_get_issue_detail_and_404(app_with_db):
    app, session, _, mock_issue, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Success
        resp = await client.get(f"/api/v1/issues/{mock_issue.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(mock_issue.id)
        assert data["title"] == mock_issue.title
        assert data["analysis"]["type"] == "bug"

        # 404 for unknown issue
        async def mock_execute_not_found(stmt):
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_result.scalars.return_value.all.return_value = []
            return mock_result

        session.execute.side_effect = mock_execute_not_found

        resp = await client.get(f"/api/v1/issues/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_enqueue_triage_job(app_with_db):
    app, session, _, mock_issue, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(f"/api/v1/issues/{mock_issue.id}/triage")
        assert resp.status_code == 202
        data = resp.json()
        assert data["issue_id"] == str(mock_issue.id)
        assert "job_id" in data


@pytest.mark.asyncio
async def test_approve_issue_endpoint(app_with_db):
    app, _, mock_repo, mock_issue, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "labels": ["bug"],
            "comment": "Looks good!",
            "post_to_github": False,
        }
        resp = await client.post(f"/api/v1/issues/{mock_issue.id}/approve", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["issue_id"] == str(mock_issue.id)
        assert data["status"] == "approved"
        assert data["posted_to_github"] is False
        assert data["labels"] == ["bug"]


@pytest.mark.asyncio
async def test_reject_issue_endpoint(app_with_db):
    app, _, _, mock_issue, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(f"/api/v1/issues/{mock_issue.id}/reject")
        assert resp.status_code == 200
        data = resp.json()
        assert data["issue_id"] == str(mock_issue.id)
        assert data["status"] == "rejected"


@pytest.mark.asyncio
@respx.mock
async def test_sync_repo_issues(app_with_db):
    app, session, mock_repo, _, _ = app_with_db

    # Mock GitHub endpoints
    respx.get("https://api.github.com/repos/octocat/Hello-World/labels").respond(
        status_code=200,
        json=[{"name": "bug"}, {"name": "enhancement"}],
    )
    respx.get("https://api.github.com/repos/octocat/Hello-World/issues?state=open&per_page=100").respond(
        status_code=200,
        json=[
            {
                "number": 101,
                "title": "Synced issue title",
                "body": "Synced issue body",
                "state": "open",
                "html_url": "https://github.com/octocat/Hello-World/issues/101",
                "created_at": "2026-10-30T10:00:00Z",
                "updated_at": "2026-10-30T10:00:00Z",
                "user": {"login": "syncuser"},
                "labels": [{"name": "bug"}],
            }
        ],
    )

    mock_provider = AsyncMock()
    mock_provider.embed.return_value = [[0.1, 0.2, 0.3]]

    with patch("app.routers.issues.get_provider", return_value=mock_provider):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(f"/api/v1/repos/{mock_repo.id}/issues/sync")
            assert resp.status_code == 200
            data = resp.json()
            assert data["synced_issues"] == 1
            assert data["labels_count"] == 2
