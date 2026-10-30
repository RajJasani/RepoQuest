from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_with_db_and_ollama_down(client: AsyncClient):
    # Without mocks, DB and Ollama are down -> degraded
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["db"] in ("ok", "down")
    assert data["ollama"] in ("ok", "down")


@pytest.mark.asyncio
async def test_health_explicitly_db_down(client: AsyncClient):
    with patch("app.routers.system.get_engine") as mock_engine:
        mock_engine.side_effect = RuntimeError("Connection refused")
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["db"] == "down"


@pytest.mark.asyncio
@respx.mock
async def test_health_with_db_and_ollama_ok(client: AsyncClient):
    # Mock DB ok
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_conn

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_cm

    # Mock Ollama ok
    respx.get("http://host.docker.internal:11434/api/tags").respond(
        status_code=200,
        json={"models": [{"name": "gemma3:4b", "size": 1000, "details": {"family": "gemma"}}]},
    )

    with patch("app.routers.system.get_engine", return_value=mock_engine):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["db"] == "ok"
        assert data["ollama"] == "ok"
        assert data["status"] == "ok"


@pytest.mark.asyncio
@respx.mock
async def test_health_with_ollama_down_and_db_ok(client: AsyncClient):
    # Mock DB ok
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_conn

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_cm

    # Mock Ollama down
    respx.get("http://host.docker.internal:11434/api/tags").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    with patch("app.routers.system.get_engine", return_value=mock_engine):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["db"] == "ok"
        assert data["ollama"] == "down"
        assert data["status"] == "degraded"
