from __future__ import annotations

import asyncio
import json
import logging
import shutil
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.core.db import get_db
from app.core.errors import ConflictError, NotFoundError
from app.core.security import encrypt_token
from app.models.core import File, Job, Repository
from app.schemas.repos import (
    FileContentResponse,
    RepoCreateRequest,
    RepoCreateResponse,
    RepoDetailResponse,
    RepoSummaryResponse,
    TreeNode,
)
from app.services.github import validate_github_repo_url
from app.services.indexer import WORKSPACE_BASE, subscribe_progress

logger = logging.getLogger("app.routers.repos")

router = APIRouter(prefix="/repos", tags=["repos"])


def build_file_tree(files: list[File]) -> list[dict[str, Any]]:
    """Builds a hierarchical nested directory tree from a flat list of File records."""
    root: dict[str, Any] = {}
    for f in sorted(files, key=lambda x: x.path):
        parts = f.path.split("/")
        current = root
        curr_path = ""
        for i, part in enumerate(parts):
            curr_path = f"{curr_path}/{part}" if curr_path else part
            if i == len(parts) - 1:
                current[part] = {
                    "name": part,
                    "path": f.path,
                    "type": "file",
                    "size_bytes": f.size_bytes,
                    "language": f.language,
                }
            else:
                if part not in current:
                    current[part] = {
                        "name": part,
                        "path": curr_path,
                        "type": "directory",
                        "_children": {},
                    }
                current = current[part]["_children"]

    def _convert(children_dict: dict[str, Any]) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []
        for val in children_dict.values():
            if val["type"] == "directory":
                children = _convert(val.pop("_children", {}))
                val["children"] = children
            nodes.append(val)
        # Sort directories first, then files alphabetically
        nodes.sort(key=lambda n: (0 if n["type"] == "directory" else 1, n["name"].lower()))
        return nodes

    return _convert(root)


@router.post("", response_model=RepoCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_repo(
    payload: RepoCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> RepoCreateResponse:
    """Connects and enqueues indexing for a GitHub repository."""
    owner, repo_name = validate_github_repo_url(payload.url)
    full_name = f"{owner}/{repo_name}"

    # Check if repository already exists
    stmt_check = select(Repository).where(Repository.full_name == full_name)
    res_check = await db.execute(stmt_check)
    existing = res_check.scalar_one_or_none()
    if existing:
        raise ConflictError(
            f"Repository '{full_name}' is already connected.",
            details={"repo_id": str(existing.id), "full_name": full_name},
        )

    # Encrypt token if provided
    token_enc: Optional[str] = None
    if payload.token:
        token_enc = encrypt_token(payload.token.strip())

    # Create Repository record
    repo = Repository(
        owner=owner,
        name=repo_name,
        full_name=full_name,
        status="queued",
        progress=0,
    )
    db.add(repo)
    await db.flush()

    # Create Job record
    job = Job(
        kind="index_repo",
        payload={"repo_id": str(repo.id), "token_enc": token_enc},
        status="queued",
    )
    db.add(job)
    await db.commit()

    return RepoCreateResponse(
        repo_id=str(repo.id),
        job_id=str(job.id),
    )


@router.get("", response_model=list[RepoSummaryResponse])
async def list_repos(
    db: AsyncSession = Depends(get_db),
) -> list[RepoSummaryResponse]:
    """Lists all connected repositories."""
    stmt = select(Repository).order_by(Repository.created_at.desc())
    res = await db.execute(stmt)
    repos = res.scalars().all()
    return [
        RepoSummaryResponse(
            id=str(r.id),
            owner=r.owner,
            name=r.name,
            full_name=r.full_name,
            default_branch=r.default_branch,
            description=r.description,
            stars=r.stars or 0,
            status=r.status,
            progress=r.progress,
            error=r.error,
            last_indexed_at=r.last_indexed_at,
            created_at=r.created_at,
        )
        for r in repos
    ]


@router.get("/{id}", response_model=RepoDetailResponse)
async def get_repo(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> RepoDetailResponse:
    """Returns repository details including language breakdown, tech stack and file count."""
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    stmt = select(Repository).where(Repository.id == repo_uuid)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if repo is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    # Count files
    stmt_count = select(func.count(File.id)).where(File.repo_id == repo_uuid)
    res_count = await db.execute(stmt_count)
    file_count = res_count.scalar() or 0

    return RepoDetailResponse(
        id=str(repo.id),
        owner=repo.owner,
        name=repo.name,
        full_name=repo.full_name,
        default_branch=repo.default_branch,
        description=repo.description,
        stars=repo.stars or 0,
        status=repo.status,
        progress=repo.progress,
        error=repo.error,
        last_indexed_at=repo.last_indexed_at,
        created_at=repo.created_at,
        languages=repo.languages or {},
        tech_stack=repo.tech_stack or [],
        contributing_md=repo.contributing_md,
        readme_excerpt=repo.readme_excerpt,
        run_instructions=repo.run_instructions,
        file_count=file_count,
    )


@router.delete("/{id}")
async def delete_repo(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Deletes a repository, cascading to files, chunks, issues and workspace snapshot."""
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    stmt = select(Repository).where(Repository.id == repo_uuid)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if repo is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    await db.delete(repo)
    await db.commit()

    # Clean up workspace
    repo_workspace = WORKSPACE_BASE / str(repo_uuid)
    if repo_workspace.exists():
        shutil.rmtree(repo_workspace, ignore_errors=True)

    return {"status": "deleted", "id": str(repo_uuid)}


@router.post("/{id}/reindex", response_model=RepoCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def reindex_repo(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> RepoCreateResponse:
    """Enqueues re-indexing for an existing repository (idempotent via content hash)."""
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    stmt = select(Repository).where(Repository.id == repo_uuid)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if repo is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    repo.status = "queued"
    repo.progress = 0
    repo.error = None

    job = Job(
        kind="index_repo",
        payload={"repo_id": str(repo.id)},
        status="queued",
    )
    db.add(job)
    await db.commit()

    return RepoCreateResponse(
        repo_id=str(repo.id),
        job_id=str(job.id),
    )


@router.get("/{id}/progress")
async def get_repo_progress(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Streams indexing progress via Server-Sent Events.
    Events: progress, error, done. Sends ': ping' comment every 15 seconds.
    Resumable on refresh; stops when client disconnects.
    """
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    stmt = select(Repository).where(Repository.id == repo_uuid)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if repo is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    initial_status = repo.status
    initial_progress = repo.progress
    initial_error = repo.error

    async def event_generator():
        # If terminal state, emit immediately and terminate
        if initial_status == "ready":
            yield {
                "event": "progress",
                "data": json.dumps({"stage": "ready", "percent": 100, "message": "Repository indexing complete"}),
            }
            yield {"event": "done", "data": json.dumps({"repo_id": str(repo_uuid)})}
            return

        if initial_status == "failed":
            yield {
                "event": "error",
                "data": json.dumps({"code": "indexing_failed", "message": initial_error or "Indexing failed"}),
            }
            yield {"event": "done", "data": json.dumps({"repo_id": str(repo_uuid)})}
            return

        # Emit current in-progress state first for resumability
        yield {
            "event": "progress",
            "data": json.dumps({
                "stage": initial_status,
                "percent": initial_progress,
                "message": f"Indexing in progress: {initial_status}",
            }),
        }

        # Subscribe to new live events
        queue, unsubscribe = subscribe_progress(str(repo_uuid))
        try:
            while True:
                if await request.is_disconnected():
                    break

                try:
                    event_payload = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield {
                        "event": event_payload["event"],
                        "data": json.dumps(event_payload["data"]),
                    }
                    if event_payload["event"] == "done":
                        break
                except asyncio.TimeoutError:
                    continue
        finally:
            unsubscribe()

    return EventSourceResponse(
        event_generator(),
        ping=15,
        ping_message_factory=lambda: ServerSentEvent(comment="ping"),
    )


@router.get("/{id}/tree", response_model=list[TreeNode])
async def get_repo_tree(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> list[TreeNode]:
    """Returns the nested directory and file tree of the indexed repository."""
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    stmt_repo = select(Repository.id).where(Repository.id == repo_uuid)
    res_repo = await db.execute(stmt_repo)
    if res_repo.scalar_one_or_none() is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    stmt = select(File).where(File.repo_id == repo_uuid)
    res = await db.execute(stmt)
    files = list(res.scalars().all())

    tree_nodes = build_file_tree(files)
    return [TreeNode.model_validate(node) for node in tree_nodes]


@router.get("/{id}/files", response_model=FileContentResponse)
async def get_repo_file(
    id: str,
    path: str = Query(..., description="File path relative to repository root"),
    start: Optional[int] = Query(None, ge=1, description="Start line (1-based)"),
    end: Optional[int] = Query(None, ge=1, description="End line (1-based)"),
    db: AsyncSession = Depends(get_db),
) -> FileContentResponse:
    """
    Returns file content with optional line slicing for the code viewer.
    Serves ONLY paths present in the files table; anything else is 404.
    """
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    # Serve only paths present in the files table; anything else is 404
    stmt = select(File).where(File.repo_id == repo_uuid, File.path == path)
    res = await db.execute(stmt)
    file_record = res.scalar_one_or_none()
    if file_record is None:
        raise NotFoundError(f"File '{path}' not found in repository.")

    # Safe filesystem path resolution
    workspace_dir = WORKSPACE_BASE / str(repo_uuid)
    full_path = (workspace_dir / path).resolve()
    if not full_path.is_relative_to(workspace_dir) or not full_path.is_file():
        raise NotFoundError(f"File '{path}' not found on disk.")

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        raise NotFoundError(f"Could not read file '{path}': {exc}")

    lines = content.splitlines()
    total_lines = len(lines)
    if total_lines == 0:
        return FileContentResponse(
            path=path,
            content="",
            total_lines=0,
            start_line=1,
            end_line=0,
        )

    s = max(1, start) if start else 1
    e = min(total_lines, end) if end else total_lines
    if s > e:
        sliced_content = ""
    else:
        sliced_content = "\n".join(lines[s - 1 : e])

    return FileContentResponse(
        path=path,
        content=sliced_content,
        total_lines=total_lines,
        start_line=s,
        end_line=e,
    )
