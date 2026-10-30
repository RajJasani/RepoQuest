from sqlalchemy import CheckConstraint

from app.models import (
    AuditLog,
    Base,
    Chunk,
    File,
    Job,
    Module,
    ModuleEdge,
    Profile,
    Repository,
    Setting,
)


def test_metadata_contains_exactly_9_tables():
    expected_tables = {
        "settings",
        "profiles",
        "repositories",
        "files",
        "chunks",
        "modules",
        "module_edges",
        "jobs",
        "audit_log",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert actual_tables == expected_tables, f"Mismatch: {actual_tables ^ expected_tables}"


def test_settings_columns_and_constraints():
    table = Setting.__table__
    expected_cols = {
        "id",
        "ollama_base_url",
        "chat_model",
        "embed_model",
        "triage_mode",
        "spam_threshold",
        "language",
        "offline_mode",
        "github_token_enc",
        "updated_at",
    }
    assert set(table.columns.keys()) == expected_cols

    checks = [c.sqltext.text for c in table.constraints if isinstance(c, CheckConstraint)]
    assert any("id = 1" in s for s in checks)
    assert any("triage_mode IN" in s for s in checks)
    assert any("spam_threshold BETWEEN" in s for s in checks)
    assert any("language IN" in s for s in checks)


def test_profiles_columns_and_constraints():
    table = Profile.__table__
    expected_cols = {"id", "display_name", "skills", "level"}
    assert set(table.columns.keys()) == expected_cols

    checks = [c.sqltext.text for c in table.constraints if isinstance(c, CheckConstraint)]
    assert any("level IN" in s for s in checks)


def test_repositories_columns_and_constraints():
    table = Repository.__table__
    expected_cols = {
        "id",
        "owner",
        "name",
        "full_name",
        "default_branch",
        "description",
        "stars",
        "languages",
        "tech_stack",
        "contributing_md",
        "readme_excerpt",
        "run_instructions",
        "status",
        "progress",
        "error",
        "last_indexed_at",
        "created_at",
    }
    assert set(table.columns.keys()) == expected_cols

    checks = [c.sqltext.text for c in table.constraints if isinstance(c, CheckConstraint)]
    assert any("status IN" in s for s in checks)


def test_files_columns_and_uniques():
    table = File.__table__
    expected_cols = {"id", "repo_id", "path", "language", "size_bytes", "content_hash", "summary"}
    assert set(table.columns.keys()) == expected_cols


def test_chunks_columns_and_indexes():
    table = Chunk.__table__
    expected_cols = {
        "id",
        "repo_id",
        "file_id",
        "chunk_index",
        "start_line",
        "end_line",
        "content",
        "content_hash",
        "embedding",
    }
    assert set(table.columns.keys()) == expected_cols

    idx_names = {idx.name for idx in table.indexes}
    assert "chunks_repo_idx" in idx_names
    assert "chunks_embedding_idx" in idx_names

    hnsw_idx = next(idx for idx in table.indexes if idx.name == "chunks_embedding_idx")
    assert hnsw_idx.dialect_options["postgresql"]["using"] == "hnsw"
    assert hnsw_idx.dialect_options["postgresql"]["ops"] == {"embedding": "vector_cosine_ops"}


def test_modules_and_edges():
    modules_table = Module.__table__
    expected_mod_cols = {
        "id",
        "repo_id",
        "path",
        "name",
        "summary",
        "key_files",
        "entry_points",
        "file_count",
    }
    assert set(modules_table.columns.keys()) == expected_mod_cols

    edges_table = ModuleEdge.__table__
    expected_edge_cols = {"repo_id", "source_id", "target_id", "weight"}
    assert set(edges_table.columns.keys()) == expected_edge_cols
    assert {c.name for c in edges_table.primary_key.columns} == {"source_id", "target_id"}


def test_jobs_columns_constraints_and_indexes():
    table = Job.__table__
    expected_cols = {
        "id",
        "kind",
        "payload",
        "status",
        "attempts",
        "error",
        "run_after",
        "created_at",
        "started_at",
        "finished_at",
    }
    assert set(table.columns.keys()) == expected_cols

    checks = [c.sqltext.text for c in table.constraints if isinstance(c, CheckConstraint)]
    assert any("status IN" in s for s in checks)

    idx_names = {idx.name for idx in table.indexes}
    assert "jobs_poll_idx" in idx_names


def test_audit_log_columns_and_indexes():
    table = AuditLog.__table__
    expected_cols = {
        "id",
        "ts",
        "feature",
        "repo_id",
        "ref_type",
        "ref_id",
        "action",
        "model",
        "prompt_version",
        "tokens_in",
        "tokens_out",
        "latency_ms",
        "outcome",
        "undo_payload",
        "undone",
    }
    assert set(table.columns.keys()) == expected_cols

    idx_names = {idx.name for idx in table.indexes}
    assert "audit_ts_idx" in idx_names
