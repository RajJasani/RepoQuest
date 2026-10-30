"""initial core tables

Revision ID: 0001
Revises: None
Create Date: 2026-10-31 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # 2. settings
    op.create_table(
        "settings",
        sa.Column("id", sa.SmallInteger(), server_default=sa.text("1"), primary_key=True),
        sa.Column("ollama_base_url", sa.Text(), server_default=sa.text("'http://host.docker.internal:11434'"), nullable=False),
        sa.Column("chat_model", sa.Text(), server_default=sa.text("'gemma3:4b'"), nullable=False),
        sa.Column("embed_model", sa.Text(), server_default=sa.text("'nomic-embed-text'"), nullable=False),
        sa.Column("triage_mode", sa.Text(), server_default=sa.text("'suggest'"), nullable=False),
        sa.Column("spam_threshold", sa.Integer(), server_default=sa.text("70"), nullable=False),
        sa.Column("language", sa.Text(), server_default=sa.text("'en'"), nullable=False),
        sa.Column("offline_mode", sa.Boolean(), server_default=sa.text("TRUE"), nullable=False),
        sa.Column("github_token_enc", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("id = 1", name="settings_id_check"),
        sa.CheckConstraint("triage_mode IN ('suggest','auto')", name="settings_triage_mode_check"),
        sa.CheckConstraint("spam_threshold BETWEEN 0 AND 100", name="settings_spam_threshold_check"),
        sa.CheckConstraint("language IN ('en','hi','kn','ta')", name="settings_language_check"),
    )

    # 3. profiles
    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("display_name", sa.Text(), server_default=sa.text("'Contributor'"), nullable=False),
        sa.Column("skills", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("level", sa.Text(), server_default=sa.text("'beginner'"), nullable=False),
        sa.CheckConstraint("level IN ('beginner','intermediate')", name="profiles_level_check"),
    )

    # 4. repositories
    op.create_table(
        "repositories",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False, unique=True),
        sa.Column("default_branch", sa.Text(), server_default=sa.text("'main'"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("stars", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("languages", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=True),
        sa.Column("tech_stack", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("contributing_md", sa.Text(), nullable=True),
        sa.Column("readme_excerpt", sa.Text(), nullable=True),
        sa.Column("run_instructions", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("progress", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('queued','fetching','chunking','embedding','summarizing','ready','failed')",
            name="repositories_status_check",
        ),
    )

    # 5. files
    op.create_table(
        "files",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.UniqueConstraint("repo_id", "path", name="files_repo_id_path_key"),
    )

    # 6. chunks
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=True),
    )
    op.create_index("chunks_repo_idx", "chunks", ["repo_id"])
    op.create_index(
        "chunks_embedding_idx",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # 7. modules
    op.create_table(
        "modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("key_files", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("entry_points", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("file_count", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.UniqueConstraint("repo_id", "path", name="modules_repo_id_path_key"),
    )

    # 8. module_edges
    op.create_table(
        "module_edges",
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("weight", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )

    # 9. jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'queued'"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("run_after", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued','running','done','failed','cancelled')",
            name="jobs_status_check",
        ),
    )
    op.create_index("jobs_poll_idx", "jobs", ["status", "run_after"])

    # 10. audit_log
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ref_type", sa.Text(), nullable=True),
        sa.Column("ref_id", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("outcome", sa.Text(), server_default=sa.text("'ok'"), nullable=False),
        sa.Column("undo_payload", postgresql.JSONB(), nullable=True),
        sa.Column("undone", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
    )
    op.create_index("audit_ts_idx", "audit_log", [sa.text("ts DESC")])


def downgrade() -> None:
    op.drop_index("audit_ts_idx", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("jobs_poll_idx", table_name="jobs")
    op.drop_table("jobs")

    op.drop_table("module_edges")
    op.drop_table("modules")

    op.drop_index("chunks_embedding_idx", table_name="chunks", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"})
    op.drop_index("chunks_repo_idx", table_name="chunks")
    op.drop_table("chunks")

    op.drop_table("files")
    op.drop_table("repositories")
    op.drop_table("profiles")
    op.drop_table("settings")
