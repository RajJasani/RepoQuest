import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cors_allows_configured_origin(client: AsyncClient):
    headers = {"Origin": "http://localhost:3000"}
    response = await client.get("/api/v1/health", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_cors_rejects_foreign_origin(client: AsyncClient):
    headers = {"Origin": "http://evil.com"}
    response = await client.get("/api/v1/health", headers=headers)
    # The response must NOT have access-control-allow-origin for evil.com
    assert response.headers.get("access-control-allow-origin") != "http://evil.com"
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_preflight_rejection(client: AsyncClient):
    headers = {
        "Origin": "http://evil.com",
        "Access-Control-Request-Method": "POST",
    }
    response = await client.options("/api/v1/health", headers=headers)
    # Foreign origin preflight is rejected (400) or missing allow-origin
    assert response.status_code == 400 or "access-control-allow-origin" not in response.headers
