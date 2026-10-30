from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import anyio
import pytest
from httpx import ASGITransport, AsyncClient
from sse_starlette.sse import AppStatus

from app.core.db import get_db
from app.main import create_app
from app.models.core import File, Repository
from app.services.indexer import broadcast_progress


@pytest.fixture(autouse=True)
def reset_sse_exit_event():
    AppStatus.should_exit_event = anyio.Event()
    yield
    AppStatus.should_exit_event = None


@pytest.fixture
def mock_repo_record():
    return Repository(
        id=uuid.uuid4(),
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        default_branch="main",
        description="A great repository",
        stars=42,
        status="ready",
        progress=100,
        languages={"Python": 100},
        tech_stack=["FastAPI"],
        contributing_md="# Contributing",
        readme_excerpt="# Readme",
        run_instructions="Run python main.py",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_files(mock_repo_record):
    return [
        File(
            id=uuid.uuid4(),
            repo_id=mock_repo_record.id,
            path="src/main.py",
            language="Python",
            size_bytes=100,
            content_hash="hash1",
        ),
        File(
            id=uuid.uuid4(),
            repo_id=mock_repo_record.id,
            path="src/utils/helpers.py",
            language="Python",
            size_bytes=200,
            content_hash="hash2",
        ),
        File(
            id=uuid.uuid4(),
            repo_id=mock_repo_record.id,
            path="README.md",
            language="Markdown",
            size_bytes=50,
            content_hash="hash3",
        ),
    ]


@pytest.fixture
def app_with_db(mock_repo_record, mock_files):
    app = create_app()
    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "count" in stmt_str:
            mock_result.scalar.return_value = len(mock_files)
        elif "from repositories" in stmt_str and "where" in stmt_str:
            # Check if matching repo_record
            mock_result.scalar_one_or_none.return_value = mock_repo_record
        elif "from repositories" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [mock_repo_record]
        elif "from files" in stmt_str and "where" in stmt_str:
            if "files.path =" in stmt_str:
                # Find matching file in mock_files
                mock_result.scalar_one_or_none.return_value = mock_files[0]
            else:
                mock_result.scalars.return_value.all.return_value = mock_files
        else:
            mock_result.scalar_one_or_none.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        return mock_result

    session.execute.side_effect = mock_execute
    session.add = MagicMock()
    session.commit.return_value = None
    session.flush.return_value = None
    session.delete.return_value = None

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return app, session, mock_repo_record, mock_files


@pytest.mark.asyncio
async def test_post_repo_valid(app_with_db):
    app, session, _, _ = app_with_db
    # Mock no existing repository with this full_name
    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        return mock_result
    session.execute.side_effect = mock_execute

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/api/v1/repos", json={"url": "https://github.com/facebook/react"})
        assert resp.status_code == 202
        data = resp.json()
        assert "repo_id" in data
        assert "job_id" in data


@pytest.mark.asyncio
async def test_post_repo_invalid_url_returns_422(app_with_db):
    app, _, _, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/api/v1/repos", json={"url": "http://invalid-url.com"})
        assert resp.status_code == 422
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_post_repo_duplicate_returns_409(app_with_db):
    app, session, mock_repo, _ = app_with_db
    # Mock existing repository returned
    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_repo
        return mock_result
    session.execute.side_effect = mock_execute

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/api/v1/repos", json={"url": "https://github.com/octocat/Hello-World"})
        assert resp.status_code == 409
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == "conflict"


@pytest.mark.asyncio
async def test_get_repos_list(app_with_db):
    app, _, mock_repo, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/repos")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["full_name"] == mock_repo.full_name


@pytest.mark.asyncio
async def test_get_repo_detail(app_with_db):
    app, _, mock_repo, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/api/v1/repos/{mock_repo.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(mock_repo.id)
        assert data["file_count"] == 3
        assert "FastAPI" in data["tech_stack"]


@pytest.mark.asyncio
async def test_get_repo_not_found(app_with_db):
    app, session, _, _ = app_with_db
    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        return mock_result
    session.execute.side_effect = mock_execute

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        random_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/repos/{random_id}")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_delete_repo_success(app_with_db, tmp_path: Path):
    app, session, mock_repo, _ = app_with_db
    transport = ASGITransport(app=app)
    with patch("app.routers.repos.WORKSPACE_BASE", tmp_path):
        repo_dir = tmp_path / str(mock_repo.id)
        repo_dir.mkdir(parents=True, exist_ok=True)

        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.delete(f"/api/v1/repos/{mock_repo.id}")
            assert resp.status_code == 200
            assert resp.json()["status"] == "deleted"
            session.delete.assert_awaited_once_with(mock_repo)
            assert not repo_dir.exists()


@pytest.mark.asyncio
async def test_reindex_repo_success(app_with_db):
    app, session, mock_repo, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(f"/api/v1/repos/{mock_repo.id}/reindex")
        assert resp.status_code == 202
        data = resp.json()
        assert data["repo_id"] == str(mock_repo.id)
        assert "job_id" in data


@pytest.mark.asyncio
async def test_get_repo_tree_nested(app_with_db):
    app, _, mock_repo, _ = app_with_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/api/v1/repos/{mock_repo.id}/tree")
        assert resp.status_code == 200
        tree = resp.json()

        # Directories first, then files
        names = [n["name"] for n in tree]
        assert "src" in names
        assert "README.md" in names

        # Check nested children
        src_dir = next(n for n in tree if n["name"] == "src")
        assert src_dir["type"] == "directory"
        assert len(src_dir["children"]) == 2  # main.py and utils directory


@pytest.mark.asyncio
async def test_get_repo_file_valid_and_line_slice(app_with_db, tmp_path: Path):
    app, session, mock_repo, _ = app_with_db
    file_content = "line 1\nline 2\nline 3\nline 4\nline 5\n"

    repo_dir = tmp_path / str(mock_repo.id)
    (repo_dir / "src").mkdir(parents=True, exist_ok=True)
    target_file = repo_dir / "src" / "main.py"
    target_file.write_text(file_content, encoding="utf-8")

    transport = ASGITransport(app=app)
    with patch("app.routers.repos.WORKSPACE_BASE", tmp_path):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                f"/api/v1/repos/{mock_repo.id}/files?path=src/main.py&start=2&end=4"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["path"] == "src/main.py"
            assert data["content"] == "line 2\nline 3\nline 4"
            assert data["start_line"] == 2
            assert data["end_line"] == 4
            assert data["total_lines"] == 5


@pytest.mark.asyncio
async def test_get_repo_file_path_traversal_returns_404(app_with_db, tmp_path: Path):
    app, session, mock_repo, _ = app_with_db

    # Traversal path is not in files table
    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        return mock_result
    session.execute.side_effect = mock_execute

    transport = ASGITransport(app=app)
    with patch("app.routers.repos.WORKSPACE_BASE", tmp_path):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                f"/api/v1/repos/{mock_repo.id}/files?path=../../etc/passwd"
            )
            assert resp.status_code == 404
            data = resp.json()
            assert data["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_sse_progress_stream_ready_resumable(app_with_db):
    app, _, mock_repo, _ = app_with_db
    mock_repo.status = "ready"
    mock_repo.progress = 100

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/api/v1/repos/{mock_repo.id}/progress")
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        text = resp.text
        assert "event: progress" in text
        assert "Repository indexing complete" in text
        assert "event: done" in text


@pytest.mark.asyncio
async def test_sse_progress_stream_live_events(app_with_db):
    app, _, mock_repo, _ = app_with_db
    mock_repo.status = "fetching"
    mock_repo.progress = 15

    transport = ASGITransport(app=app)

    async def emit_events():
        await asyncio.sleep(0.05)
        await broadcast_progress(
            str(mock_repo.id),
            "progress",
            {"stage": "chunking", "percent": 35, "message": "Chunking"},
        )
        await asyncio.sleep(0.05)
        await broadcast_progress(str(mock_repo.id), "done", {"repo_id": str(mock_repo.id)})

    emit_task = asyncio.create_task(emit_events())

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/api/v1/repos/{mock_repo.id}/progress")
        assert resp.status_code == 200
        text = resp.text
        assert "event: progress" in text
        assert "Chunking" in text
        assert "event: done" in text

    await emit_task
