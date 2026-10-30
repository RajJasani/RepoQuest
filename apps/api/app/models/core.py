import uuid
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, embedding_768, timestamptz_now, timestamptz_null, uuid_pk


class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="settings_id_check"),
        CheckConstraint("triage_mode IN ('suggest','auto')", name="settings_triage_mode_check"),
        CheckConstraint("spam_threshold BETWEEN 0 AND 100", name="settings_spam_threshold_check"),
        CheckConstraint("language IN ('en','hi','kn','ta')", name="settings_language_check"),
    )

    id: Mapped[int] = mapped_column(
        SmallInteger,
        primary_key=True,
        server_default=text("1"),
    )
    ollama_base_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'http://host.docker.internal:11434'"),
    )
    chat_model: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'gemma3:4b'"),
    )
    embed_model: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'nomic-embed-text'"),
    )
    triage_mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'suggest'"),
    )
    spam_threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("70"),
    )
    language: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'en'"),
    )
    offline_mode: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    github_token_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[timestamptz_now]


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (
        CheckConstraint("level IN ('beginner','intermediate')", name="profiles_level_check"),
    )

    id: Mapped[uuid_pk]
    display_name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'Contributor'"),
    )
    skills: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    level: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'beginner'"),
    )


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','fetching','chunking','embedding','summarizing','ready','failed')",
            name="repositories_status_check",
        ),
    )

    id: Mapped[uuid_pk]
    owner: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    default_branch: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'main'"),
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stars: Mapped[Optional[int]] = mapped_column(Integer, server_default=text("0"), nullable=True)
    languages: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        nullable=True,
    )
    tech_stack: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    labels: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    contributing_md: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    readme_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'queued'"),
    )
    progress: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_indexed_at: Mapped[timestamptz_null]
    created_at: Mapped[timestamptz_now]


class File(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("repo_id", "path", name="files_repo_id_path_key"),
    )

    id: Mapped[uuid_pk]
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("chunks_repo_idx", "repo_id"),
        Index(
            "chunks_embedding_idx",
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
    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[embedding_768]


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint("repo_id", "path", name="modules_repo_id_path_key"),
    )

    id: Mapped[uuid_pk]
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_files: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    entry_points: Mapped[Optional[Any]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        nullable=True,
    )
    file_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        server_default=text("0"),
        nullable=True,
    )


class ModuleEdge(Base):
    __tablename__ = "module_edges"

    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        primary_key=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        primary_key=True,
    )
    weight: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued','running','done','failed','cancelled')",
            name="jobs_status_check",
        ),
        Index("jobs_poll_idx", "status", "run_after"),
    )

    id: Mapped[uuid_pk]
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Any] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        server_default=text("'queued'"),
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    run_after: Mapped[timestamptz_now]
    created_at: Mapped[timestamptz_now]
    started_at: Mapped[timestamptz_null]
    finished_at: Mapped[timestamptz_null]


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        Index("audit_ts_idx", text("ts DESC")),
    )

    id: Mapped[uuid_pk]
    ts: Mapped[timestamptz_now]
    feature: Mapped[str] = mapped_column(Text, nullable=False)
    repo_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="SET NULL"),
        nullable=True,
    )
    ref_type: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ref_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tokens_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'ok'"))
    undo_payload: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    undone: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
