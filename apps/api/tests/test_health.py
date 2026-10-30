from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_with_db_down(client: AsyncClient):
    # Without mock (or with DB down), get_health returns 200 with db: 'down' and status: 'degraded'
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "db" in data
    assert "ollama" in data
    assert data["db"] in ("ok", "down")
    assert data["ollama"] == "unknown"


@pytest.mark.asyncio
async def test_health_explicitly_db_down(client: AsyncClient):
    with patch("app.routers.system.get_engine") as mock_engine:
        mock_engine.side_effect = RuntimeError("Connection refused")
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["db"] == "down"
        assert data["ollama"] == "unknown"


@pytest.mark.asyncio
async def test_health_with_db_ok(client: AsyncClient):
    mock_conn = AsyncMock()
    mock_conn.execute.return_value = None

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_conn

    mock_engine = MagicMock()
    mock_engine.connect.return_value = mock_cm

    with patch("app.routers.system.get_engine", return_value=mock_engine):
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "ok"
        assert data["ollama"] == "unknown"
