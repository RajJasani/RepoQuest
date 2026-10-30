from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class IssueSyncResponse(BaseModel):
    synced_issues: int
    labels_count: int


class IssueAnalysisResponse(BaseModel):
    id: str
    type: Optional[str] = None
    severity: Optional[str] = None
    labels: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    missing_info: list[str] = Field(default_factory=list)
    duplicates: list[dict[str, Any]] = Field(default_factory=list)
    good_first_issue_score: Optional[int] = None
    suggested_reply: Optional[str] = None
    confidence: Optional[float] = None
    model: str
    prompt_version: str
    created_at: datetime


class IssueDetailResponse(BaseModel):
    id: str
    repo_id: str
    number: int
    title: str
    body: Optional[str] = None
    state: str
    author: Optional[str] = None
    labels: list[str] = Field(default_factory=list)
    html_url: Optional[str] = None
    triage_status: str
    created_at_gh: Optional[datetime] = None
    analysis: Optional[IssueAnalysisResponse] = None


class IssueListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[IssueDetailResponse] = Field(default_factory=list)


class IssueApproveRequest(BaseModel):
    labels: Optional[list[str]] = None
    comment: Optional[str] = None
    post_to_github: bool = False


class IssueApproveResponse(BaseModel):
    status: str
    issue_id: str
    labels: list[str] = Field(default_factory=list)
    comment: Optional[str] = None
    posted_to_github: bool = False


class IssueTriageEnqueueResponse(BaseModel):
    issue_id: str
    job_id: str
