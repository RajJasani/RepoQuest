# Architecture & Design Decisions

## ADR 001: Store Repository Labels in `repositories.labels` (JSONB)

- **Date:** 2026-10-31
- **Status:** Accepted
- **Context:** PRD §6 (F2) requires issue triage to strictly whitelist suggested labels against the repository's existing labels (`labels never include a name that does not exist in the repo (enforced in code)`). However, the initial database schema (§10) did not provide a dedicated table or column for repository-level labels.
- **Decision:** Added a nullable `JSONB` column `labels` (server default `'[]'::jsonb`) to the `repositories` table via Alembic migration `0003_repo_labels.py`.
- **Consequences:**
  - Allowed repository labels are fetched from GitHub via `GET /repos/{owner}/{repo}/labels` during `POST /repos/{id}/issues/sync` (and initial indexing) and persisted in `repositories.labels`.
  - Triage logic and API endpoints can perform in-memory label whitelisting without issuing redundant outbound requests to GitHub on every triage run.
  - The database design remains simple and avoids an extra join table for labels in v1.
