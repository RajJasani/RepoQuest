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

## ADR 002: Simulated GitHub Writes for Demo Repository (`demo/*`)

- **Date:** 2026-10-31
- **Status:** Accepted
- **Context:** PRD §17.3 requires Demo Mode to function 100% offline without internet access or GitHub rate limits. Actions modifying issues or pull requests (e.g. applying triage labels, posting comments, submitting PR reviews) must not fail due to a missing GitHub token or network unavailability.
- **Decision:** When a repository owner is `demo` (e.g., `demo/taskboard`), `GitHubClient` intercepts all outbound write requests (`post_issue_comment`, `add_labels`, `remove_label`, `create_pull_request_review`) without calling `api.github.com`. It returns a simulated response describing the exact HTTP request that would have been dispatched. The action marks the item as `Applied (demo)` in the API response while keeping the underlying database status valid per constraint rules (`applied` / `posted`).
- **Consequences:**
  - Demo mode works completely offline with zero network calls and no GitHub token requirement.
  - Maintainers and judges can test approving triage recommendations or posting PR reviews interactively during live evaluations.
  - Audit logs record simulated actions accurately with `simulated: True` in undo payloads.

## ADR 003: Model Recommendation Endpoint (`GET /api/v1/models/recommend`)

- **Date:** 2026-10-31
- **Status:** Accepted
- **Context:** PRD §6 F9 specifies a "Recommend a model" helper in Model Lab that maps user-provided system RAM to a sensible model size. While the table in §11 only listed `GET /models`, a dedicated helper endpoint was needed to provide deterministic, rule-based recommendations for the frontend UI.
- **Decision:** Added `GET /api/v1/models/recommend?ram_gb=<float>` to the `system` router. It categorizes host RAM:
  - `< 8 GB`: 1B-2B models (e.g., `qwen2.5:1.5b`)
  - `8 - 15.9 GB`: 3B-4B models (e.g., `gemma3:4b`, `llama3.2:3b`)
  - `16 - 31.9 GB`: 7B-9B models (e.g., `qwen2.5:7b`, `llama3.1:8b`)
  - `>= 32 GB`: 14B-32B models (e.g., `qwen2.5:14b`)
- **Consequences:**
  - The UI setup wizard and Model Lab can query recommended model parameters instantly without LLM latency.
  - Aligns with the hardware guide in PRD §15 (8 GB minimum for 3-4B models, 16 GB recommended).



