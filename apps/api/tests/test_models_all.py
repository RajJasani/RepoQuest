from sqlalchemy import UniqueConstraint

from app.models import Base


def test_metadata_contains_all_23_tables():
    expected_tables = {
        # Core 9
        "settings",
        "profiles",
        "repositories",
        "files",
        "chunks",
        "modules",
        "module_edges",
        "jobs",
        "audit_log",
        # Remaining 14
        "issues",
        "issue_analyses",
        "pull_requests",
        "pr_reviews",
        "spam_assessments",
        "chat_sessions",
        "chat_messages",
        "onboarding_paths",
        "onboarding_steps",
        "onboarding_progress",
        "benchmark_runs",
        "health_snapshots",
        "digests",
        "webhook_deliveries",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert len(actual_tables) == 23, f"Expected 23 tables, got {len(actual_tables)}: {actual_tables}"
    assert actual_tables == expected_tables, f"Mismatch: {actual_tables ^ expected_tables}"


def test_unique_constraints():
    tables = Base.metadata.tables

    # repositories: full_name is unique
    assert tables["repositories"].c.full_name.unique or any(
        "full_name" in [col.name for col in u.columns]
        for u in tables["repositories"].constraints
        if isinstance(u, UniqueConstraint)
    )

    # files: (repo_id, path)
    files_uniques = [
        tuple(col.name for col in u.columns)
        for u in tables["files"].constraints
        if isinstance(u, UniqueConstraint)
    ]
    assert ("repo_id", "path") in files_uniques

    # modules: (repo_id, path)
    modules_uniques = [
        tuple(col.name for col in u.columns)
        for u in tables["modules"].constraints
        if isinstance(u, UniqueConstraint)
    ]
    assert ("repo_id", "path") in modules_uniques

    # issues: (repo_id, number)
    issues_uniques = [
        tuple(col.name for col in u.columns)
        for u in tables["issues"].constraints
        if isinstance(u, UniqueConstraint)
    ]
    assert ("repo_id", "number") in issues_uniques

    # pull_requests: (repo_id, number)
    prs_uniques = [
        tuple(col.name for col in u.columns)
        for u in tables["pull_requests"].constraints
        if isinstance(u, UniqueConstraint)
    ]
    assert ("repo_id", "number") in prs_uniques

    # onboarding_paths: (repo_id, language)
    paths_uniques = [
        tuple(col.name for col in u.columns)
        for u in tables["onboarding_paths"].constraints
        if isinstance(u, UniqueConstraint)
    ]
    assert ("repo_id", "language") in paths_uniques

    # onboarding_steps: (path_id, position)
    steps_uniques = [
        tuple(col.name for col in u.columns)
        for u in tables["onboarding_steps"].constraints
        if isinstance(u, UniqueConstraint)
    ]
    assert ("path_id", "position") in steps_uniques

    # digests: (repo_id, week_start)
    digests_uniques = [
        tuple(col.name for col in u.columns)
        for u in tables["digests"].constraints
        if isinstance(u, UniqueConstraint)
    ]
    assert ("repo_id", "week_start") in digests_uniques


def test_foreign_keys_cascade():
    tables = Base.metadata.tables

    expected_cascades = [
        ("files", "repo_id", "repositories.id"),
        ("chunks", "repo_id", "repositories.id"),
        ("chunks", "file_id", "files.id"),
        ("modules", "repo_id", "repositories.id"),
        ("module_edges", "repo_id", "repositories.id"),
        ("module_edges", "source_id", "modules.id"),
        ("module_edges", "target_id", "modules.id"),
        ("issues", "repo_id", "repositories.id"),
        ("issue_analyses", "issue_id", "issues.id"),
        ("pull_requests", "repo_id", "repositories.id"),
        ("pr_reviews", "pr_id", "pull_requests.id"),
        ("spam_assessments", "pr_id", "pull_requests.id"),
        ("chat_sessions", "repo_id", "repositories.id"),
        ("chat_messages", "session_id", "chat_sessions.id"),
        ("onboarding_paths", "repo_id", "repositories.id"),
        ("onboarding_steps", "path_id", "onboarding_paths.id"),
        ("onboarding_progress", "profile_id", "profiles.id"),
        ("onboarding_progress", "step_id", "onboarding_steps.id"),
        ("health_snapshots", "repo_id", "repositories.id"),
        ("digests", "repo_id", "repositories.id"),
    ]

    for table_name, col_name, target in expected_cascades:
        col = tables[table_name].c[col_name]
        fk = next(fk for fk in col.foreign_keys)
        assert fk.target_fullname == target, f"{table_name}.{col_name} target is {fk.target_fullname}, expected {target}"
        assert fk.ondelete.upper() == "CASCADE", f"{table_name}.{col_name} ondelete is {fk.ondelete}, expected CASCADE"

    # audit_log.repo_id must have ON DELETE SET NULL
    audit_fk = next(fk for fk in tables["audit_log"].c.repo_id.foreign_keys)
    assert audit_fk.target_fullname == "repositories.id"
    assert audit_fk.ondelete.upper() == "SET NULL"


def test_cascade_delete_dependency_graph():
    """Verify that every repository child and grandchild table has CASCADE ondelete."""
    tables = Base.metadata.tables
    repo_table = tables["repositories"]

    # Direct children referencing repositories
    direct_children = set()
    for t_name, table in tables.items():
        if t_name == "repositories":
            continue
        for fk in table.foreign_keys:
            if fk.column.table == repo_table and fk.ondelete and fk.ondelete.upper() == "CASCADE":
                direct_children.add(t_name)

    expected_direct = {
        "files",
        "chunks",
        "modules",
        "module_edges",
        "issues",
        "pull_requests",
        "chat_sessions",
        "onboarding_paths",
        "health_snapshots",
        "digests",
    }
    assert expected_direct.issubset(direct_children)

    # Secondary children that cascade from direct children
    secondary_cascades = [
        ("issue_analyses", "issue_id", "issues.id"),
        ("pr_reviews", "pr_id", "pull_requests.id"),
        ("spam_assessments", "pr_id", "pull_requests.id"),
        ("chat_messages", "session_id", "chat_sessions.id"),
        ("onboarding_steps", "path_id", "onboarding_paths.id"),
        ("onboarding_progress", "step_id", "onboarding_steps.id"),
    ]
    for child, col, target in secondary_cascades:
        fk = next(fk for fk in tables[child].c[col].foreign_keys)
        assert fk.target_fullname == target
        assert fk.ondelete.upper() == "CASCADE"

