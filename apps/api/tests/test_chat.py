from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import anyio
import pytest
from httpx import ASGITransport, AsyncClient
from sse_starlette.sse import AppStatus

from app.core.db import get_db
from app.main import create_app
from app.models.core import Chunk, Repository
from app.models.features import ChatMessage, ChatSession


@pytest.fixture(autouse=True)
def reset_sse_exit_event():
    AppStatus.should_exit_event = anyio.Event()
    yield
    AppStatus.should_exit_event = None


class FakeChatProvider:
    def __init__(self, tokens: list[str] = None, emb: list[float] = None):
        self.tokens = tokens or ["Authentication", " is", " in", " auth.py", " [1]", " and", " [99]."]
        self.emb = emb or [1.0, 0.0, 0.0]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self.emb for _ in texts]

    async def chat_stream(self, messages: list) -> AsyncIterator[str]:
        for token in self.tokens:
            yield token

    async def chat(self, *args, **kwargs):
        pass

    async def list_models(self):
        return []


@pytest.fixture
def mock_repo():
    return Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        default_branch="main",
        status="ready",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_session(mock_repo):
    return ChatSession(
        id=uuid.uuid4(),
        repo_id=mock_repo.id,
        mode="newcomer",
        language="en",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def app_with_db(mock_repo, mock_session):
    app = create_app()
    session = AsyncMock()

    mock_chunk = Chunk(
        id=uuid.uuid4(),
        repo_id=mock_repo.id,
        file_id=uuid.uuid4(),
        chunk_index=0,
        start_line=10,
        end_line=25,
        content="def authenticate_user(): pass",
        content_hash="h1",
        embedding=[1.0, 0.0, 0.0],
    )

    messages_store: list[ChatMessage] = []

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "from repositories" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_repo
        elif "from chat_sessions" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_session
        elif "from chat_messages" in stmt_str:
            mock_result.scalars.return_value.all.return_value = messages_store
        elif "from chunks" in stmt_str:
            mock_result.all.return_value = [(mock_chunk, "src/auth.py")]
        else:
            mock_result.scalar_one_or_none.return_value = None
            mock_result.all.return_value = []
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    session.execute.side_effect = mock_execute
    session.add = MagicMock(side_effect=lambda obj: messages_store.append(obj) if isinstance(obj, ChatMessage) else None)
    session.commit.return_value = None
    session.refresh.return_value = None
    session.delete.return_value = None

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return app, session, mock_repo, mock_session, messages_store


@pytest.mark.asyncio
async def test_create_chat_session_success(app_with_db):
    app, _, mock_repo, _, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            f"/api/v1/repos/{mock_repo.id}/chat/sessions",
            json={"mode": "expert", "language": "hi"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "expert"
        assert data["language"] == "hi"
        assert data["repo_id"] == str(mock_repo.id)
        assert "id" in data


@pytest.mark.asyncio
async def test_create_chat_session_validation_error(app_with_db):
    app, _, mock_repo, _, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Invalid mode
        resp_mode = await client.post(
            f"/api/v1/repos/{mock_repo.id}/chat/sessions",
            json={"mode": "invalid_mode", "language": "en"},
        )
        assert resp_mode.status_code == 422
        assert resp_mode.json()["error"]["code"] == "validation_error"

        # Invalid language
        resp_lang = await client.post(
            f"/api/v1/repos/{mock_repo.id}/chat/sessions",
            json={"mode": "newcomer", "language": "fr"},
        )
        assert resp_lang.status_code == 422
        assert resp_lang.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_chat_message_length_validation(app_with_db):
    app, _, _, mock_session, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Exceeds 2,000 characters
        too_long = "x" * 2001
        resp = await client.post(
            f"/api/v1/chat/sessions/{mock_session.id}/messages",
            json={"content": too_long},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "validation_error"

        # Empty string
        resp_empty = await client.post(
            f"/api/v1/chat/sessions/{mock_session.id}/messages",
            json={"content": "   "},
        )
        assert resp_empty.status_code == 422


@pytest.mark.asyncio
async def test_chat_message_streaming_and_citations(app_with_db):
    app, session, _, mock_session, messages_store = app_with_db
    fake_provider = FakeChatProvider()

    transport = ASGITransport(app=app)
    with patch("app.routers.chat.get_provider", return_value=fake_provider):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                f"/api/v1/chat/sessions/{mock_session.id}/messages",
                json={"content": "Where is auth handled?"},
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            text = resp.text

            # Token events
            assert "event: token" in text
            assert "Authentication" in text

            # Citation events: [1] should be emitted, [99] should NOT
            assert "event: citation" in text
            assert "src/auth.py" in text

            # Done event
            assert "event: done" in text

            # Verify persisted messages
            roles = [m.role for m in messages_store]
            assert "user" in roles
            assert "assistant" in roles
            asst_msg = next(m for m in messages_store if m.role == "assistant")
            assert len(asst_msg.citations) == 1
            assert asst_msg.citations[0]["file"] == "src/auth.py"
            # [99] was stripped from cleaned content
            assert "[99]" not in asst_msg.content


@pytest.mark.asyncio
async def test_chat_message_low_confidence_streaming(app_with_db):
    app, session, _, mock_session, messages_store = app_with_db
    # Orthogonal embedding -> similarity 0.0 < 0.35
    fake_provider = FakeChatProvider(emb=[0.0, 1.0, 0.0])

    transport = ASGITransport(app=app)
    with patch("app.routers.chat.get_provider", return_value=fake_provider):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                f"/api/v1/chat/sessions/{mock_session.id}/messages",
                json={"content": "where is completely unrelated rocket engine logic?"},
            )
            assert resp.status_code == 200
            text = resp.text

            assert "event: token" in text
            assert "event: done" in text
            # Reconstruct streamed text from token payloads
            import json
            tokens = [
                json.loads(line[6:])["text"]
                for line in text.splitlines()
                if line.startswith("data: ") and '"text"' in line
            ]
            full_msg = "".join(tokens)
            assert "could not find this in the repo" in full_msg.lower()


@pytest.mark.asyncio
async def test_get_chat_session_history(app_with_db):
    app, session, _, mock_session, messages_store = app_with_db

    # Add mock messages
    m1 = ChatMessage(
        id=uuid.uuid4(),
        session_id=mock_session.id,
        role="user",
        content="Hello!",
        citations=[],
        created_at=datetime.now(timezone.utc),
    )
    m2 = ChatMessage(
        id=uuid.uuid4(),
        session_id=mock_session.id,
        role="assistant",
        content="Hi there! [1]",
        citations=[{"file": "src/main.py", "start_line": 1, "end_line": 5}],
        created_at=datetime.now(timezone.utc),
    )
    messages_store.extend([m1, m2])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/api/v1/chat/sessions/{mock_session.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(mock_session.id)
        assert len(data["messages"]) == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][1]["role"] == "assistant"
        assert len(data["messages"][1]["citations"]) == 1


@pytest.mark.asyncio
async def test_delete_chat_session(app_with_db):
    app, session, _, mock_session, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.delete(f"/api/v1/chat/sessions/{mock_session.id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"
        session.delete.assert_awaited_once_with(mock_session)
