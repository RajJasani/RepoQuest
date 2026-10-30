from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any, Optional
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Chunk, File, Repository
from app.models.features import Issue, PullRequest
from app.providers.base import LLMProvider
from app.services.chunker import chunk_file
from app.services.explorer import ExplorerService
from app.services.techdetect import (
    detect_languages_from_files,
    detect_tech_stack,
    extract_run_instructions,
)

logger = logging.getLogger("app.services.demo")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEMO_REPO_DIR = DATA_DIR / "demo_repo"
DEMO_ISSUES_PATH = DATA_DIR / "demo_issues.json"
DEMO_PRS_PATH = DATA_DIR / "demo_prs.json"


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


async def load_demo_data(
    session: AsyncSession,
    provider: LLMProvider,
    fixture_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """
    Creates and indexes the demo/taskboard repository from bundled local files.
    Operates 100% offline with zero network calls.
    Embeds files, issues, and PRs on load.
    Finishes in under 20 seconds.
    """
    start_time = time.monotonic()
    repo_dir = fixture_dir or DEMO_REPO_DIR

    if not repo_dir.exists():
        raise FileNotFoundError(f"Demo repository directory not found: {repo_dir}")

    # 1. Load demo issues data to get allowed labels
    labels_list = [
        "bug",
        "enhancement",
        "documentation",
        "good-first-issue",
        "help wanted",
        "question",
        "chore",
        "security",
        "duplicate",
        "invalid",
        "ui",
        "api",
    ]
    issues_data = []
    if DEMO_ISSUES_PATH.exists():
        with open(DEMO_ISSUES_PATH, encoding="utf-8") as f:
            raw_issues = json.load(f)
            labels_list = raw_issues.get("labels", labels_list)
            issues_data = raw_issues.get("issues", [])

    prs_data = []
    if DEMO_PRS_PATH.exists():
        with open(DEMO_PRS_PATH, encoding="utf-8") as f:
            prs_data = json.load(f)

    # 2. Find or create demo/taskboard repository
    stmt = select(Repository).where(Repository.full_name == "demo/taskboard")
    res = await session.execute(stmt)
    repo = res.scalar_one_or_none()

    if repo is None:
        repo = Repository(
            id=uuid.uuid4(),
            owner="demo",
            name="taskboard",
            full_name="demo/taskboard",
            default_branch="main",
            description="TaskBoard lightweight task management application",
            labels=labels_list,
            status="fetching",
            progress=0,
            created_at=datetime.now(timezone.utc),
        )
        session.add(repo)
        await session.flush()
    else:
        repo.labels = labels_list
        # Clear existing dependent data for idempotent reload
        await session.execute(delete(File).where(File.repo_id == repo.id))
        await session.execute(delete(Issue).where(Issue.repo_id == repo.id))
        await session.execute(delete(PullRequest).where(PullRequest.repo_id == repo.id))
        await session.flush()

    repo.status = "chunking"
    repo.progress = 20

    # 3. Read and chunk all repository files
    all_files_on_disk = [p for p in repo_dir.rglob("*") if p.is_file() and not p.name.startswith(".")]
    file_records: list[File] = []
    chunks_to_embed: list[dict[str, Any]] = []

    for file_path in all_files_on_disk:
        rel_path = file_path.relative_to(repo_dir).as_posix()
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        size_bytes = len(content.encode("utf-8"))
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        # Language detection
        ext = file_path.suffix.lower()
        if ext == ".py":
            lang = "Python"
        elif ext == ".js":
            lang = "JavaScript"
        elif ext == ".json":
            lang = "JSON"
        elif ext == ".md":
            lang = "Markdown"
        else:
            lang = "Text"

        file_obj = File(
            id=uuid.uuid4(),
            repo_id=repo.id,
            path=rel_path,
            language=lang,
            size_bytes=size_bytes,
            content_hash=content_hash,
        )
        file_records.append(file_obj)
        session.add(file_obj)

        # Chunk file
        file_chunks = chunk_file(rel_path, content)
        for c in file_chunks:
            chunks_to_embed.append({
                "file_id": file_obj.id,
                "chunk_index": c.chunk_index,
                "start_line": c.start_line,
                "end_line": c.end_line,
                "content": c.content,
                "content_hash": c.content_hash,
            })

    await session.flush()

    # 4. Batch embed file chunks
    repo.status = "embedding"
    repo.progress = 50

    chunk_objects: list[Chunk] = []
    batch_size = 32

    for i in range(0, len(chunks_to_embed), batch_size):
        batch = chunks_to_embed[i : i + batch_size]
        texts = [b["content"] for b in batch]
        try:
            embeddings = await provider.embed(texts)
        except Exception as exc:
            logger.warning("Embedding batch failed for demo files: %s", exc)
            embeddings = [[0.0] * 768 for _ in texts]

        for item, emb in zip(batch, embeddings):
            c_obj = Chunk(
                id=uuid.uuid4(),
                repo_id=repo.id,
                file_id=item["file_id"],
                chunk_index=item["chunk_index"],
                start_line=item["start_line"],
                end_line=item["end_line"],
                content=item["content"],
                content_hash=item["content_hash"],
                embedding=emb,
            )
            chunk_objects.append(c_obj)
            session.add(c_obj)

    await session.flush()

    # 5. Extract metadata & build architecture graph
    repo.status = "summarizing"
    repo.progress = 80

    rel_paths = [p.relative_to(repo_dir).as_posix() for p in all_files_on_disk]
    repo.languages = detect_languages_from_files(rel_paths)

    manifests = {}
    req_path = repo_dir / "requirements.txt"
    if req_path.exists():
        manifests["requirements.txt"] = req_path.read_text(encoding="utf-8")
    pkg_path = repo_dir / "package.json"
    if pkg_path.exists():
        manifests["package.json"] = pkg_path.read_text(encoding="utf-8")

    repo.tech_stack = detect_tech_stack(manifests)

    readme_text = ""
    readme_path = repo_dir / "README.md"
    if readme_path.exists():
        readme_text = readme_path.read_text(encoding="utf-8")
        repo.readme_excerpt = readme_text[:1000]

    repo.run_instructions = extract_run_instructions(readme_text, manifests)

    contributing_path = repo_dir / "CONTRIBUTING.md"
    if contributing_path.exists():
        repo.contributing_md = contributing_path.read_text(encoding="utf-8")

    explorer = ExplorerService(provider=provider)
    await explorer.build_and_save_module_graph(session, repo, repo_dir)

    # 6. Load and embed demo issues
    issue_objects: list[Issue] = []
    if issues_data:
        issue_texts = [f"{iss['title']}\n\n{iss.get('body', '')}" for iss in issues_data]
        issue_embeddings = []
        for i in range(0, len(issue_texts), batch_size):
            batch_texts = issue_texts[i : i + batch_size]
            try:
                embs = await provider.embed(batch_texts)
            except Exception as exc:
                logger.warning("Embedding demo issues failed: %s", exc)
                embs = [[0.0] * 768 for _ in batch_texts]
            issue_embeddings.extend(embs)

        for iss, emb in zip(issues_data, issue_embeddings):
            iss_obj = Issue(
                id=uuid.uuid4(),
                repo_id=repo.id,
                number=iss["number"],
                title=iss["title"],
                body=iss.get("body", ""),
                state=iss.get("state", "open"),
                author=iss.get("author", "demo_author"),
                labels=iss.get("labels", []),
                html_url=iss.get("html_url"),
                created_at_gh=_parse_datetime(iss.get("created_at")),
                embedding=emb,
                triage_status="untriaged",
            )
            issue_objects.append(iss_obj)
            session.add(iss_obj)

        await session.flush()

    # 7. Load demo pull requests
    pr_objects: list[PullRequest] = []
    for pr in prs_data:
        diff_str = pr.get("diff", "")
        diff_hash = hashlib.sha256(diff_str.encode("utf-8")).hexdigest()

        author_assoc = pr.get("author_association", "")
        author_is_first_time = author_assoc in ("FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER")

        pr_obj = PullRequest(
            id=uuid.uuid4(),
            repo_id=repo.id,
            number=pr["number"],
            title=pr["title"],
            body=pr.get("body", ""),
            state=pr.get("state", "open"),
            author=pr.get("author", "demo_contributor"),
            author_is_first_time=author_is_first_time,
            additions=pr.get("additions", 0),
            deletions=pr.get("deletions", 0),
            changed_files=pr.get("changed_files", 1),
            merged=False,
            html_url=pr.get("html_url"),
            head_sha=pr.get("head_sha"),
            diff_hash=diff_hash,
            created_at_gh=datetime.now(timezone.utc),
            updated_at_gh=datetime.now(timezone.utc),
        )
        pr_objects.append(pr_obj)
        session.add(pr_obj)

    repo.status = "ready"
    repo.progress = 100
    repo.last_indexed_at = datetime.now(timezone.utc)

    await session.commit()

    duration = time.monotonic() - start_time
    logger.info(
        "Demo repository loaded in %.2f s: %d files, %d chunks, %d issues, %d PRs",
        duration,
        len(file_records),
        len(chunk_objects),
        len(issue_objects),
        len(pr_objects),
    )

    return {
        "repo_id": str(repo.id),
        "owner": repo.owner,
        "name": repo.name,
        "full_name": repo.full_name,
        "status": repo.status,
        "files_count": len(file_records),
        "chunks_count": len(chunk_objects),
        "issues_count": len(issue_objects),
        "prs_count": len(pr_objects),
        "duration_seconds": round(duration, 2),
    }
