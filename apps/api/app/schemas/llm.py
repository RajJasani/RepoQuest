from typing import Any, Literal, Optional
from pydantic import BaseModel, Field


class Duplicate(BaseModel):
    number: int
    similarity: float
    reason: str


class TriageResult(BaseModel):
    type: Literal["bug", "feature", "question", "docs", "chore", "spam"]
    severity: Literal["P0", "P1", "P2", "P3"]
    labels: list[str] = Field(default_factory=list)
    summary: str
    missing_info: list[str] = Field(default_factory=list)
    duplicates: list[Duplicate] = Field(default_factory=list)
    good_first_issue_score: int = Field(ge=0, le=100)
    suggested_reply: str
    confidence: float = Field(ge=0.0, le=1.0)


class FileComment(BaseModel):
    file: str
    line_start: int
    line_end: int
    severity: Literal["info", "suggestion", "warning", "blocker"]
    comment: str
    suggestion: Optional[str] = None


class FileReview(BaseModel):
    file_comments: list[FileComment] = Field(default_factory=list)


class PRReview(BaseModel):
    summary: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"]
    risk_reasons: list[str] = Field(default_factory=list)
    checks: dict[str, Optional[bool]] = Field(default_factory=dict)
    file_comments: list[FileComment] = Field(default_factory=list)
    newcomer_explainer: str
    verdict: Literal["approve_ready", "needs_changes", "needs_discussion"]


class SpamLLMResult(BaseModel):
    meaningful_change: bool
    matches_description: bool
    looks_generic: bool
    reasons: list[str] = Field(default_factory=list)
    polite_comment: str


class IssueBrief(BaseModel):
    context: str
    files_to_touch: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    acceptance_checklist: list[str] = Field(default_factory=list)
    how_to_test: str
    difficulty: Literal["easy", "medium"]
    estimated_time: str


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(default_factory=list)
    correct_index: int
    explanation: str


class OnboardingStep(BaseModel):
    title: str
    goal: str
    files: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str
    quiz: list[QuizQuestion] = Field(default_factory=list)
    try_it: str


class OnboardingPath(BaseModel):
    title: str
    steps: list[OnboardingStep] = Field(default_factory=list)
