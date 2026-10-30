from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient

from app.core.db import get_db
from app.core.startup import check_embedding_dimension, ensure_seed_data
from app.main import create_app
from app.models.core import Profile, Setting


@pytest.fixture
def mock_db_session():
    setting = Setting(
        id=1,
        ollama_base_url="http://host.docker.internal:11434",
        chat_model="gemma3:4b",
        embed_model="nomic-embed-text",
        triage_mode="suggest",
        spam_threshold=70,
        language="en",
        offline_mode=True,
        github_token_enc=None,
        updated_at=datetime.now(timezone.utc),
    )

    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = setting
        return mock_result

    session.execute.side_effect = mock_execute
    session.add = MagicMock()
    session.commit.return_value = None
    session.refresh.return_value = None

    return session, setting


@pytest.fixture
async def settings_client(mock_db_session):
    session, setting = mock_db_session
    app = create_app()

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, setting


@pytest.mark.asyncio
async def test_get_settings_success(settings_client):
    client, setting = settings_client
    response = await client.get("/api/v1/settings")
    assert response.status_code == 200
    data = response.json()

    assert data["ollama_base_url"] == "http://host.docker.internal:11434"
    assert data["chat_model"] == "gemma3:4b"
    assert data["embed_model"] == "nomic-embed-text"
    assert data["triage_mode"] == "suggest"
    assert data["spam_threshold"] == 70
    assert data["language"] == "en"
    assert data["offline_mode"] is True
    assert data["has_github_token"] is False
    # Crucial security guarantee: token is never returned
    assert "github_token" not in data
    assert "github_token_enc" not in data


@pytest.mark.asyncio
async def test_update_settings_valid(settings_client):
    client, setting = settings_client
    payload = {
        "ollama_base_url": "https://remote-ollama.internal:11434",
        "chat_model": "llama3.2:3b",
        "spam_threshold": 85,
        "language": "hi",
        "triage_mode": "auto",
        "offline_mode": False,
    }

    response = await client.put("/api/v1/settings", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["ollama_base_url"] == "https://remote-ollama.internal:11434"
    assert data["chat_model"] == "llama3.2:3b"
    assert data["spam_threshold"] == 85
    assert data["language"] == "hi"
    assert data["triage_mode"] == "auto"
    assert data["offline_mode"] is False
    assert "github_token" not in data
    assert "github_token_enc" not in data


@pytest.mark.asyncio
async def test_update_settings_validation_errors(settings_client):
    client, _ = settings_client

    # 1. Invalid URL schema (must be http or https)
    res = await client.put("/api/v1/settings", json={"ollama_base_url": "ftp://my-server"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"

    # 2. Spam threshold < 0 or > 100
    res_low = await client.put("/api/v1/settings", json={"spam_threshold": -1})
    assert res_low.status_code == 422
    res_high = await client.put("/api/v1/settings", json={"spam_threshold": 101})
    assert res_high.status_code == 422

    # 3. Invalid language (must be en, hi, kn, ta)
    res_lang = await client.put("/api/v1/settings", json={"language": "es"})
    assert res_lang.status_code == 422

    # 4. Invalid triage mode (must be suggest or auto)
    res_mode = await client.put("/api/v1/settings", json={"triage_mode": "manual"})
    assert res_mode.status_code == 422

    # 5. Empty chat model
    res_empty_model = await client.put("/api/v1/settings", json={"chat_model": "  "})
    assert res_empty_model.status_code == 422


@pytest.mark.asyncio
@respx.mock
async def test_github_token_lifecycle(settings_client):
    client, setting = settings_client

    # Mock valid token verification
    respx.get("https://api.github.com/user").respond(
        status_code=200,
        json={"login": "testuser", "id": 12345},
    )

    # 1. Put token
    raw_token = "ghp_superSecretToken1234567890abcdef"
    put_res = await client.put("/api/v1/settings/github-token", json={"token": raw_token})
    assert put_res.status_code == 200
    assert put_res.json() == {"status": "ok", "has_github_token": True}

    # Verify encrypted in DB and not plaintext
    assert setting.github_token_enc is not None
    assert raw_token not in setting.github_token_enc

    # Verify GET settings reports has_github_token=True and does not expose token
    get_res = await client.get("/api/v1/settings")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["has_github_token"] is True
    assert "github_token" not in get_data
    assert "github_token_enc" not in get_data
    assert raw_token not in str(get_data)

    # 2. Delete token
    del_res = await client.delete("/api/v1/settings/github-token")
    assert del_res.status_code == 200
    assert del_res.json() == {"status": "ok", "has_github_token": False}
    assert setting.github_token_enc is None


@pytest.mark.asyncio
@respx.mock
async def test_github_token_verification_failure(settings_client):
    client, setting = settings_client

    # Mock 401 Bad credentials
    respx.get("https://api.github.com/user").respond(
        status_code=401,
        json={"message": "Bad credentials"},
    )

    put_res = await client.put("/api/v1/settings/github-token", json={"token": "ghp_badToken"})
    assert put_res.status_code == 502
    assert put_res.json()["error"]["code"] == "github_error"
    assert setting.github_token_enc is None


@pytest.mark.asyncio
@respx.mock
async def test_get_models_success(settings_client):
    client, _ = settings_client

    respx.get("http://host.docker.internal:11434/api/tags").respond(
        status_code=200,
        json={
            "models": [
                {
                    "name": "gemma3:4b",
                    "size": 2500000000,
                    "details": {"family": "gemma", "parameter_size": "4B"},
                    "modified_at": "2026-10-30T10:00:00Z",
                },
                {
                    "name": "nomic-embed-text",
                    "size": 274000000,
                    "details": {"family": "nomic-bert"},
                    "modified_at": "2026-10-30T11:00:00Z",
                },
            ]
        },
    )

    response = await client.get("/api/v1/models")
    assert response.status_code == 200
    models = response.json()
    assert len(models) == 2
    assert models[0]["name"] == "gemma3:4b"
    assert models[0]["family"] == "gemma"
    assert models[0]["size"] == 2500000000


@pytest.mark.asyncio
@respx.mock
async def test_get_models_ollama_unreachable(settings_client):
    client, _ = settings_client

    respx.get("http://host.docker.internal:11434/api/tags").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    response = await client.get("/api/v1/models")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_unavailable"


@pytest.mark.asyncio
async def test_ensure_seed_data_logic():
    session = AsyncMock()
    session.add = MagicMock()

    # Case 1: Rows do not exist -> both created
    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_res_none

    await ensure_seed_data(session)

    assert session.add.call_count == 2
    added_types = [type(call[0][0]) for call in session.add.call_args_list]
    assert Setting in added_types
    assert Profile in added_types
    assert session.commit.called


@pytest.mark.asyncio
@respx.mock
async def test_embedding_dimension_check(settings_client):
    client, _ = settings_client

    # 1. Probe returns 768 -> ok
    respx.post("http://host.docker.internal:11434/api/embed").respond(
        status_code=200,
        json={"embeddings": [[0.1] * 768]},
    )
    await check_embedding_dimension(None)

    # 2. Probe returns non-768 (e.g. 1536) -> warning and not ok
    respx.post("http://host.docker.internal:11434/api/embed").respond(
        status_code=200,
        json={"embeddings": [[0.1] * 1536]},
    )
    await check_embedding_dimension(None)

    # Check health reports the warning and degraded
    respx.get("http://host.docker.internal:11434/api/tags").respond(
        status_code=200,
        json={"models": []},
    )

    res = await client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["embedding_dimension_ok"] is False
    assert "1536" in data["embedding_dimension_warning"]
    assert data["status"] == "degraded"
