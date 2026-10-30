from collections.abc import AsyncGenerator
import os

from cryptography.fernet import Fernet
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Ensure a valid default Fernet key is set for testing
TEST_FERNET_KEY = Fernet.generate_key().decode()
os.environ.setdefault("APP_SECRET_KEY", TEST_FERNET_KEY)

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()

from app.main import create_app  # noqa: E402


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
