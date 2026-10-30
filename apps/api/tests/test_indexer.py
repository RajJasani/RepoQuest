from __future__ import annotations

from datetime import datetime, timezone
import io
from pathlib import Path
import tarfile
from typing import Any
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest

from app.core.errors import GitHubError, NotFoundError, RateLimitedError
from app.models.core import Repository
from app.services.indexer import IndexerService


def make_tarball(files: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path, content in files.items():
            data = content.encode("utf-8")
            ti = tarfile.TarInfo(name=path)
            ti.size = len(data)
            tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


class FakeProvider:
    def __init__(self, dim: int = 768):
        self.dim = dim
        self.embed_calls: list[list[str]] = []

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(texts)
        return [[0.05] * self.dim for _ in texts]

    async def chat(self, *args, **kwargs):
        pass

    async def chat_stream(self, *args, **kwargs):
        pass

    async def list_models(self):
        return []


def create_mock_session(mock_repo: Repository, existing_chunks: list[tuple[str, Any]] = None):
    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "from repositories" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_repo
        elif "from chunks" in stmt_str and "where" in stmt_str:
            mock_result.all.return_value = existing_chunks or []
        elif "from settings" in stmt_str:
            mock_result.scalar_one_or_none.return_value = None
        else:
            mock_result.scalar_one_or_none.return_value = None
            mock_result.all.return_value = []
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    session.execute.side_effect = mock_execute
    session.add = MagicMock()
    session.add_all = MagicMock()
    session.commit.return_value = None
    session.refresh.return_value = None
    session.flush.return_value = None

    class MockSessionMaker:
        def __call__(self):
            return self

        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            pass

    return MockSessionMaker()


@pytest.fixture
def mock_repo():
    return Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        default_branch="main",
        status="queued",
        progress=0,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_indexer_whole_pipeline_success(tmp_path: Path, mock_repo: Repository):
    tarball = make_tarball({
        "README.md": "# Hello World\nWelcome to our project!\nRun with `python main.py`.",
        "CONTRIBUTING.md": "# Guidelines\nPlease write tests and submit PRs.",
        "main.py": "def hello():\n    return 'world'\n",
        "package.json": '{"name": "hello-pkg", "dependencies": {"react": "^18.0.0"}}',
    })

    fake_gh = AsyncMock()
    fake_gh.get_repo.return_value = {
        "default_branch": "main",
        "description": "Test repo",
        "stargazers_count": 99,
    }
    fake_gh.download_tarball.return_value = tarball
    fake_gh.get_open_issues.return_value = [
        {"number": 1, "title": "First issue", "body": "Broken button", "state": "open"}
    ]
    fake_gh.get_open_pull_requests.return_value = [
        {"number": 2, "title": "First PR", "body": "Fix button", "state": "open"}
    ]

    provider = FakeProvider()
    sm = create_mock_session(mock_repo)

    indexer = IndexerService(
        sessionmaker=sm,
        provider=provider,
        github_client=fake_gh,
        workspace_dir=tmp_path,
    )

    await indexer.index_repository(str(mock_repo.id))

    assert mock_repo.status == "ready"
    assert mock_repo.progress == 100
    assert mock_repo.description == "Test repo"
    assert mock_repo.stars == 99
    assert mock_repo.readme_excerpt is not None
    assert "Hello World" in mock_repo.readme_excerpt
    assert mock_repo.contributing_md is not None
    assert "Guidelines" in mock_repo.contributing_md
    assert "React" in mock_repo.tech_stack

    assert len(provider.embed_calls) >= 1
    assert (tmp_path / str(mock_repo.id) / "main.py").exists()


@pytest.mark.asyncio
async def test_indexer_reindex_idempotency(tmp_path: Path, mock_repo: Repository):
    content = "def add(a, b):\n    return a + b\n"
    from app.services.chunker import compute_content_hash
    content_hash = compute_content_hash(content)

    tarball = make_tarball({
        "math_utils.py": content,
    })

    fake_gh = AsyncMock()
    fake_gh.get_repo.return_value = {"default_branch": "main"}
    fake_gh.download_tarball.return_value = tarball
    fake_gh.get_open_issues.return_value = []
    fake_gh.get_open_pull_requests.return_value = []

    provider = FakeProvider()
    existing_emb = [0.99] * 768
    sm = create_mock_session(mock_repo, existing_chunks=[(content_hash, existing_emb)])

    indexer = IndexerService(
        sessionmaker=sm,
        provider=provider,
        github_client=fake_gh,
        workspace_dir=tmp_path,
    )

    await indexer.index_repository(str(mock_repo.id))

    assert len(provider.embed_calls) == 0
    assert mock_repo.status == "ready"


@pytest.mark.asyncio
async def test_indexer_rate_limit_error_handling(tmp_path: Path, mock_repo: Repository):
    fake_gh = AsyncMock()
    fake_gh.get_repo.side_effect = RateLimitedError(message="API rate limit exceeded")

    sm = create_mock_session(mock_repo)

    indexer = IndexerService(
        sessionmaker=sm,
        provider=FakeProvider(),
        github_client=fake_gh,
        workspace_dir=tmp_path,
    )

    with pytest.raises(RateLimitedError):
        await indexer.index_repository(str(mock_repo.id))

    assert mock_repo.status == "failed"
    assert "rate limit exceeded" in mock_repo.error.lower()


@pytest.mark.asyncio
async def test_indexer_not_found_or_private_error_handling(tmp_path: Path, mock_repo: Repository):
    fake_gh = AsyncMock()
    fake_gh.get_repo.side_effect = NotFoundError("Repository not found")

    sm = create_mock_session(mock_repo)

    indexer = IndexerService(
        sessionmaker=sm,
        provider=FakeProvider(),
        github_client=fake_gh,
        workspace_dir=tmp_path,
    )

    with pytest.raises(NotFoundError):
        await indexer.index_repository(str(mock_repo.id))

    assert mock_repo.status == "failed"
    assert "not found or is private" in mock_repo.error.lower()


@pytest.mark.asyncio
async def test_indexer_github_api_error_handling(tmp_path: Path, mock_repo: Repository):
    fake_gh = AsyncMock()
    fake_gh.get_repo.side_effect = GitHubError("Internal GitHub outage", details={"status": 500})

    sm = create_mock_session(mock_repo)

    indexer = IndexerService(
        sessionmaker=sm,
        provider=FakeProvider(),
        github_client=fake_gh,
        workspace_dir=tmp_path,
    )

    with pytest.raises(GitHubError):
        await indexer.index_repository(str(mock_repo.id))

    assert mock_repo.status == "failed"
    assert "github api error" in mock_repo.error.lower()
