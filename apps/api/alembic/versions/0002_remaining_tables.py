"""remaining tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31 03:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. issues
    op.create_table(
        "issues",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("labels", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("html_url", sa.Text(), nullable=True),
        sa.Column("created_at_gh", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at_gh", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("triage_status", sa.Text(), server_default=sa.text("'untriaged'"), nullable=False),
        sa.CheckConstraint(
            "triage_status IN ('untriaged','suggested','approved','applied','rejected','needs_human')",
            name="issues_triage_status_check",
        ),
        sa.UniqueConstraint("repo_id", "number", name="issues_repo_id_number_key"),
    )
    op.create_index(
        "issues_embedding_idx",
        "issues",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    # 2. issue_analyses
    op.create_table(
        "issue_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("issue_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("issues.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True),
        sa.Column("labels", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("missing_info", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("duplicates", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("good_first_issue_score", sa.Integer(), nullable=True),
        sa.Column("suggested_reply", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("brief", postgresql.JSONB(), nullable=True),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 3. pull_requests
    op.create_table(
        "pull_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("author_is_first_time", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True),
        sa.Column("additions", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("deletions", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("changed_files", sa.Integer(), server_default=sa.text("0"), nullable=True),
        sa.Column("merged", sa.Boolean(), server_default=sa.text("FALSE"), nullable=True),
        sa.Column("html_url", sa.Text(), nullable=True),
        sa.Column("head_sha", sa.Text(), nullable=True),
        sa.Column("diff_hash", sa.Text(), nullable=True),
        sa.Column("created_at_gh", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at_gh", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("repo_id", "number", name="pull_requests_repo_id_number_key"),
    )

    # 4. pr_reviews
    op.create_table(
        "pr_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("pr_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'running'"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.Text(), nullable=True),
        sa.Column("checks", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=True),
        sa.Column("file_comments", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("newcomer_explainer", sa.Text(), nullable=True),
        sa.Column("verdict", sa.Text(), nullable=True),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('running','done','failed','posted')",
            name="pr_reviews_status_check",
        ),
    )

    # 5. spam_assessments
    op.create_table(
        "spam_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("pr_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("spam_score", sa.Integer(), nullable=False),
        sa.Column("reasons", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("rule_signals", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("polite_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "spam_score BETWEEN 0 AND 100",
            name="spam_assessments_spam_score_check",
        ),
    )

    # 6. chat_sessions
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.Text(), server_default=sa.text("'newcomer'"), nullable=False),
        sa.Column("language", sa.Text(), server_default=sa.text("'en'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "mode IN ('newcomer','expert')",
            name="chat_sessions_mode_check",
        ),
    )

    # 7. chat_messages
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "role IN ('user','assistant')",
            name="chat_messages_role_check",
        ),
    )

    # 8. onboarding_paths
    op.create_table(
        "onboarding_paths",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("language", sa.Text(), server_default=sa.text("'en'"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("repo_id", "language", name="onboarding_paths_repo_id_language_key"),
    )

    # 9. onboarding_steps
    op.create_table(
        "onboarding_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("path_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("onboarding_paths.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("files", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("quiz", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=True),
        sa.Column("try_it", sa.Text(), nullable=True),
        sa.UniqueConstraint("path_id", "position", name="onboarding_steps_path_id_position_key"),
    )

    # 10. onboarding_progress
    op.create_table(
        "onboarding_progress",
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("step_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("onboarding_steps.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("completed", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False),
        sa.Column("quiz_score", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 11. benchmark_runs
    op.create_table(
        "benchmark_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("type_accuracy", sa.Float(), nullable=True),
        sa.Column("severity_accuracy", sa.Float(), nullable=True),
        sa.Column("json_valid_rate", sa.Float(), nullable=True),
        sa.Column("avg_latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_per_sec", sa.Float(), nullable=True),
        sa.Column("details", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'running'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('running','done','failed','cancelled')",
            name="benchmark_runs_status_check",
        ),
    )

    # 12. health_snapshots
    op.create_table(
        "health_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("taken_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("load_index", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "load_index BETWEEN 0 AND 100",
            name="health_snapshots_load_index_check",
        ),
    )

    # 13. digests
    op.create_table(
        "digests",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("repo_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("repo_id", "week_start", name="digests_repo_id_week_start_key"),
    )

    # 14. webhook_deliveries
    op.create_table(
        "webhook_deliveries",
        sa.Column("delivery_id", sa.Text(), primary_key=True),
        sa.Column("event", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("digests")
    op.drop_table("health_snapshots")
    op.drop_table("benchmark_runs")
    op.drop_table("onboarding_progress")
    op.drop_table("onboarding_steps")
    op.drop_table("onboarding_paths")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("spam_assessments")
    op.drop_table("pr_reviews")
    op.drop_table("pull_requests")
    op.drop_table("issue_analyses")
    op.drop_index("issues_embedding_idx", table_name="issues", postgresql_using="hnsw", postgresql_ops={"embedding": "vector_cosine_ops"})
    op.drop_table("issues")
