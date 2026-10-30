from datetime import date
from typing import Any, Optional
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, embedding_768, timestamptz_now, timestamptz_null, uuid_pk


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        CheckConstraint(
            "triage_status IN ('untriaged','suggested','approved','applied','rejected','needs_human')",
            name="issues_triage_status_check",
        ),
        UniqueConstraint("repo_id", "number", name="issues_repo_id_number_key"),
        Index(
            "issues_embedding_idx",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[uuid_pk]
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    labels: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    html_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at_gh: Mapped[timestamptz_null]
    updated_at_gh: Mapped[timestamptz_null]
    first_response_at: Mapped[timestamptz_null]
    embedding: Mapped[embedding_768]
    triage_status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'untriaged'"),
    )


class IssueAnalysis(Base):
    __tablename__ = "issue_analyses"

    id: Mapped[uuid_pk]
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    labels: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    missing_info: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    duplicates: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    good_first_issue_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    suggested_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    brief: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[timestamptz_now]


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repo_id", "number", name="pull_requests_repo_id_number_key"),
    )

    id: Mapped[uuid_pk]
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author_is_first_time: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        server_default=text("FALSE"),
        nullable=True,
    )
    additions: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"), nullable=True)
    deletions: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"), nullable=True)
    changed_files: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"), nullable=True)
    merged: Mapped[Optional[bool]] = mapped_column(Boolean, server_default=text("FALSE"), nullable=True)
    html_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    head_sha: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diff_hash: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at_gh: Mapped[timestamptz_null]
    updated_at_gh: Mapped[timestamptz_null]


class PRReview(Base):
    __tablename__ = "pr_reviews"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','done','failed','posted')",
            name="pr_reviews_status_check",
        ),
    )

    id: Mapped[uuid_pk]
    pr_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'running'"),
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    checks: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=True,
    )
    file_comments: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    newcomer_explainer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verdict: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[timestamptz_now]


class SpamAssessment(Base):
    __tablename__ = "spam_assessments"
    __table_args__ = (
        CheckConstraint(
            "spam_score BETWEEN 0 AND 100",
            name="spam_assessments_spam_score_check",
        ),
    )

    id: Mapped[uuid_pk]
    pr_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    spam_score: Mapped[int] = mapped_column(Integer, nullable=False)
    reasons: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    rule_signals: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=True,
    )
    recommended_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    polite_comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[timestamptz_now]


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        CheckConstraint(
            "mode IN ('newcomer','expert')",
            name="chat_sessions_mode_check",
        ),
    )

    id: Mapped[uuid_pk]
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'newcomer'"),
    )
    language: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'en'"),
    )
    created_at: Mapped[timestamptz_now]


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user','assistant')",
            name="chat_messages_role_check",
        ),
    )

    id: Mapped[uuid_pk]
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    created_at: Mapped[timestamptz_now]


class OnboardingPath(Base):
    __tablename__ = "onboarding_paths"
    __table_args__ = (
        UniqueConstraint("repo_id", "language", name="onboarding_paths_repo_id_language_key"),
    )

    id: Mapped[uuid_pk]
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'en'"),
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[timestamptz_now]


class OnboardingStep(Base):
    __tablename__ = "onboarding_steps"
    __table_args__ = (
        UniqueConstraint("path_id", "position", name="onboarding_steps_path_id_position_key"),
    )

    id: Mapped[uuid_pk]
    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("onboarding_paths.id", ondelete="CASCADE"),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    files: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    quiz: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    try_it: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class OnboardingProgress(Base):
    __tablename__ = "onboarding_progress"

    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("onboarding_steps.id", ondelete="CASCADE"),
        primary_key=True,
    )
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    quiz_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[timestamptz_null]


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running','done','failed','cancelled')",
            name="benchmark_runs_status_check",
        ),
    )

    id: Mapped[uuid_pk]
    model: Mapped[str] = mapped_column(Text, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False)
    type_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    severity_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    json_valid_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_per_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    details: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'running'"),
    )
    created_at: Mapped[timestamptz_now]


class HealthSnapshot(Base):
    __tablename__ = "health_snapshots"
    __table_args__ = (
        CheckConstraint(
            "load_index BETWEEN 0 AND 100",
            name="health_snapshots_load_index_check",
        ),
    )

    id: Mapped[uuid_pk]
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    taken_at: Mapped[timestamptz_now]
    metrics: Mapped[Any] = mapped_column(JSONB, nullable=False)
    load_index: Mapped[int] = mapped_column(Integer, nullable=False)


class Digest(Base):
    __tablename__ = "digests"
    __table_args__ = (
        UniqueConstraint("repo_id", "week_start", name="digests_repo_id_week_start_key"),
    )

    id: Mapped[uuid_pk]
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[timestamptz_now]


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    delivery_id: Mapped[str] = mapped_column(Text, primary_key=True)
    event: Mapped[str] = mapped_column(Text, nullable=False)
    received_at: Mapped[timestamptz_now]
