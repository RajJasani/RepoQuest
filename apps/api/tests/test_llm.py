import json
from typing import Literal
import httpx
import pytest
import respx
from pydantic import BaseModel, Field

from app.core.errors import LLMUnavailableError
from app.providers.base import Msg
from app.providers.ollama import OllamaProvider
from app.providers.openai_compat import OpenAICompatProvider
from app.schemas.llm import (
    Duplicate,
    FileComment,
    FileReview,
    IssueBrief,
    OnboardingPath,
    OnboardingStep,
    PRReview,
    QuizQuestion,
    SpamLLMResult,
    TriageResult,
)
from app.services.redact import redact_secrets, should_skip_file
from app.services.structured import run_structured_pipeline


# Dummy schema for pipeline testing
class SimpleResponse(BaseModel):
    summary: str
    score: int = Field(ge=0, le=100)
    category: Literal["A", "B"]


@pytest.mark.asyncio
@respx.mock
async def test_ollama_chat_success():
    provider = OllamaProvider(base_url="http://test-ollama:11434", chat_model="gemma3:4b")

    mock_response = {
        "model": "gemma3:4b",
        "message": {"role": "assistant", "content": '{"summary": "test", "score": 80, "category": "A"}'},
        "prompt_eval_count": 42,
        "eval_count": 18,
    }

    route = respx.post("http://test-ollama:11434/api/chat").respond(status_code=200, json=mock_response)

    schema = SimpleResponse.model_json_schema()
    messages = [Msg(role="user", content="Hello!")]

    result = await provider.chat(messages, schema=schema, temperature=0.2)

    assert route.called
    req_body = json.loads(route.calls.last.request.content)
    assert req_body["model"] == "gemma3:4b"
    assert req_body["stream"] is False
    assert req_body["options"]["temperature"] == 0.2
    assert req_body["options"]["num_ctx"] == 8192
    assert req_body["format"] == schema

    assert result.content == '{"summary": "test", "score": 80, "category": "A"}'
    assert result.tokens_in == 42
    assert result.tokens_out == 18
    assert result.latency_ms is not None and result.latency_ms >= 0


@pytest.mark.asyncio
@respx.mock
async def test_ollama_embed_batching_32():
    provider = OllamaProvider(base_url="http://test-ollama:11434", embed_model="nomic-embed-text")

    # Mock embed endpoint to return dummy 768-dim embeddings matching input count
    def embed_side_effect(request: httpx.Request):
        data = json.loads(request.content)
        inputs = data["input"]
        return httpx.Response(status_code=200, json={"embeddings": [[0.1] * 768 for _ in inputs]})

    route = respx.post("http://test-ollama:11434/api/embed").mock(side_effect=embed_side_effect)

    # 70 texts -> 32 + 32 + 6 = 3 batches
    texts = [f"Text chunk number {i}" for i in range(70)]
    embeddings = await provider.embed(texts)

    assert len(embeddings) == 70
    assert route.call_count == 3

    # Check batch sizes
    call_1_data = json.loads(route.calls[0].request.content)
    call_2_data = json.loads(route.calls[1].request.content)
    call_3_data = json.loads(route.calls[2].request.content)

    assert len(call_1_data["input"]) == 32
    assert len(call_2_data["input"]) == 32
    assert len(call_3_data["input"]) == 6


@pytest.mark.asyncio
@respx.mock
async def test_ollama_unreachable_gives_llm_unavailable():
    provider = OllamaProvider(base_url="http://test-ollama:11434")

    # ConnectError
    respx.post("http://test-ollama:11434/api/chat").mock(side_effect=httpx.ConnectError("Connection refused"))
    respx.post("http://test-ollama:11434/api/embed").mock(side_effect=httpx.ConnectTimeout("Timed out"))
    respx.get("http://test-ollama:11434/api/tags").mock(side_effect=httpx.NetworkError("Network down"))

    with pytest.raises(LLMUnavailableError) as exc_chat:
        await provider.chat([Msg(role="user", content="hi")])
    assert exc_chat.value.code == "llm_unavailable"

    with pytest.raises(LLMUnavailableError) as exc_embed:
        await provider.embed(["sample text"])
    assert exc_embed.value.code == "llm_unavailable"

    with pytest.raises(LLMUnavailableError) as exc_tags:
        await provider.list_models()
    assert exc_tags.value.code == "llm_unavailable"


@pytest.mark.asyncio
@respx.mock
async def test_structured_invalid_json_then_repaired():
    provider = OllamaProvider(base_url="http://test-ollama:11434")

    # Attempt 0: Invalid JSON
    # Attempt 1 (repair): Valid JSON
    responses = [
        {"model": "gemma3:4b", "message": {"role": "assistant", "content": "I am not JSON!"}, "eval_count": 5},
        {
            "model": "gemma3:4b",
            "message": {
                "role": "assistant",
                "content": '{"summary": "Fixed valid summary", "score": 95, "category": "B"}',
            },
            "eval_count": 15,
        },
    ]

    respx.post("http://test-ollama:11434/api/chat").mock(
        side_effect=[
            httpx.Response(200, json=responses[0]),
            httpx.Response(200, json=responses[1]),
        ]
    )

    result = await run_structured_pipeline(
        provider=provider,
        task_name="triage",
        context_text="Issue about a bug",
        schema=SimpleResponse,
        max_retries=2,
    )

    assert result.outcome == "ok"
    assert result.retries == 1
    assert result.data.summary == "Fixed valid summary"
    assert result.data.score == 95
    assert result.data.category == "B"


@pytest.mark.asyncio
@respx.mock
async def test_structured_invalid_after_retries_gives_fallback():
    provider = OllamaProvider(base_url="http://test-ollama:11434")

    # All attempts return invalid JSON
    respx.post("http://test-ollama:11434/api/chat").respond(
        status_code=200,
        json={"model": "gemma3:4b", "message": {"role": "assistant", "content": "Bad format always"}},
    )

    fallback_obj = SimpleResponse(summary="Safe fallback", score=0, category="A")

    result = await run_structured_pipeline(
        provider=provider,
        task_name="triage",
        context_text="Broken input",
        schema=SimpleResponse,
        fallback=fallback_obj,
        max_retries=2,
    )

    assert result.outcome == "invalid_llm_output"
    assert result.retries == 2
    assert result.data.summary == "Safe fallback"
    assert result.data.score == 0
    assert result.error is not None


def test_redaction_files():
    # Should skip sensitive files
    assert should_skip_file(".env") is True
    assert should_skip_file(".env.local") is True
    assert should_skip_file(".env.production") is True
    assert should_skip_file("/path/to/.env.test") is True
    assert should_skip_file("private.pem") is True
    assert should_skip_file("/etc/ssl/cert.pem") is True
    assert should_skip_file("id_rsa.key") is True
    assert should_skip_file("server.key") is True

    # Should not skip normal files
    assert should_skip_file("main.py") is False
    assert should_skip_file("README.md") is False
    assert should_skip_file("package.json") is False
    assert should_skip_file("CONTRIBUTING.md") is False


def test_redaction_token_patterns():
    # GitHub tokens
    gh_text = "My token is ghp_1234567890abcdef1234567890abcdef1234 and github_pat_11AAAAAAA0123456789_abcdefghijklmnopqrstuvwxyz"
    redacted_gh = redact_secrets(gh_text)
    assert "ghp_" not in redacted_gh
    assert "github_pat_" not in redacted_gh
    assert "[REDACTED]" in redacted_gh

    # Bearer tokens
    bearer_text = "Authorization: Bearer ya29.a0ARrdaM_secretTokenValue12345"
    redacted_bearer = redact_secrets(bearer_text)
    assert "secretTokenValue" not in redacted_bearer
    assert "Bearer [REDACTED]" in redacted_bearer

    # OpenAI / AWS / Slack / Private Keys
    mixed_text = (
        "sk-proj-1234567890abcdef1234567890\n"
        "AKIAIOSFODNN7EXAMPLE\n"
        "xoxb-1234567890-123456789012-abcdef123456\n"
        "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...\n-----END RSA PRIVATE KEY-----"
    )
    redacted_mixed = redact_secrets(mixed_text)
    assert "sk-proj-" not in redacted_mixed
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted_mixed
    assert "xoxb-" not in redacted_mixed
    assert "BEGIN RSA PRIVATE KEY" not in redacted_mixed
    assert "[REDACTED]" in redacted_mixed


def test_openai_compat_disabled_by_default():
    provider = OpenAICompatProvider()
    assert provider.enabled is False

    with pytest.raises(LLMUnavailableError) as exc:
        provider._check_enabled()
    assert "disabled by default" in str(exc.value)


@pytest.mark.asyncio
@respx.mock
async def test_structured_post_validate_hook():
    provider = OllamaProvider(base_url="http://test-ollama:11434")

    # LLM outputs triage with an illegal label "hacked_label"
    llm_output = {
        "type": "bug",
        "severity": "P1",
        "labels": ["bug", "hacked_label", "frontend"],
        "summary": "Buttons are overlapping on mobile screen",
        "missing_info": ["browser version"],
        "duplicates": [],
        "good_first_issue_score": 25,
        "suggested_reply": "Thanks for reporting! What browser are you using?",
        "confidence": 0.9,
    }

    respx.post("http://test-ollama:11434/api/chat").respond(
        status_code=200,
        json={"model": "gemma3:4b", "message": {"role": "assistant", "content": json.dumps(llm_output)}},
    )

    allowed_labels = {"bug", "enhancement", "frontend"}

    def sanitize_triage_labels(triage: TriageResult) -> TriageResult:
        # Whitelist labels
        triage.labels = [lbl for lbl in triage.labels if lbl in allowed_labels]
        return triage

    result = await run_structured_pipeline(
        provider=provider,
        task_name="triage",
        context_text="Issue context",
        schema=TriageResult,
        post_validate=sanitize_triage_labels,
    )

    assert result.outcome == "ok"
    assert "hacked_label" not in result.data.labels
    assert result.data.labels == ["bug", "frontend"]


def test_all_output_schemas():
    dup = Duplicate(number=10, similarity=0.88, reason="Same auth issue")
    assert dup.number == 10

    triage = TriageResult(
        type="bug",
        severity="P0",
        labels=["security"],
        summary="Critical auth bypass",
        missing_info=[],
        duplicates=[dup],
        good_first_issue_score=10,
        suggested_reply="Thanks for reporting!",
        confidence=0.95,
    )
    assert triage.severity == "P0"

    fc = FileComment(
        file="auth.py",
        line_start=12,
        line_end=15,
        severity="warning",
        comment="Potential null pointer",
        suggestion="check for None",
    )
    assert fc.file == "auth.py"

    fr = FileReview(file_comments=[fc])
    assert len(fr.file_comments) == 1

    pr = PRReview(
        summary=["Refactors auth flow"],
        risk_level="high",
        risk_reasons=["Touches security core"],
        checks={"tests_updated": True, "breaking_change": False},
        file_comments=[fc],
        newcomer_explainer="This changes how logins work.",
        verdict="needs_changes",
    )
    assert pr.verdict == "needs_changes"

    spam = SpamLLMResult(
        meaningful_change=False,
        matches_description=False,
        looks_generic=True,
        reasons=["Automated spam PR"],
        polite_comment="Thanks, but we cannot accept this PR.",
    )
    assert spam.meaningful_change is False

    brief = IssueBrief(
        context="Newcomer issue context",
        files_to_touch=["routes.py"],
        steps=["Add endpoint", "Write test"],
        acceptance_checklist=["Endpoint works"],
        how_to_test="pytest tests/test_routes.py",
        difficulty="easy",
        estimated_time="1 hour",
    )
    assert brief.difficulty == "easy"

    qq = QuizQuestion(
        question="Where is auth handled?",
        options=["auth.py", "main.py", "db.py"],
        correct_index=0,
        explanation="Defined in auth.py",
    )
    assert qq.correct_index == 0

    step = OnboardingStep(
        title="Explore Auth",
        goal="Understand auth flow",
        files=[{"path": "auth.py", "start_line": 1, "end_line": 50}],
        explanation="Auth module uses JWT.",
        quiz=[qq],
        try_it="Run test_auth.py",
    )
    assert len(step.quiz) == 1

    path = OnboardingPath(
        title="Day-1 Tour",
        steps=[step],
    )
    assert len(path.steps) == 1
