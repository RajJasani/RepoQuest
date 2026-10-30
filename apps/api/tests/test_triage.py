from __future__ import annotations

from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
import respx

from app.core.security import encrypt_token
from app.models.core import Repository, Setting
from app.models.features import Issue
from app.providers.base import ChatResult, Msg
from app.services.triage import (
    approve_issue,
    find_candidate_duplicates,
    reject_issue,
    triage_issue,
)


class MockTriageProvider:
    def __init__(self, raw_json_response: str = None, should_fail: bool = False):
        self.raw_json = raw_json_response or (
            '{"type": "bug", "severity": "P1", "labels": ["bug", "hallucinated_label"], '
            '"summary": "Fix button crash.", "missing_info": ["logs"], "duplicates": [], '
            '"good_first_issue_score": 10, "suggested_reply": "Thanks for reporting!", "confidence": 0.95}'
        )
        self.should_fail = should_fail
        self.chat_model = "gemma3:4b"

    async def chat(
        self,
        messages: list[Msg],
        *,
        schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> ChatResult:
        if self.should_fail:
            return ChatResult(content="not valid json at all")
        return ChatResult(content=self.raw_json)

    async def chat_stream(
        self,
        messages: list[Msg],
        *,
        temperature: float = 0.3,
        **kwargs: Any,
    ):
        yield self.raw_json

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _ in texts]

    async def list_models(self):
        return []


@pytest.mark.asyncio
async def test_find_candidate_duplicates_threshold():
    repo_id = uuid.uuid4()
    current_issue_id = uuid.uuid4()
    query_emb = [1.0, 0.0, 0.0]

    # Candidate 1: identical vector -> sim 1.0 (>= 0.82)
    iss1 = Issue(
        id=uuid.uuid4(),
        repo_id=repo_id,
        number=1,
        title="Crash on button click",
        state="open",
        embedding=[1.0, 0.0, 0.0],
    )

    # Candidate 2: high similarity -> sim ~0.89 (>= 0.82)
    iss2 = Issue(
        id=uuid.uuid4(),
        repo_id=repo_id,
        number=2,
        title="Button crashes the UI",
        state="open",
        embedding=[0.9, 0.1, 0.0],
    )

    # Candidate 3: low similarity -> sim ~0.0 (< 0.82)
    iss3 = Issue(
        id=uuid.uuid4(),
        repo_id=repo_id,
        number=3,
        title="Unrelated documentation typo",
        state="open",
        embedding=[0.0, 1.0, 0.0],
    )

    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [iss1, iss2, iss3]
        return mock_result

    session.execute.side_effect = mock_execute

    candidates = await find_candidate_duplicates(
        session=session,
        repo_id=repo_id,
        issue_id=current_issue_id,
        query_embedding=query_emb,
    )

    # Only issues with sim >= 0.82 are returned
    cand_numbers = [c.number for c, _ in candidates]
    assert 1 in cand_numbers
    assert 2 in cand_numbers
    assert 3 not in cand_numbers


@pytest.mark.asyncio
async def test_label_whitelisting_in_code():
    repo = Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        labels=["bug", "documentation"],  # Allowed repo labels
    )

    issue = Issue(
        id=uuid.uuid4(),
        repo_id=repo.id,
        number=10,
        title="Button is broken",
        body="It throws an exception",
        state="open",
        triage_status="untriaged",
        embedding=[1.0, 0.0, 0.0],
    )

    # LLM outputs "bug" (valid) and "hallucinated_label" (invalid)
    provider = MockTriageProvider()

    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None
        return mock_result

    session.execute.side_effect = mock_execute
    session.add = MagicMock()

    analysis = await triage_issue(
        session=session,
        issue=issue,
        repo=repo,
        provider=provider,
    )

    assert analysis.type == "bug"
    assert "bug" in analysis.labels
    # Hallucinated label must be stripped in code
    assert "hallucinated_label" not in analysis.labels
    assert issue.triage_status == "suggested"


@pytest.mark.asyncio
async def test_invalid_json_retries_then_needs_human():
    repo = Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        labels=["bug"],
    )

    issue = Issue(
        id=uuid.uuid4(),
        repo_id=repo.id,
        number=11,
        title="Completely malformed output",
        body="Cannot parse",
        state="open",
        triage_status="untriaged",
        embedding=[1.0, 0.0, 0.0],
    )

    # Provider returns invalid JSON across all retries
    failing_provider = MockTriageProvider(should_fail=True)

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_res.scalars.return_value.all.return_value = []
    mock_res.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res)
    added_objects = []
    session.add = MagicMock(side_effect=lambda o: added_objects.append(o))

    analysis = await triage_issue(
        session=session,
        issue=issue,
        repo=repo,
        provider=failing_provider,
    )

    # Issue status must become 'needs_human'
    assert issue.triage_status == "needs_human"
    assert "needs human review" in analysis.summary.lower()


@pytest.mark.asyncio
async def test_approve_issue_without_token():
    repo = Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        labels=["bug", "help wanted"],
    )

    issue = Issue(
        id=uuid.uuid4(),
        repo_id=repo.id,
        number=12,
        title="Needs fix",
        state="open",
        labels=["old_label"],
        triage_status="suggested",
    )

    settings_row = Setting(id=1, github_token_enc=None)

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res)
    session.add = MagicMock()

    result = await approve_issue(
        session=session,
        issue=issue,
        repo=repo,
        settings_row=settings_row,
        labels=["bug", "help wanted"],
        comment="LGTM!",
        post_to_github=True,
    )

    # Without token, cannot post to GitHub; marks approved and returns comment
    assert result["status"] == "approved"
    assert result["posted_to_github"] is False
    assert result["labels"] == ["bug", "help wanted"]
    assert issue.triage_status == "approved"


@pytest.mark.asyncio
@respx.mock
async def test_approve_issue_with_token():
    repo = Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        labels=["bug", "p1"],
    )

    issue = Issue(
        id=uuid.uuid4(),
        repo_id=repo.id,
        number=13,
        title="Severe bug",
        state="open",
        labels=[],
        triage_status="suggested",
    )

    enc_token = encrypt_token("ghp_validToken12345678901234567890")
    settings_row = Setting(id=1, github_token_enc=enc_token)

    # Mock GitHub API endpoints
    respx.post("https://api.github.com/repos/octocat/Hello-World/issues/13/labels").respond(
        status_code=200,
        json=[{"name": "bug"}, {"name": "p1"}],
    )
    respx.post("https://api.github.com/repos/octocat/Hello-World/issues/13/comments").respond(
        status_code=201,
        json={"id": 999, "body": "Confirmed bug."},
    )

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res)
    session.add = MagicMock()

    result = await approve_issue(
        session=session,
        issue=issue,
        repo=repo,
        settings_row=settings_row,
        labels=["bug", "p1"],
        comment="Confirmed bug.",
        post_to_github=True,
    )

    # With token, posts to GitHub and marks applied
    assert result["status"] == "applied"
    assert result["posted_to_github"] is True
    assert issue.triage_status == "applied"


@pytest.mark.asyncio
async def test_reject_issue():
    issue = Issue(
        id=uuid.uuid4(),
        repo_id=uuid.uuid4(),
        number=14,
        title="Spam issue",
        state="open",
        triage_status="suggested",
    )

    session = AsyncMock()
    session.add = MagicMock()

    res = await reject_issue(session=session, issue=issue, repo_id=issue.repo_id)
    assert res["status"] == "rejected"
    assert issue.triage_status == "rejected"
