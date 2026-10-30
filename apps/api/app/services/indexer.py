from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Optional
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_sessionmaker
from app.core.errors import GitHubError, NotFoundError, RateLimitedError
from app.core.security import decrypt_token
from app.models.core import Chunk, File, Repository, Setting
from app.models.features import Issue, PullRequest
from app.providers.base import LLMProvider
from app.providers.factory import get_provider
from app.services.archive import extract_tarball_safely
from app.services.chunker import chunk_file, compute_content_hash
from app.services.explorer import ExplorerService
from app.services.github import GitHubClient
from app.services.techdetect import (
    detect_languages_from_files,
    detect_tech_stack,
    extract_run_instructions,
)

logger = logging.getLogger("app.services.indexer")

WORKSPACE_BASE = Path("workspace").resolve()

# In-memory pub/sub for SSE progress events per repository ID
_progress_subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}


def subscribe_progress(repo_id: str) -> tuple[asyncio.Queue[dict[str, Any]], Any]:
    """Registers an SSE subscriber queue for a repository."""
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    if repo_id not in _progress_subscribers:
        _progress_subscribers[repo_id] = []
    _progress_subscribers[repo_id].append(queue)

    def unsubscribe() -> None:
        if repo_id in _progress_subscribers:
            if queue in _progress_subscribers[repo_id]:
                _progress_subscribers[repo_id].remove(queue)
            if not _progress_subscribers[repo_id]:
                del _progress_subscribers[repo_id]

    return queue, unsubscribe


async def broadcast_progress(repo_id: str, event_type: str, data: dict[str, Any]) -> None:
    """Broadcasts a progress, error, or done event to all active SSE subscribers."""
    queues = _progress_subscribers.get(repo_id, [])
    payload = {"event": event_type, "data": data}
    for q in queues:
        await q.put(payload)


class IndexerService:
    def __init__(
        self,
        sessionmaker: Optional[Any] = None,
        provider: Optional[LLMProvider] = None,
        github_client: Optional[GitHubClient] = None,
        workspace_dir: Optional[Path] = None,
    ):
        self.sessionmaker = sessionmaker or get_sessionmaker()
        self.provider = provider
        self.github_client = github_client
        self.workspace_dir = workspace_dir or WORKSPACE_BASE

    async def _update_repo_status(
        self,
        session: AsyncSession,
        repo: Repository,
        status: str,
        progress: int,
        message: str,
        error: Optional[str] = None,
    ) -> None:
        repo.status = status
        repo.progress = progress
        if error is not None:
            repo.error = error
        await session.commit()
        await session.refresh(repo)

        await broadcast_progress(
            str(repo.id),
            "progress",
            {"stage": status, "percent": progress, "message": message},
        )

    async def index_repository(
        self,
        repo_id: str,
        token_enc: Optional[str] = None,
    ) -> None:
        """
        Runs the 6-stage indexing pipeline:
        queued -> fetching -> chunking -> embedding -> summarizing -> ready.
        Idempotent via content_hash. Single-file failures are logged and skipped.
        """
        dest_dir = self.workspace_dir / repo_id
        dest_dir.mkdir(parents=True, exist_ok=True)

        async with self.sessionmaker() as session:
            stmt = select(Repository).where(Repository.id == uuid.UUID(repo_id))
            result = await session.execute(stmt)
            repo = result.scalar_one_or_none()
            if repo is None:
                logger.error("Repository %s not found for indexing", repo_id)
                return

            # Determine GitHub token
            token: Optional[str] = None
            if token_enc:
                try:
                    token = decrypt_token(token_enc)
                except Exception as exc:
                    logger.warning("Failed to decrypt provided token: %s", exc)

            if not token:
                # Check global settings
                stmt_s = select(Setting).where(Setting.id == 1)
                res_s = await session.execute(stmt_s)
                setting_row = res_s.scalar_one_or_none()
                if setting_row and setting_row.github_token_enc:
                    try:
                        token = decrypt_token(setting_row.github_token_enc)
                    except Exception as exc:
                        logger.warning("Failed to decrypt settings token: %s", exc)

            gh = self.github_client or GitHubClient(token=token)
            llm_provider = self.provider or await get_provider(session)

            try:
                # Stage 1: queued
                await self._update_repo_status(session, repo, "queued", 0, "Indexing queued")

                # Stage 2: fetching
                await self._update_repo_status(
                    session, repo, "fetching", 15, "Fetching repository metadata and snapshot from GitHub"
                )

                # Fetch metadata
                meta = await gh.get_repo(repo.owner, repo.name)
                repo.default_branch = meta.get("default_branch", "main")
                repo.description = meta.get("description")
                repo.stars = meta.get("stargazers_count", 0)

                # Download and extract tarball
                tarball_bytes = await gh.download_tarball(repo.owner, repo.name, ref=repo.default_branch)
                extract_tarball_safely(tarball_bytes, dest_dir)

                # Fetch labels, open issues and open PRs
                try:
                    labels_data = await gh.get_labels(repo.owner, repo.name)
                    repo.labels = [lbl["name"] for lbl in labels_data if isinstance(lbl, dict) and "name" in lbl]
                except Exception as exc:
                    logger.debug("Failed to fetch repository labels: %s", exc)

                issues_data = await gh.get_open_issues(repo.owner, repo.name)
                prs_data = await gh.get_open_pull_requests(repo.owner, repo.name)

                all_files: list[Path] = [p for p in dest_dir.rglob("*") if p.is_file()]
                file_records_to_save: list[tuple[File, list[Any]]] = []

                # Stage 3: chunking
                await self._update_repo_status(
                    session, repo, "chunking", 35, f"Scanning and chunking {len(all_files)} repository source files"
                )

                for fpath in all_files:
                    try:
                        rel_path = fpath.relative_to(dest_dir).as_posix()
                        raw_bytes = fpath.read_bytes()
                        content_str = raw_bytes.decode("utf-8", errors="replace")
                        file_hash = compute_content_hash(content_str)
                        file_lang = detect_languages_from_files([rel_path]).get("language")

                        file_obj = File(
                            repo_id=repo.id,
                            path=rel_path,
                            language=file_lang,
                            size_bytes=len(raw_bytes),
                            content_hash=file_hash,
                        )

                        chunks = chunk_file(content_str, filename=rel_path)
                        file_records_to_save.append((file_obj, chunks))
                    except Exception as exc:
                        # Single-file failures are logged and skipped
                        logger.warning("Skipping file %s due to processing failure: %s", fpath, exc)

                # Stage 4: embedding
                await self._update_repo_status(
                    session,
                    repo,
                    "embedding",
                    55,
                    f"Generating vector embeddings ({len(file_records_to_save)} files, {len(issues_data)} issues)",
                )

                # Fetch existing chunk embeddings for idempotency
                stmt_chunks = select(Chunk.content_hash, Chunk.embedding).where(
                    Chunk.repo_id == repo.id, Chunk.embedding.isnot(None)
                )
                res_chunks = await session.execute(stmt_chunks)
                existing_embeddings: dict[str, Any] = {row[0]: row[1] for row in res_chunks.all()}

                # Gather new chunks that need embedding
                all_chunk_objs: list[Chunk] = []
                chunks_to_embed: list[Chunk] = []
                texts_to_embed: list[str] = []

                # Remove old files/chunks for reindex to refresh file records
                await session.execute(delete(File).where(File.repo_id == repo.id))
                await session.flush()

                for file_obj, chunks in file_records_to_save:
                    session.add(file_obj)
                    await session.flush()  # populate file_obj.id

                    for c in chunks:
                        chunk_obj = Chunk(
                            repo_id=repo.id,
                            file_id=file_obj.id,
                            chunk_index=c.chunk_index,
                            start_line=c.start_line,
                            end_line=c.end_line,
                            content=c.content,
                            content_hash=c.content_hash,
                        )

                        # Idempotent re-index check: reuse existing embedding if content unchanged
                        if c.content_hash in existing_embeddings:
                            chunk_obj.embedding = existing_embeddings[c.content_hash]
                        else:
                            chunks_to_embed.append(chunk_obj)
                            texts_to_embed.append(c.content)

                        all_chunk_objs.append(chunk_obj)

                # Batch embed new chunks
                if texts_to_embed:
                    new_embeddings = await llm_provider.embed(texts_to_embed)
                    for chunk_obj, emb in zip(chunks_to_embed, new_embeddings):
                        chunk_obj.embedding = emb

                session.add_all(all_chunk_objs)

                # Embed issues for duplicate detection
                await session.execute(delete(Issue).where(Issue.repo_id == repo.id))
                await session.flush()

                issue_objs: list[Issue] = []
                issue_texts_to_embed: list[str] = []

                for idata in issues_data:
                    title = idata.get("title", "")
                    body = idata.get("body", "") or ""
                    combo_text = f"{title}\n{body}".strip()

                    created_gh = None
                    if idata.get("created_at"):
                        try:
                            created_gh = datetime.fromisoformat(idata["created_at"].replace("Z", "+00:00"))
                        except Exception:
                            pass

                    issue_obj = Issue(
                        repo_id=repo.id,
                        number=idata["number"],
                        title=title,
                        body=body,
                        state=idata.get("state", "open"),
                        author=idata.get("user", {}).get("login"),
                        labels=[lbl["name"] for lbl in idata.get("labels", []) if isinstance(lbl, dict)],
                        html_url=idata.get("html_url"),
                        created_at_gh=created_gh,
                        triage_status="untriaged",
                    )
                    issue_objs.append(issue_obj)
                    issue_texts_to_embed.append(combo_text)

                if issue_texts_to_embed:
                    issue_embeddings = await llm_provider.embed(issue_texts_to_embed)
                    for i_obj, emb in zip(issue_objs, issue_embeddings):
                        i_obj.embedding = emb

                session.add_all(issue_objs)

                # Save pull requests
                await session.execute(delete(PullRequest).where(PullRequest.repo_id == repo.id))
                await session.flush()

                pr_objs: list[PullRequest] = []
                for pdata in prs_data:
                    created_gh = None
                    if pdata.get("created_at"):
                        try:
                            created_gh = datetime.fromisoformat(pdata["created_at"].replace("Z", "+00:00"))
                        except Exception:
                            pass

                    pr_obj = PullRequest(
                        repo_id=repo.id,
                        number=pdata["number"],
                        title=pdata.get("title", ""),
                        body=pdata.get("body", ""),
                        state=pdata.get("state", "open"),
                        author=pdata.get("user", {}).get("login"),
                        html_url=pdata.get("html_url"),
                        created_at_gh=created_gh,
                    )
                    pr_objs.append(pr_obj)

                session.add_all(pr_objs)
                await session.flush()

                # Stage 5: summarizing
                await self._update_repo_status(
                    session, repo, "summarizing", 85, "Summarizing project tech stack, readme and instructions"
                )

                rel_paths = [f.relative_to(dest_dir).as_posix() for f in all_files]
                repo.languages = detect_languages_from_files(rel_paths)

                # Read manifests for tech stack detection
                manifest_names = {"package.json", "requirements.txt", "pyproject.toml", "pom.xml", "go.mod", "cargo.toml"}
                manifests: dict[str, str] = {}
                for f in all_files:
                    if f.name.lower() in manifest_names:
                        try:
                            manifests[f.name.lower()] = f.read_text(encoding="utf-8", errors="replace")
                        except Exception:
                            pass

                repo.tech_stack = detect_tech_stack(manifests)

                # Find CONTRIBUTING and README
                readme_text: Optional[str] = None
                for f in all_files:
                    fname = f.name.lower()
                    if fname.startswith("contributing"):
                        try:
                            repo.contributing_md = f.read_text(encoding="utf-8", errors="replace")
                        except Exception:
                            pass
                    elif fname.startswith("readme"):
                        try:
                            readme_text = f.read_text(encoding="utf-8", errors="replace")
                            repo.readme_excerpt = readme_text[:2000]
                        except Exception:
                            pass

                repo.run_instructions = extract_run_instructions(readme_content=readme_text, manifests=manifests)

                # Build architecture module graph and module summaries
                try:
                    explorer_svc = ExplorerService(provider=llm_provider)
                    await explorer_svc.build_and_save_module_graph(session, repo, dest_dir)
                except Exception as exc:
                    logger.warning("Failed to build module graph for %s: %s", repo.full_name, exc)

                # Stage 6: ready
                repo.status = "ready"
                repo.progress = 100
                repo.last_indexed_at = datetime.now(timezone.utc)
                repo.error = None
                await session.commit()

                ready_msg = (
                    f"Indexing complete: {len(file_records_to_save)} files, "
                    f"{len(all_chunk_objs)} chunks, {len(issue_objs)} issues indexed"
                )
                await broadcast_progress(
                    str(repo.id),
                    "progress",
                    {"stage": "ready", "percent": 100, "message": ready_msg},
                )
                await broadcast_progress(str(repo.id), "done", {"repo_id": str(repo.id)})

            except RateLimitedError:
                msg = "GitHub API rate limit exceeded. Please configure a GitHub token in settings or try again later."
                logger.error("Indexing failed for %s: %s", repo_id, msg)
                await self._fail_repo(session, repo, msg)
                raise
            except NotFoundError:
                msg = f"Repository {repo.full_name} not found or is private. If private, configure a GitHub token."
                logger.error("Indexing failed for %s: %s", repo_id, msg)
                await self._fail_repo(session, repo, msg)
                raise
            except GitHubError as exc:
                msg = f"GitHub API error: {exc.message}"
                logger.error("Indexing failed for %s: %s", repo_id, msg)
                await self._fail_repo(session, repo, msg)
                raise
            except Exception as exc:
                msg = f"Indexing failed unexpectedly: {exc}"
                logger.exception("Unexpected error during indexing of %s", repo_id)
                await self._fail_repo(session, repo, msg)
                raise

    async def _fail_repo(self, session: AsyncSession, repo: Repository, error_msg: str) -> None:
        repo.status = "failed"
        repo.error = error_msg
        await session.commit()
        await broadcast_progress(
            str(repo.id),
            "error",
            {"code": "indexing_failed", "message": error_msg},
        )
        await broadcast_progress(str(repo.id), "done", {"repo_id": str(repo.id)})
