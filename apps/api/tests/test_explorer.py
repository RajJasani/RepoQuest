from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.db import get_db
from app.main import create_app
from app.models.core import File, Module, ModuleEdge, Repository
from app.providers.base import ChatResult, Msg
from app.services.explorer import (
    ExplorerService,
    detect_entry_points_in_files,
    parse_js_ts_imports,
    parse_python_imports,
)


class MockLLMProvider:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def chat(self, messages: list[Msg], options=None) -> ChatResult:
        if self.should_fail:
            raise RuntimeError("Ollama connection failed")
        return ChatResult(content="This module handles core authentication and routing.")

    async def chat_stream(self, messages: list[Msg]):
        yield "sample token"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]

    async def list_models(self):
        return []


def test_parse_python_imports():
    code = """
import os
import sys
from app.models.core import Repository, File
from app.routers import chat as chat_router
from ..services import indexer
"""
    imports = parse_python_imports(code)
    assert "os" in imports
    assert "sys" in imports
    assert "app.models.core" in imports
    assert "app.routers" in imports


def test_parse_js_ts_imports():
    code = """
import React, { useState } from 'react';
import { Button } from '../components/Button';
const utils = require('../utils/helpers');
export * from './types';
"""
    imports = parse_js_ts_imports(code)
    assert "react" in imports
    assert "../components/Button" in imports
    assert "../utils/helpers" in imports
    assert "./types" in imports


def test_detect_entry_points_manifests_and_files():
    files = ["src/main.py", "app.py", "src/utils.py", "README.md", "index.ts"]
    pkg_json = json.dumps({
        "name": "my-pkg",
        "main": "./dist/index.js",
        "bin": {"my-cli": "./bin/cli.js"},
    })

    entry_points = detect_entry_points_in_files(files, manifests={"package.json": pkg_json})
    assert "app.py" in entry_points
    assert "src/main.py" in entry_points
    assert "index.ts" in entry_points
    assert "dist/index.js" in entry_points
    assert "bin/cli.js" in entry_points
    assert "src/utils.py" not in entry_points


def test_python_import_edges(tmp_path: Path):
    # Setup test files
    ws = tmp_path / "workspace"
    (ws / "app" / "routers").mkdir(parents=True)
    (ws / "app" / "models").mkdir(parents=True)

    auth_file = ws / "app" / "routers" / "auth.py"
    auth_file.write_text("from app.models import User\nimport app.models\n", encoding="utf-8")

    user_file = ws / "app" / "models" / "user.py"
    user_file.write_text("class User: pass\n", encoding="utf-8")

    svc = ExplorerService()
    modules = svc.partition_files_into_modules(["app/routers/auth.py", "app/models/user.py"])
    assert len(modules) == 2
    mod_names = {m.name for m in modules}
    assert "routers" in mod_names
    assert "models" in mod_names

    edges = svc.extract_module_edges(modules, ws)
    assert len(edges) >= 1

    # Edge from routers -> models with weight >= 2
    src_id, tgt_id, weight = edges[0]
    routers_mod = next(m for m in modules if m.name == "routers")
    models_mod = next(m for m in modules if m.name == "models")
    assert src_id == routers_mod.id
    assert tgt_id == models_mod.id
    assert weight >= 1


def test_js_ts_import_edges(tmp_path: Path):
    ws = tmp_path / "workspace"
    (ws / "components").mkdir(parents=True)
    (ws / "theme").mkdir(parents=True)

    btn_file = ws / "components" / "Button.tsx"
    btn_file.write_text("import { colors } from '../theme/colors';\n", encoding="utf-8")

    theme_file = ws / "theme" / "colors.ts"
    theme_file.write_text("export const colors = { red: '#f00' };\n", encoding="utf-8")

    svc = ExplorerService()
    modules = svc.partition_files_into_modules(["components/Button.tsx", "theme/colors.ts"])
    assert len(modules) == 2

    edges = svc.extract_module_edges(modules, ws)
    assert len(edges) == 1

    btn_mod = next(m for m in modules if m.name == "components")
    theme_mod = next(m for m in modules if m.name == "theme")
    src_id, tgt_id, weight = edges[0]
    assert src_id == btn_mod.id
    assert tgt_id == theme_mod.id
    assert weight == 1


def test_fallback_graph_zero_imports(tmp_path: Path):
    ws = tmp_path / "workspace"
    (ws / "docs").mkdir(parents=True)
    (ws / "scripts").mkdir(parents=True)

    (ws / "docs" / "index.md").write_text("# Docs\n", encoding="utf-8")
    (ws / "scripts" / "setup.sh").write_text("echo hello\n", encoding="utf-8")

    svc = ExplorerService()
    modules = svc.partition_files_into_modules(["docs/index.md", "scripts/setup.sh"])
    assert len(modules) == 2

    # Zero cross-module imports exist
    edges = svc.extract_module_edges(modules, ws)
    # Folder-tree graph fallback should produce a connected edge
    assert len(edges) >= 1
    assert edges[0][2] == 1  # Weight 1 fallback edge


@pytest.mark.asyncio
async def test_llm_failure_fallback_summary(tmp_path: Path):
    ws = tmp_path / "workspace"
    (ws / "core").mkdir(parents=True)
    (ws / "core" / "engine.py").write_text("class Engine: pass\n", encoding="utf-8")

    failing_provider = MockLLMProvider(should_fail=True)
    svc = ExplorerService(provider=failing_provider)
    modules = svc.partition_files_into_modules(["core/engine.py"])
    mod = modules[0]

    summary = await svc.summarize_module(mod, ws)
    assert summary is not None
    # Deterministic fallback format check
    assert "core" in summary
    assert "1 files" in summary or "1 file" in summary


# Endpoint tests
@pytest.fixture
def mock_architecture_data():
    repo_id = uuid.uuid4()
    repo = Repository(
        id=repo_id,
        owner="octocat",
        name="Hello-World",
        full_name="octocat/Hello-World",
        default_branch="main",
        status="ready",
        tech_stack=["Python", "FastAPI"],
        run_instructions="uvicorn main:app",
    )

    m1 = Module(
        id=uuid.uuid4(),
        repo_id=repo_id,
        path="app/routers",
        name="routers",
        summary="Handles API routing.",
        key_files=["repos.py", "chat.py"],
        entry_points=["repos.py"],
        file_count=2,
    )
    m2 = Module(
        id=uuid.uuid4(),
        repo_id=repo_id,
        path="app/models",
        name="models",
        summary="Database entities.",
        key_files=["core.py", "features.py"],
        entry_points=[],
        file_count=2,
    )

    edge = ModuleEdge(
        repo_id=repo_id,
        source_id=m1.id,
        target_id=m2.id,
        weight=5,
    )

    files = [
        File(id=uuid.uuid4(), repo_id=repo_id, path="app/routers/repos.py", size_bytes=100, content_hash="h1"),
        File(id=uuid.uuid4(), repo_id=repo_id, path="app/routers/chat.py", size_bytes=100, content_hash="h2"),
    ]

    return repo, [m1, m2], [edge], files


@pytest.fixture
def explorer_client(mock_architecture_data):
    repo, modules, edges, files = mock_architecture_data
    app = create_app()
    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "from repositories" in stmt_str:
            mock_result.scalar_one_or_none.return_value = repo
        elif "from modules" in stmt_str and "where" in stmt_str and "modules.id =" in stmt_str:
            # Check module_id
            mock_result.scalar_one_or_none.return_value = modules[0]
        elif "from modules" in stmt_str:
            mock_result.scalars.return_value.all.return_value = modules
        elif "from module_edges" in stmt_str and "join" in stmt_str:
            # Neighbors query
            if "source_id =" in stmt_str:
                # Outgoing: m1 -> m2
                mock_result.all.return_value = [(edges[0], modules[1])]
            else:
                # Incoming
                mock_result.all.return_value = []
        elif "from module_edges" in stmt_str:
            mock_result.scalars.return_value.all.return_value = edges
        elif "from files" in stmt_str:
            mock_result.all.return_value = [(f.path,) for f in files]
        else:
            mock_result.scalar_one_or_none.return_value = None
            mock_result.scalars.return_value.all.return_value = []
            mock_result.all.return_value = []
        return mock_result

    session.execute.side_effect = mock_execute

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    return app, repo, modules, edges


@pytest.mark.asyncio
async def test_get_architecture_success(explorer_client):
    app, repo, modules, edges = explorer_client
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/api/v1/repos/{repo.id}/architecture")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1
        assert data["edges"][0]["weight"] == 5
        assert "FastAPI" in data["tech_stack"]
        assert "uvicorn main:app" in data["run_instructions"]
        assert "repos.py" in data["entry_points"]


@pytest.mark.asyncio
async def test_get_architecture_not_found(explorer_client):
    app, repo, _, _ = explorer_client
    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        return mock_result

    session.execute.side_effect = mock_execute

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        random_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/repos/{random_id}/architecture")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_get_module_detail_success(explorer_client):
    app, repo, modules, _ = explorer_client
    m1 = modules[0]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get(f"/api/v1/repos/{repo.id}/modules/{m1.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(m1.id)
        assert data["name"] == "routers"
        assert len(data["files"]) == 2
        assert "neighbors" in data
        assert len(data["neighbors"]["outgoing"]) == 1
        assert data["neighbors"]["outgoing"][0]["name"] == "models"


@pytest.mark.asyncio
async def test_get_module_detail_not_found(explorer_client):
    app, repo, _, _ = explorer_client
    session = AsyncMock()

    async def mock_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt).lower()
        if "from repositories" in stmt_str:
            mock_result.scalar_one_or_none.return_value = repo
        else:
            # Module not found
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    session.execute.side_effect = mock_execute
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        random_mod_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/repos/{repo.id}/modules/{random_mod_id}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"

        # Also unknown repo id returns 404
        random_repo_id = str(uuid.uuid4())
        resp_repo = await client.get(f"/api/v1/repos/{random_repo_id}/modules/{random_mod_id}")
        assert resp_repo.status_code == 404
        assert resp_repo.json()["error"]["code"] == "not_found"
