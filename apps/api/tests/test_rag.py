from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from app.models.core import Chunk
from app.services.rag import (
    build_rag_prompt,
    extract_query_keywords,
    process_citations,
    retrieve_rag_context,
)


class FakeProvider:
    def __init__(self, emb: list[float] = None):
        self.emb = emb or [1.0, 0.0, 0.0]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.emb for _ in texts]

    async def chat(self, *args, **kwargs):
        pass

    async def chat_stream(self, *args, **kwargs):
        pass

    async def list_models(self):
        return []


def test_extract_query_keywords():
    keywords = extract_query_keywords("Where is the authentication router and user model handled?")
    assert "authentication" in keywords
    assert "router" in keywords
    assert "user" in keywords
    assert "model" in keywords
    assert "handled" in keywords
    # Stopwords excluded
    assert "where" not in keywords
    assert "the" not in keywords
    assert "and" not in keywords


def test_process_citations_drops_invalid():
    excerpt_map = {
        1: {"file": "src/auth.py", "start_line": 10, "end_line": 25},
        2: {"file": "src/users.py", "start_line": 1, "end_line": 30},
    }
    input_text = "Auth is in auth.py [1] and tokens are in [99]. Users in [2]."
    cleaned, citations = process_citations(input_text, excerpt_map)

    # Valid markers preserved, invalid dropped
    assert "[1]" in cleaned
    assert "[2]" in cleaned
    assert "[99]" not in cleaned
    assert len(citations) == 2
    assert citations[0]["file"] == "src/auth.py"
    assert citations[1]["file"] == "src/users.py"


@pytest.mark.asyncio
async def test_retrieval_ordering_and_top_8():
    repo_id = uuid.uuid4()
    provider = FakeProvider(emb=[1.0, 0.0, 0.0])

    # 10 chunks with varying similarities
    mock_chunks = []
    for i in range(10):
        # Similarity varies with i
        emb = [1.0 - (i * 0.05), (i * 0.05), 0.0]
        c = Chunk(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=uuid.uuid4(),
            chunk_index=i,
            start_line=10 * i + 1,
            end_line=10 * i + 9,
            content=f"content for chunk {i}",
            content_hash=f"hash{i}",
            embedding=emb,
        )
        mock_chunks.append((c, f"src/file_{9 - i}.py"))

    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "from chunks" in stmt_str:
            mock_result.all.return_value = [
                (c, path) for c, path in mock_chunks
            ]
        return mock_result

    session.execute.side_effect = mock_execute

    ctx = await retrieve_rag_context(
        session=session,
        repo_id=repo_id,
        query="test query",
        provider=provider,
    )

    assert not ctx.is_low_confidence
    # Top 8 selected out of 10
    assert len(ctx.excerpts) == 8

    # Verify retained chunks are sorted by path and line
    paths = [fpath for _, fpath, _ in ctx.excerpts]
    assert paths == sorted(paths)

    # Prompt injection defense check
    assert "<retrieved_context>" in ctx.context_text
    assert "</retrieved_context>" in ctx.context_text
    assert "untrusted data" in ctx.context_text.lower()


@pytest.mark.asyncio
async def test_context_budget_trimming():
    repo_id = uuid.uuid4()
    provider = FakeProvider(emb=[1.0, 0.0, 0.0])

    # 8 chunks, each 4,000 characters = ~1,000 tokens
    # 8 * 1,000 = 8,000 tokens > 6,000 budget
    mock_chunks = []
    for i in range(8):
        c = Chunk(
            id=uuid.uuid4(),
            repo_id=repo_id,
            file_id=uuid.uuid4(),
            chunk_index=i,
            start_line=i * 100,
            end_line=i * 100 + 50,
            content="a" * 4000,
            content_hash=f"h{i}",
            # chunk 0 has highest similarity, chunk 7 lowest
            embedding=[1.0 - (i * 0.05), (i * 0.05), 0.0],
        )
        mock_chunks.append((c, f"src/mod_{i}.py"))

    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.all.return_value = mock_chunks
        return mock_result

    session.execute.side_effect = mock_execute

    ctx = await retrieve_rag_context(
        session=session,
        repo_id=repo_id,
        query="test query",
        provider=provider,
    )

    # Chunks trimmed so total chars / 4 <= 6000
    total_tokens = sum(len(c.content) // 4 for c, _, _ in ctx.excerpts)
    assert total_tokens <= 6000
    assert len(ctx.excerpts) < 8
    # Lowest scored chunks were dropped first
    retained_paths = [p for _, p, _ in ctx.excerpts]
    assert "src/mod_0.py" in retained_paths


@pytest.mark.asyncio
async def test_low_confidence_path():
    repo_id = uuid.uuid4()
    # Provider vector is orthogonal to chunks -> similarity ~0.0 < 0.35
    provider = FakeProvider(emb=[0.0, 1.0, 0.0])

    c = Chunk(
        id=uuid.uuid4(),
        repo_id=repo_id,
        file_id=uuid.uuid4(),
        chunk_index=0,
        start_line=1,
        end_line=10,
        content="unrelated code",
        content_hash="hash",
        embedding=[1.0, 0.0, 0.0],  # orthogonal -> similarity 0.0
    )

    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.all.return_value = [(c, "src/unrelated.py")]
        return mock_result

    session.execute.side_effect = mock_execute

    ctx = await retrieve_rag_context(
        session=session,
        repo_id=repo_id,
        query="where is database configured?",
        provider=provider,
    )

    assert ctx.is_low_confidence is True
    assert "I could not find this in the repo" in ctx.fallback_answer
    assert len(ctx.excerpts) == 0


def test_build_rag_prompt_modes_and_languages():
    from app.services.rag import RAGContext
    ctx = RAGContext(
        excerpts=[],
        excerpt_map={},
        context_text="<retrieved_context>code</retrieved_context>",
        is_low_confidence=False,
    )

    # Newcomer mode in Hindi
    msgs_hi = build_rag_prompt(ctx, "Question?", mode="newcomer", language="hi")
    sys_content = msgs_hi[0]["content"]
    assert "Newcomer" in sys_content
    assert "Hindi" in sys_content
    assert "analogy" in sys_content.lower()

    # Expert mode in English
    msgs_en = build_rag_prompt(ctx, "Question?", mode="expert", language="en")
    sys_expert = msgs_en[0]["content"]
    assert "Expert" in sys_expert
    assert "concise" in sys_expert.lower()
