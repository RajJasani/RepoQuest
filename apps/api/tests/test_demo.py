from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
import respx

from app.core.db import get_db
from app.main import create_app
from app.models.core import Repository, Setting
from app.models.features import Issue
from app.providers.base import ChatResult, Msg
from app.services.demo import load_demo_data
from app.services.diffparse import parse_unified_diff
from app.services.github import GitHubClient
from app.services.triage import approve_issue

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class FakeDemoProvider:
    def __init__(self):
        self.chat_model = "gemma3:4b"

    async def chat(self, messages: list[Msg], **kwargs) -> ChatResult:
        return ChatResult(content="{}")

    async def chat_stream(self, messages: list[Msg], **kwargs):
        yield "{}"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    async def list_models(self):
        return []


def test_demo_issues_counts_and_composition():
    path = DATA_DIR / "demo_issues.json"
    assert path.exists()

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    allowed_labels = set(data["labels"])
    issues = data["issues"]

    # Exactly 25 issues
    assert len(issues) == 25

    # Every label used exists in allowed labels
    for iss in issues:
        for lbl in iss["labels"]:
            assert lbl in allowed_labels, f"Label {lbl} is not in allowed labels list"

    # 4 clear good-first-issue candidates
    gfi_issues = [i for i in issues if "good-first-issue" in i["labels"]]
    assert len(gfi_issues) == 4

    # 5 near-duplicate issues (duplicates in labels or titles/bodies)
    duplicate_issues = [i for i in issues if "duplicate" in i["labels"] or i["number"] in (1, 2, 3, 4, 5)]
    assert len(duplicate_issues) >= 5

    # 1 spam issue
    spam_issues = [i for i in issues if "crypto" in i["title"].lower() or "free" in i["title"].lower()]
    assert len(spam_issues) >= 1


def test_demo_prs_counts_and_diffs():
    path = DATA_DIR / "demo_prs.json"
    assert path.exists()

    with open(path, encoding="utf-8") as f:
        prs = json.load(f)

    # Exactly 20 PRs
    assert len(prs) == 20

    # 10 genuine (1-10) and 10 spam-like (11-20)
    genuine = [p for p in prs if p["number"] <= 10]
    spam = [p for p in prs if p["number"] > 10]
    assert len(genuine) == 10
    assert len(spam) == 10

    # Every single PR diff parses cleanly with parse_unified_diff
    for pr in prs:
        num = pr["number"]
        diff_text = pr["diff"]
        parsed = parse_unified_diff(diff_text)
        assert len(parsed) >= 1, f"Failed parsing diff for PR #{num}"
        assert parsed[0].path, f"PR #{num} diff has empty path"


def test_benchmark_issues_counts_and_types():
    path = DATA_DIR / "benchmark_issues.json"
    assert path.exists()

    with open(path, encoding="utf-8") as f:
        benchmark = json.load(f)

    # Exactly 40 benchmark issues
    assert len(benchmark) == 40

    valid_types = {"bug", "feature", "question", "docs", "chore", "spam"}
    valid_severities = {"P0", "P1", "P2", "P3"}

    for item in benchmark:
        assert item["expected_type"] in valid_types
        assert item["expected_severity"] in valid_severities


@pytest.mark.asyncio
@respx.mock
async def test_demo_loader_offline_with_fake_provider():
    """Confirms loader works with a fake provider and makes zero network calls."""
    session = AsyncMock()

    # Track added objects
    added_objects = []
    session.add = MagicMock(side_effect=lambda o: added_objects.append(o))
    session.add_all = MagicMock(side_effect=lambda objs: added_objects.extend(objs))

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_res.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_res)
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    provider = FakeDemoProvider()

    summary = await load_demo_data(session=session, provider=provider)

    assert summary["full_name"] == "demo/taskboard"
    assert summary["status"] == "ready"
    assert summary["issues_count"] == 25
    assert summary["prs_count"] == 20
    assert summary["files_count"] >= 28
    assert summary["duration_seconds"] < 20.0

    # Ensure ZERO network requests were attempted
    assert len(respx.calls) == 0


@pytest.mark.asyncio
async def test_simulated_github_writes_and_approve():
    """Validates simulated GitHub writes for demo repository."""
    gh = GitHubClient(token=None)

    # 1. Direct GitHub client simulated writes
    comment_res = await gh.post_issue_comment("demo", "taskboard", 1, "Simulated reply")
    assert comment_res["simulated"] is True
    assert comment_res["status"] == "Applied (demo)"
    assert comment_res["request"]["method"] == "POST"

    label_res = await gh.add_labels("demo", "taskboard", 1, ["bug", "ui"])
    assert len(label_res) == 2
    assert label_res[0]["simulated"] is True
    assert label_res[0]["status"] == "Applied (demo)"

    review_res = await gh.create_pull_request_review("demo", "taskboard", 1, "Review body", "APPROVE")
    assert review_res["simulated"] is True
    assert review_res["status"] == "Applied (demo)"

    # 2. Simulated approve flow in triage service
    repo = Repository(
        id=uuid.uuid4(),
        owner="demo",
        name="taskboard",
        full_name="demo/taskboard",
        labels=["bug", "ui"],
    )
    issue = Issue(
        id=uuid.uuid4(),
        repo_id=repo.id,
        number=1,
        title="Test demo issue",
        body="Issue description",
        labels=[],
        state="open",
        triage_status="suggested",
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    approve_result = await approve_issue(
        session=session,
        issue=issue,
        repo=repo,
        settings_row=Setting(id=1),
        labels=["bug"],
        comment="LGTM in demo",
        post_to_github=True,
    )

    assert approve_result["status"] == "Applied (demo)"
    assert approve_result["posted_to_github"] is True
    assert approve_result["simulated"] is True


@pytest.mark.asyncio
@respx.mock
async def test_demo_load_endpoint():
    app = create_app()
    session = AsyncMock()

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_res.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_res)
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    provider = FakeDemoProvider()

    with patch("app.routers.demo.get_provider", return_value=provider):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post("/api/v1/demo/load")
            assert resp.status_code == 200
            data = resp.json()
            assert data["full_name"] == "demo/taskboard"
            assert data["issues_count"] == 25
            assert data["prs_count"] == 20
            assert data["duration_seconds"] < 20.0
