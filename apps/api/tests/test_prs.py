from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
import respx

from app.core.db import get_db
from app.core.security import encrypt_token
from app.main import create_app
from app.models.core import Repository, Setting
from app.models.features import PRReview, PullRequest, SpamAssessment
from app.providers.base import ChatResult, Msg
from app.services.diffparse import ParsedFileDiff, parse_unified_diff
from app.services.review import (
    execute_pr_review,
    validate_file_comments,
)
from app.schemas.llm import FileComment


class FakeReviewProvider:
    def __init__(self, file_comments: list[dict[str, Any]] = None, fail: bool = False):
        self.file_comments = file_comments or [
            {
                "file": "src/main.py",
                "line_start": 12,
                "line_end": 12,
                "severity": "suggestion",
                "comment": "Consider refactoring this print statement.",
                "suggestion": "print('optimized')",
            }
        ]
        self.fail = fail
        self.chat_model = "gemma3:4b"

    async def chat(
        self,
        messages: list[Msg],
        *,
        schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> ChatResult:
        if self.fail:
            return ChatResult(content="not valid json")

        # Determine if prompt is for file review or merge
        user_msg = messages[-1].content
        if "pr_review_merge" in user_msg or "combine file results" in user_msg or "Synthesizing" in user_msg or "Changed files reviewed" in user_msg:
            merge_data = {
                "summary": ["Add new logging feature.", "Refactor entrypoint."],
                "risk_level": "low",
                "risk_reasons": ["Well-tested changes."],
                "checks": {
                    "tests_updated": True,
                    "docs_updated": False,
                    "follows_contributing": True,
                    "good_description": True,
                    "breaking_change": False,
                    "possible_secret": False,
                },
                "newcomer_explainer": "This pull request adds improved logging when starting the app.",
                "verdict": "approve_ready",
            }
            return ChatResult(content=json.dumps(merge_data))
        else:
            file_data = {
                "file_comments": self.file_comments,
            }
            return ChatResult(content=json.dumps(file_data))

    async def chat_stream(self, messages: list[Msg], *, temperature: float = 0.3, **kwargs: Any):
        yield "{}"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    async def list_models(self):
        return []


SAMPLE_DIFF = """diff --git a/src/main.py b/src/main.py
index 1111111..2222222 100644
--- a/src/main.py
+++ b/src/main.py
@@ -10,4 +10,6 @@ def run():
     print("start")
+    print("step 1")
+    print("step 2")
     print("done")
diff --git a/README.md b/README.md
index 3333333..4444444 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,4 @@
 # Sample Project
+Updated documentation.
 Line 2
"""


def test_diff_parsing():
    parsed = parse_unified_diff(SAMPLE_DIFF)
    assert len(parsed) == 2

    main_py = parsed[0]
    assert main_py.path == "src/main.py"
    assert main_py.added_lines_count == 2
    assert main_py.deleted_lines_count == 0
    assert 11 in main_py.valid_lines
    assert 12 in main_py.valid_lines
    assert main_py.changed_lines == 2

    readme = parsed[1]
    assert readme.path == "README.md"
    assert readme.added_lines_count == 1
    assert 2 in readme.valid_lines


def test_invalid_line_numbers_dropped():
    file_diff = ParsedFileDiff(
        path="src/main.py",
        valid_lines={10, 11, 12, 13},
        added_lines_count=2,
    )

    comments = [
        FileComment(
            file="src/main.py",
            line_start=11,
            line_end=12,
            severity="suggestion",
            comment="Valid comment inside hunk.",
        ),
        FileComment(
            file="src/main.py",
            line_start=99,
            line_end=100,
            severity="warning",
            comment="Invalid comment on non-existent line.",
        ),
    ]

    validated = validate_file_comments(comments, file_diff)
    assert len(validated) == 1
    assert validated[0].comment == "Valid comment inside hunk."
    assert validated[0].line_start == 11
    assert validated[0].line_end == 12


@pytest.mark.asyncio
async def test_large_diff_truncation_notice():
    # Build a simulated diff with > 1,500 lines across 15 files
    diff_parts = []
    for i in range(15):
        added = "\n".join(f"+line {k}" for k in range(120))
        diff_parts.append(
            f"diff --git a/file{i}.py b/file{i}.py\n--- a/file{i}.py\n+++ b/file{i}.py\n@@ -1,1 +1,120 @@\n{added}"
        )
    huge_diff = "\n".join(diff_parts)

    repo = Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="huge-repo",
        full_name="octocat/huge-repo",
    )
    pr = PullRequest(
        id=uuid.uuid4(),
        repo_id=repo.id,
        number=77,
        title="Huge Refactoring",
        body="Massive diff",
        state="open",
        author="alice",
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    provider = FakeReviewProvider()

    review_record, final_review, _ = await execute_pr_review(
        session=session,
        pr=pr,
        repo=repo,
        raw_diff=huge_diff,
        provider=provider,
    )

    # Must contain truncation notice
    assert any("1,500" in bullet for bullet in final_review.summary)
    assert any("10 most-changed" in bullet for bullet in final_review.summary)


@pytest.mark.asyncio
async def test_secrets_redaction_and_check():
    secret_diff = """diff --git a/config.py b/config.py
--- a/config.py
+++ b/config.py
@@ -1,2 +1,3 @@
 # Configuration
+GITHUB_TOKEN = "ghp_12345678901234567890"
+API_KEY = "sk-abcdefghijklmnopqrstuvwxyz123456"
"""
    repo = Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="test-repo",
        full_name="octocat/test-repo",
    )
    pr = PullRequest(
        id=uuid.uuid4(),
        repo_id=repo.id,
        number=88,
        title="Add credentials",
        body="Adding secret tokens",
        state="open",
        author="leaker",
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    seen_messages = []

    class InspectingProvider(FakeReviewProvider):
        async def chat(self, messages, *, schema=None, temperature=0.2, **kwargs):
            for m in messages:
                seen_messages.append(m.content)
            return await super().chat(messages, schema=schema, temperature=temperature, **kwargs)

    provider = InspectingProvider()
    _, final_review, _ = await execute_pr_review(
        session=session,
        pr=pr,
        repo=repo,
        raw_diff=secret_diff,
        provider=provider,
    )

    # 1. Regex check must flag secret
    assert final_review.checks["possible_secret"] is True
    assert any("secret" in r.lower() for r in final_review.risk_reasons)

    # 2. Raw token must NEVER appear in any message sent to the LLM
    for msg_text in seen_messages:
        assert "ghp_12345678901234567890" not in msg_text
        assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in msg_text


@pytest.mark.asyncio
async def test_fallback_review_on_repeated_invalid_output():
    repo = Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="test-repo",
        full_name="octocat/test-repo",
    )
    pr = PullRequest(
        id=uuid.uuid4(),
        repo_id=repo.id,
        number=99,
        title="Crashing model test",
        body="Details",
        state="open",
        author="alice",
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_res.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    failing_provider = FakeReviewProvider(fail=True)
    review_record, final_review, _ = await execute_pr_review(
        session=session,
        pr=pr,
        repo=repo,
        raw_diff=SAMPLE_DIFF,
        provider=failing_provider,
    )

    assert review_record.status == "done"
    assert final_review.verdict == "needs_discussion"
    assert any("Unable to complete" in s for s in final_review.summary)


@pytest.fixture
def pr_app_with_db():
    app = create_app()
    session = AsyncMock()

    repo = Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        default_branch="main",
        created_at=datetime.now(timezone.utc),
    )

    pr = PullRequest(
        id=uuid.uuid4(),
        repo_id=repo.id,
        number=101,
        title="Fix core issue",
        body="Closes #10",
        state="open",
        author="newbie_dev",
        author_is_first_time=True,
        created_at_gh=datetime.now(timezone.utc),
        updated_at_gh=datetime.now(timezone.utc),
    )

    review = PRReview(
        id=uuid.uuid4(),
        pr_id=pr.id,
        status="done",
        summary="Added tests\nFixed logic",
        risk_level="low",
        checks={"tests_updated": True, "possible_secret": False},
        file_comments=[
            {
                "file": "src/main.py",
                "line_start": 12,
                "line_end": 12,
                "severity": "suggestion",
                "comment": "Nice work",
            }
        ],
        newcomer_explainer="Plain English explanation.",
        verdict="approve_ready",
        model="gemma3:4b",
        prompt_version="v1",
        created_at=datetime.now(timezone.utc),
    )

    spam = SpamAssessment(
        id=uuid.uuid4(),
        pr_id=pr.id,
        spam_score=15,
        reasons=["Genuine PR"],
        rule_signals={},
        recommended_action="approve",
        polite_comment="Thanks!",
        created_at=datetime.now(timezone.utc),
    )

    settings_row = Setting(
        id=1,
        github_token_enc=None,
    )

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "from settings" in stmt_str:
            mock_result.scalar_one_or_none.return_value = settings_row
        elif "count" in stmt_str:
            mock_result.scalar.return_value = 1
        elif "from repositories" in stmt_str:
            mock_result.scalar_one_or_none.return_value = repo
        elif "from pull_requests" in stmt_str:
            if "order by" in stmt_str and "limit" in stmt_str:
                mock_result.scalars.return_value.all.return_value = [pr]
            else:
                mock_result.scalar_one_or_none.return_value = pr
        elif "from pr_reviews" in stmt_str:
            mock_result.scalar_one_or_none.return_value = review
        elif "from spam_assessments" in stmt_str:
            mock_result.scalar_one_or_none.return_value = spam
        elif "from chunks" in stmt_str:
            mock_result.scalars.return_value.all.return_value = []
        else:
            mock_result.scalar_one_or_none.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    session.execute.side_effect = mock_execute
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return app, session, repo, pr, review, settings_row


@pytest.mark.asyncio
async def test_prs_list_and_detail(pr_app_with_db):
    app, _, repo, pr, review, _ = pr_app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Pagination validation
        resp_bad_page = await client.get(f"/api/v1/repos/{repo.id}/prs?page=0")
        assert resp_bad_page.status_code == 422

        resp_bad_size = await client.get(f"/api/v1/repos/{repo.id}/prs?page_size=101")
        assert resp_bad_size.status_code == 422

        # Valid list
        resp = await client.get(f"/api/v1/repos/{repo.id}/prs?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        item = data["items"][0]
        assert item["number"] == 101
        assert item["author_is_first_time"] is True
        assert item["latest_review"]["verdict"] == "approve_ready"
        assert item["latest_spam_assessment"]["spam_score"] == 15

        # Detail
        resp_detail = await client.get(f"/api/v1/prs/{pr.id}")
        assert resp_detail.status_code == 200
        detail_data = resp_detail.json()
        assert detail_data["id"] == str(pr.id)
        assert detail_data["latest_review"]["summary"] == ["Added tests", "Fixed logic"]


@pytest.mark.asyncio
@respx.mock
async def test_prs_sync(pr_app_with_db):
    app, session, repo, _, _, _ = pr_app_with_db

    # Mock GitHub open PRs endpoint
    respx.get("https://api.github.com/repos/octocat/Hello-World/pulls?state=open&per_page=100").respond(
        status_code=200,
        json=[
            {
                "number": 201,
                "title": "New feature from first-timer",
                "body": "Hi, first time contributing!",
                "state": "open",
                "user": {"login": "first_user"},
                "author_association": "FIRST_TIME_CONTRIBUTOR",
                "html_url": "https://github.com/octocat/Hello-World/pull/201",
                "head": {"sha": "abc1234"},
                "created_at": "2026-10-31T00:00:00Z",
                "updated_at": "2026-10-31T01:00:00Z",
            }
        ],
    )

    mock_provider = FakeReviewProvider()
    with patch("app.routers.prs.get_provider", return_value=mock_provider):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(f"/api/v1/repos/{repo.id}/prs/sync")
            assert resp.status_code == 200
            data = resp.json()
            assert data["synced_prs"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_sse_review_stream_order(pr_app_with_db):
    app, session, repo, pr, _, _ = pr_app_with_db

    # Mock GitHub raw diff endpoint
    respx.get("https://api.github.com/repos/octocat/Hello-World/pulls/101").respond(
        status_code=200,
        text=SAMPLE_DIFF,
    )

    mock_provider = FakeReviewProvider()
    with patch("app.routers.prs.get_provider", return_value=mock_provider):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(f"/api/v1/prs/{pr.id}/review")
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

            # Parse SSE events in order
            events = []
            for line in resp.text.splitlines():
                if line.startswith("event:"):
                    events.append(line.split(":", 1)[1].strip())

            # Progress must be sent, followed by result, followed by done
            assert "progress" in events
            assert "result" in events
            assert "done" in events
            # Verify relative order
            first_prog = events.index("progress")
            res_idx = events.index("result")
            done_idx = events.index("done")
            assert first_prog < res_idx < done_idx


@pytest.mark.asyncio
@respx.mock
async def test_post_review_without_and_with_token(pr_app_with_db):
    app, session, repo, pr, review, settings_row = pr_app_with_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Without token: returns 409 conflict with markdown in details
        settings_row.github_token_enc = None
        resp_no_token = await client.post(f"/api/v1/prs/{pr.id}/review/post")
        assert resp_no_token.status_code == 409
        err = resp_no_token.json()["error"]
        assert err["code"] == "conflict"
        assert "markdown" in err["details"]
        assert "RepoQuest PR Review" in err["details"]["markdown"]

        # 2. With token: calls GitHub API and returns 200
        settings_row.github_token_enc = encrypt_token("ghp_testToken12345678901234567890")

        respx.post("https://api.github.com/repos/octocat/Hello-World/pulls/101/reviews").respond(
            status_code=200,
            json={"id": 8888, "state": "APPROVED"},
        )

        resp_with_token = await client.post(f"/api/v1/prs/{pr.id}/review/post")
        assert resp_with_token.status_code == 200
        data = resp_with_token.json()
        assert data["status"] == "posted"
        assert data["review_id"] == str(review.id)
        assert review.status == "posted"
