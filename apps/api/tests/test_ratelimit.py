import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from app.core.ratelimit import InMemoryRateLimiter
from app.main import create_app


@pytest.mark.asyncio
async def test_rate_limiter_blocks_after_limit():
    app = create_app()
    limiter = InMemoryRateLimiter(requests_per_minute=3, window_seconds=60.0)

    @app.get("/test-limited", dependencies=[Depends(limiter)])
    async def limited_endpoint():
        return {"success": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # First 3 requests should pass
        for _ in range(3):
            res = await client.get("/test-limited")
            assert res.status_code == 200

        # 4th request must be rate limited (429)
        res4 = await client.get("/test-limited")
        assert res4.status_code == 429
        data = res4.json()
        assert "error" in data
        assert data["error"]["code"] == "rate_limited"
        assert "Rate limit exceeded" in data["error"]["message"]
        assert data["error"]["details"]["limit"] == 3


@pytest.mark.asyncio
async def test_rate_limiter_distinct_ips():
    app = create_app()
    limiter = InMemoryRateLimiter(requests_per_minute=2, window_seconds=60.0)

    @app.get("/test-limited-ip", dependencies=[Depends(limiter)])
    async def limited_endpoint():
        return {"success": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Client 1 uses quota
        headers1 = {"X-Forwarded-For": "192.168.1.1"}
        assert (await client.get("/test-limited-ip", headers=headers1)).status_code == 200
        assert (await client.get("/test-limited-ip", headers=headers1)).status_code == 200
        assert (await client.get("/test-limited-ip", headers=headers1)).status_code == 429

        # Client 2 still has quota
        headers2 = {"X-Forwarded-For": "192.168.1.2"}
        assert (await client.get("/test-limited-ip", headers=headers2)).status_code == 200
