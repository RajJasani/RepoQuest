from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.core import File, Module, ModuleEdge, Repository
from app.schemas.explorer import (
    ArchitectureEdge,
    ArchitectureNode,
    ArchitectureResponse,
    ModuleDetailResponse,
    ModuleNeighbors,
    NeighborNode,
)

logger = logging.getLogger("app.routers.explorer")

router = APIRouter(prefix="/repos", tags=["explorer"])


@router.get("/{id}/architecture", response_model=ArchitectureResponse)
async def get_repo_architecture(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> ArchitectureResponse:
    """Returns the architectural module graph, tech stack, run instructions, and entry points."""
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    stmt_repo = select(Repository).where(Repository.id == repo_uuid)
    res_repo = await db.execute(stmt_repo)
    repo = res_repo.scalar_one_or_none()
    if repo is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    # Fetch modules
    stmt_modules = select(Module).where(Module.repo_id == repo_uuid).order_by(Module.path.asc())
    res_modules = await db.execute(stmt_modules)
    modules = res_modules.scalars().all()

    # Fetch edges
    stmt_edges = select(ModuleEdge).where(ModuleEdge.repo_id == repo_uuid)
    res_edges = await db.execute(stmt_edges)
    edges = res_edges.scalars().all()

    # Aggregate all entry points
    all_entry_points: list[str] = []
    nodes: list[ArchitectureNode] = []
    for m in modules:
        entry_pts = m.entry_points or []
        for ep in entry_pts:
            if ep not in all_entry_points:
                all_entry_points.append(ep)
        nodes.append(
            ArchitectureNode(
                id=str(m.id),
                name=m.name,
                path=m.path,
                summary=m.summary,
                key_files=m.key_files or [],
                entry_points=entry_pts,
                file_count=m.file_count or 0,
            )
        )

    return ArchitectureResponse(
        nodes=nodes,
        edges=[
            ArchitectureEdge(
                source=str(e.source_id),
                target=str(e.target_id),
                weight=e.weight,
            )
            for e in edges
        ],
        tech_stack=repo.tech_stack or [],
        run_instructions=repo.run_instructions,
        entry_points=sorted(all_entry_points),
    )


@router.get("/{id}/modules/{module_id}", response_model=ModuleDetailResponse)
async def get_module_detail(
    id: str,
    module_id: str,
    db: AsyncSession = Depends(get_db),
) -> ModuleDetailResponse:
    """Returns detailed information for a module including its files and incoming/outgoing neighbors."""
    try:
        repo_uuid = uuid.UUID(id)
        mod_uuid = uuid.UUID(module_id)
    except ValueError:
        raise NotFoundError("Invalid repository or module ID format.")

    # Verify repository exists
    stmt_repo = select(Repository.id).where(Repository.id == repo_uuid)
    res_repo = await db.execute(stmt_repo)
    if res_repo.scalar_one_or_none() is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    # Fetch module
    stmt_mod = select(Module).where(Module.id == mod_uuid, Module.repo_id == repo_uuid)
    res_mod = await db.execute(stmt_mod)
    module = res_mod.scalar_one_or_none()
    if module is None:
        raise NotFoundError(f"Module '{module_id}' not found.")

    # Fetch files belonging to this module
    if module.path == ".":
        # Root files: no slash in path
        stmt_files = select(File.path).where(File.repo_id == repo_uuid)
    else:
        prefix = f"{module.path}/"
        stmt_files = select(File.path).where(
            File.repo_id == repo_uuid,
            or_(File.path == module.path, File.path.startswith(prefix)),
        )

    res_files = await db.execute(stmt_files)
    all_matched_files = [row[0] for row in res_files.all()]
    if module.path == ".":
        # Keep only files in root
        all_matched_files = [p for p in all_matched_files if "/" not in p]

    # Fetch neighbors
    # Outgoing edges: module imports others
    stmt_outgoing = (
        select(ModuleEdge, Module)
        .join(Module, ModuleEdge.target_id == Module.id)
        .where(ModuleEdge.source_id == mod_uuid, ModuleEdge.repo_id == repo_uuid)
    )
    res_outgoing = await db.execute(stmt_outgoing)
    outgoing_neighbors = [
        NeighborNode(
            id=str(target_mod.id),
            name=target_mod.name,
            path=target_mod.path,
            weight=edge.weight,
        )
        for edge, target_mod in res_outgoing.all()
    ]

    # Incoming edges: others import this module
    stmt_incoming = (
        select(ModuleEdge, Module)
        .join(Module, ModuleEdge.source_id == Module.id)
        .where(ModuleEdge.target_id == mod_uuid, ModuleEdge.repo_id == repo_uuid)
    )
    res_incoming = await db.execute(stmt_incoming)
    incoming_neighbors = [
        NeighborNode(
            id=str(source_mod.id),
            name=source_mod.name,
            path=source_mod.path,
            weight=edge.weight,
        )
        for edge, source_mod in res_incoming.all()
    ]

    return ModuleDetailResponse(
        id=str(module.id),
        repo_id=str(module.repo_id),
        name=module.name,
        path=module.path,
        summary=module.summary,
        key_files=module.key_files or [],
        entry_points=module.entry_points or [],
        file_count=module.file_count or len(all_matched_files),
        files=sorted(all_matched_files),
        neighbors=ModuleNeighbors(
            incoming=incoming_neighbors,
            outgoing=outgoing_neighbors,
        ),
    )
