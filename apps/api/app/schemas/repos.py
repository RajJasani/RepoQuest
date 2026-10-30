from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class RepoCreateRequest(BaseModel):
    url: str
    token: Optional[str] = None


class RepoCreateResponse(BaseModel):
    repo_id: str
    job_id: str


class RepoSummaryResponse(BaseModel):
    id: str
    owner: str
    name: str
    full_name: str
    default_branch: str
    description: Optional[str] = None
    stars: Optional[int] = 0
    status: str
    progress: int
    error: Optional[str] = None
    last_indexed_at: Optional[datetime] = None
    created_at: datetime


class RepoDetailResponse(RepoSummaryResponse):
    languages: Optional[dict[str, Any]] = Field(default_factory=dict)
    tech_stack: Optional[list[str]] = Field(default_factory=list)
    contributing_md: Optional[str] = None
    readme_excerpt: Optional[str] = None
    run_instructions: Optional[str] = None
    file_count: Optional[int] = 0


class FileContentResponse(BaseModel):
    path: str
    content: str
    total_lines: int
    start_line: int
    end_line: int


class TreeNode(BaseModel):
    name: str
    path: str
    type: str  # "directory" | "file"
    size_bytes: Optional[int] = None
    language: Optional[str] = None
    children: Optional[list[TreeNode]] = None


TreeNode.model_rebuild()
