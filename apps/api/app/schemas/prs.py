from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class PRSyncResponse(BaseModel):
    synced_prs: int


class PRReviewResponse(BaseModel):
    id: str
    pr_id: str
    status: str
    summary: list[str] = Field(default_factory=list)
    risk_level: Optional[str] = None
    risk_reasons: list[str] = Field(default_factory=list)
    checks: dict[str, Optional[bool]] = Field(default_factory=dict)
    file_comments: list[dict[str, Any]] = Field(default_factory=list)
    newcomer_explainer: Optional[str] = None
    verdict: Optional[str] = None
    model: str
    prompt_version: str
    created_at: datetime


class SpamAssessmentResponse(BaseModel):
    id: str
    pr_id: str
    spam_score: int
    reasons: list[str] = Field(default_factory=list)
    rule_signals: dict[str, Any] = Field(default_factory=dict)
    recommended_action: Optional[str] = None
    polite_comment: Optional[str] = None
    created_at: datetime


class PRDetailResponse(BaseModel):
    id: str
    repo_id: str
    number: int
    title: str
    body: Optional[str] = None
    state: str
    author: Optional[str] = None
    author_is_first_time: bool = False
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    merged: bool = False
    html_url: Optional[str] = None
    head_sha: Optional[str] = None
    diff_hash: Optional[str] = None
    created_at_gh: Optional[datetime] = None
    updated_at_gh: Optional[datetime] = None
    latest_review: Optional[PRReviewResponse] = None
    latest_spam_assessment: Optional[SpamAssessmentResponse] = None


class PRListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PRDetailResponse] = Field(default_factory=list)


class PRPostReviewResponse(BaseModel):
    status: str
    review_id: str
