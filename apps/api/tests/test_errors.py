import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.errors import AppError
from app.main import create_app


class ItemPayload(BaseModel):
    name: str
    count: int


@pytest.mark.asyncio
async def test_404_error_format(client: AsyncClient):
    response = await client.get("/api/v1/nonexistent-endpoint")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "not_found"
    assert isinstance(data["error"]["message"], str)
    assert data["error"]["details"] == {}


@pytest.mark.asyncio
async def test_422_validation_error_format():
    app = create_app()

    @app.post("/test-validation")
    async def endpoint(payload: ItemPayload):
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        # Send invalid payload (missing name, count is string)
        response = await test_client.post("/test-validation", json={"count": "not-an-int"})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "validation_error"
        assert data["error"]["message"] == "Request validation failed"
        assert isinstance(data["error"]["details"], list)
        assert len(data["error"]["details"]) > 0


@pytest.mark.asyncio
async def test_injected_500_error_format():
    app = create_app()

    @app.get("/test-injected-500")
    async def blow_up():
        raise RuntimeError("Secret database connection string: postgresql://admin:supersecret@db:5432")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        response = await test_client.get("/test-injected-500")
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "internal_error"
        assert data["error"]["message"] == "Internal server error"
        assert data["error"]["details"] == {}
        # Ensure secret and stack traces are not leaked
        assert "supersecret" not in response.text
        assert "Traceback" not in response.text


@pytest.mark.asyncio
async def test_app_error_token_sanitization():
    app = create_app()

    @app.get("/test-token-leak")
    async def leak_token():
        raise AppError(
            message="Failed with ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            details={"token": "ghp_secret_token", "info": "safe info"},
            code="github_error",
            status_code=502,
        )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        response = await test_client.get("/test-token-leak")
        assert response.status_code == 502
        data = response.json()
        assert data["error"]["code"] == "github_error"
        assert "ghp_1234567890abcdefghijklmnopqrstuvwxyz" not in response.text
        assert "ghp_secret_token" not in response.text
        assert "[REDACTED]" in data["error"]["message"]
        assert data["error"]["details"]["token"] == "[REDACTED]"
        assert data["error"]["details"]["info"] == "safe info"


@pytest.mark.asyncio
async def test_request_id_header(client: AsyncClient):
    # Without request ID header -> returns generated one
    res1 = await client.get("/api/v1/health")
    assert "x-request-id" in res1.headers
    generated_id = res1.headers["x-request-id"]
    assert len(generated_id) > 0

    # With custom request ID header -> returns same request ID
    custom_id = "test-req-id-12345"
    res2 = await client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert res2.headers.get("x-request-id") == custom_id
