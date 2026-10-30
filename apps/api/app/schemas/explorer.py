from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ArchitectureNode(BaseModel):
    id: str
    name: str
    path: str
    summary: Optional[str] = None
    key_files: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    file_count: int = 0


class ArchitectureEdge(BaseModel):
    source: str
    target: str
    weight: int = 1


class ArchitectureResponse(BaseModel):
    nodes: list[ArchitectureNode] = Field(default_factory=list)
    edges: list[ArchitectureEdge] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    run_instructions: Optional[str] = None
    entry_points: list[str] = Field(default_factory=list)


class NeighborNode(BaseModel):
    id: str
    name: str
    path: str
    weight: int = 1


class ModuleNeighbors(BaseModel):
    incoming: list[NeighborNode] = Field(default_factory=list)
    outgoing: list[NeighborNode] = Field(default_factory=list)


class ModuleDetailResponse(BaseModel):
    id: str
    repo_id: str
    name: str
    path: str
    summary: Optional[str] = None
    key_files: list[str] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    file_count: int = 0
    files: list[str] = Field(default_factory=list)
    neighbors: ModuleNeighbors = Field(default_factory=ModuleNeighbors)
