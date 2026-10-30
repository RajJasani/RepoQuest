from __future__ import annotations

from datetime import datetime
import logging
import time
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.core.security import decrypt_token
from app.models.core import Job, Repository, Setting
from app.models.features import Issue, IssueAnalysis
from app.providers.factory import get_provider
from app.schemas.issues import (
    IssueAnalysisResponse,
    IssueApproveRequest,
    IssueApproveResponse,
    IssueDetailResponse,
    IssueListResponse,
    IssueSyncResponse,
    IssueTriageEnqueueResponse,
)
from app.services.audit import record_audit
from app.services.github import GitHubClient
from app.services.triage import approve_issue, reject_issue

logger = logging.getLogger("app.routers.issues")

router = APIRouter(tags=["issues"])


@router.post("/repos/{id}/issues/sync", response_model=IssueSyncResponse)
async def sync_repo_issues(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> IssueSyncResponse:
    """Pulls open issues and repository labels from GitHub and embeds titles and bodies."""
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    stmt_repo = select(Repository).where(Repository.id == repo_uuid)
    res_repo = await db.execute(stmt_repo)
    repo = res_repo.scalar_one_or_none()
    if repo is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    # Determine GitHub token
    token: Optional[str] = None
    stmt_set = select(Setting).where(Setting.id == 1)
    res_set = await db.execute(stmt_set)
    settings_row = res_set.scalar_one_or_none()
    if settings_row and settings_row.github_token_enc:
        try:
            token = decrypt_token(settings_row.github_token_enc)
        except Exception:
            pass

    gh = GitHubClient(token=token)
    provider = await get_provider(db)

    # 1. Fetch labels
    labels_data = await gh.get_labels(repo.owner, repo.name)
    repo_labels = [lbl["name"] for lbl in labels_data if isinstance(lbl, dict) and "name" in lbl]
    repo.labels = repo_labels

    # 2. Fetch open issues (GitHubClient.get_open_issues excludes pull requests)
    issues_data = await gh.get_open_issues(repo.owner, repo.name)

    # 3. Existing issues lookup to preserve IDs/triage statuses
    stmt_existing = select(Issue).where(Issue.repo_id == repo_uuid)
    res_existing = await db.execute(stmt_existing)
    existing_map: dict[int, Issue] = {i.number: i for i in res_existing.scalars().all()}

    texts_to_embed: list[str] = []
    issues_to_update: list[tuple[Issue, str]] = []

    for idata in issues_data:
        num = idata["number"]
        title = idata.get("title", "")
        body = idata.get("body", "") or ""
        combo_text = f"{title}\n{body}".strip()

        created_gh = None
        if idata.get("created_at"):
            try:
                created_gh = datetime.fromisoformat(idata["created_at"].replace("Z", "+00:00"))
            except Exception:
                pass

        updated_gh = None
        if idata.get("updated_at"):
            try:
                updated_gh = datetime.fromisoformat(idata["updated_at"].replace("Z", "+00:00"))
            except Exception:
                pass

        raw_labels = [lbl["name"] for lbl in idata.get("labels", []) if isinstance(lbl, dict) and "name" in lbl]

        if num in existing_map:
            issue_obj = existing_map[num]
            issue_obj.title = title
            issue_obj.body = body
            issue_obj.state = idata.get("state", "open")
            issue_obj.author = idata.get("user", {}).get("login")
            issue_obj.labels = raw_labels
            issue_obj.html_url = idata.get("html_url")
            issue_obj.created_at_gh = created_gh
            issue_obj.updated_at_gh = updated_gh
        else:
            issue_obj = Issue(
                id=uuid.uuid4(),
                repo_id=repo.id,
                number=num,
                title=title,
                body=body,
                state=idata.get("state", "open"),
                author=idata.get("user", {}).get("login"),
                labels=raw_labels,
                html_url=idata.get("html_url"),
                created_at_gh=created_gh,
                updated_at_gh=updated_gh,
                triage_status="untriaged",
            )
            db.add(issue_obj)

        issues_to_update.append((issue_obj, combo_text))
        texts_to_embed.append(combo_text)

    # Batch embed issues
    if texts_to_embed:
        t0 = time.perf_counter()
        embeddings = await provider.embed(texts_to_embed)
        t1 = time.perf_counter()
        for (issue_obj, _), emb in zip(issues_to_update, embeddings):
            issue_obj.embedding = emb
        await record_audit(
            session=db,
            feature="embeddings",
            action="embed_issues_sync",
            repo_id=repo.id,
            ref_type="repository",
            ref_id=str(repo.id),
            model=getattr(provider, "embed_model", "nomic-embed-text"),
            prompt_version="v1",
            tokens_in=sum(len(t) for t in texts_to_embed) // 4,
            tokens_out=0,
            latency_ms=max(int((t1 - t0) * 1000), 1),
            outcome="ok",
        )

    await db.commit()

    return IssueSyncResponse(
        synced_issues=len(issues_data),
        labels_count=len(repo_labels),
    )


@router.get("/repos/{id}/issues", response_model=IssueListResponse)
async def list_repo_issues(
    id: str,
    status: Optional[str] = Query(None, description="Filter by triage status"),
    q: Optional[str] = Query(None, description="Search keyword in title or body"),
    page: int = Query(1, ge=1, description="Page number (>=1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    db: AsyncSession = Depends(get_db),
) -> IssueListResponse:
    """Returns a paginated list of issues with their latest triage analysis."""
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    # Base filter
    filters = [Issue.repo_id == repo_uuid]
    if status:
        filters.append(Issue.triage_status == status)
    if q:
        search_filter = or_(
            Issue.title.ilike(f"%{q}%"),
            Issue.body.ilike(f"%{q}%"),
        )
        filters.append(search_filter)

    # Count total matching
    stmt_count = select(func.count(Issue.id)).where(*filters)
    res_count = await db.execute(stmt_count)
    total = res_count.scalar() or 0

    # Query paginated issues
    stmt = (
        select(Issue)
        .where(*filters)
        .order_by(Issue.number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    issues = res.scalars().all()

    # Load latest analysis for each issue
    items: list[IssueDetailResponse] = []
    for iss in issues:
        stmt_analysis = (
            select(IssueAnalysis)
            .where(IssueAnalysis.issue_id == iss.id)
            .order_by(IssueAnalysis.created_at.desc())
            .limit(1)
        )
        res_analysis = await db.execute(stmt_analysis)
        analysis_obj = res_analysis.scalar_one_or_none()

        analysis_resp = None
        if analysis_obj:
            analysis_resp = IssueAnalysisResponse(
                id=str(analysis_obj.id),
                type=analysis_obj.type,
                severity=analysis_obj.severity,
                labels=analysis_obj.labels or [],
                summary=analysis_obj.summary,
                missing_info=analysis_obj.missing_info or [],
                duplicates=analysis_obj.duplicates or [],
                good_first_issue_score=analysis_obj.good_first_issue_score,
                suggested_reply=analysis_obj.suggested_reply,
                confidence=analysis_obj.confidence,
                model=analysis_obj.model,
                prompt_version=analysis_obj.prompt_version,
                created_at=analysis_obj.created_at,
            )

        items.append(
            IssueDetailResponse(
                id=str(iss.id),
                repo_id=str(iss.repo_id),
                number=iss.number,
                title=iss.title,
                body=iss.body,
                state=iss.state,
                author=iss.author,
                labels=iss.labels or [],
                html_url=iss.html_url,
                triage_status=iss.triage_status,
                created_at_gh=iss.created_at_gh,
                analysis=analysis_resp,
            )
        )

    return IssueListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/issues/{id}", response_model=IssueDetailResponse)
async def get_issue(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> IssueDetailResponse:
    """Returns issue detail and its latest triage analysis."""
    try:
        issue_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Issue '{id}' not found.")

    stmt = select(Issue).where(Issue.id == issue_uuid)
    res = await db.execute(stmt)
    issue = res.scalar_one_or_none()
    if issue is None:
        raise NotFoundError(f"Issue '{id}' not found.")

    stmt_analysis = (
        select(IssueAnalysis)
        .where(IssueAnalysis.issue_id == issue.id)
        .order_by(IssueAnalysis.created_at.desc())
        .limit(1)
    )
    res_analysis = await db.execute(stmt_analysis)
    analysis_obj = res_analysis.scalar_one_or_none()

    analysis_resp = None
    if analysis_obj:
        analysis_resp = IssueAnalysisResponse(
            id=str(analysis_obj.id),
            type=analysis_obj.type,
            severity=analysis_obj.severity,
            labels=analysis_obj.labels or [],
            summary=analysis_obj.summary,
            missing_info=analysis_obj.missing_info or [],
            duplicates=analysis_obj.duplicates or [],
            good_first_issue_score=analysis_obj.good_first_issue_score,
            suggested_reply=analysis_obj.suggested_reply,
            confidence=analysis_obj.confidence,
            model=analysis_obj.model,
            prompt_version=analysis_obj.prompt_version,
            created_at=analysis_obj.created_at,
        )

    return IssueDetailResponse(
        id=str(issue.id),
        repo_id=str(issue.repo_id),
        number=issue.number,
        title=issue.title,
        body=issue.body,
        state=issue.state,
        author=issue.author,
        labels=issue.labels or [],
        html_url=issue.html_url,
        triage_status=issue.triage_status,
        created_at_gh=issue.created_at_gh,
        analysis=analysis_resp,
    )


@router.post("/issues/{id}/triage", response_model=IssueTriageEnqueueResponse, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_triage_job(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> IssueTriageEnqueueResponse:
    """Enqueues a background job to run AI triage on the issue."""
    try:
        issue_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Issue '{id}' not found.")

    stmt = select(Issue).where(Issue.id == issue_uuid)
    res = await db.execute(stmt)
    issue = res.scalar_one_or_none()
    if issue is None:
        raise NotFoundError(f"Issue '{id}' not found.")

    job = Job(
        kind="triage_issue",
        payload={"issue_id": str(issue.id), "repo_id": str(issue.repo_id)},
        status="queued",
    )
    db.add(job)
    await db.commit()

    return IssueTriageEnqueueResponse(
        issue_id=str(issue.id),
        job_id=str(job.id),
    )


@router.post("/issues/{id}/approve", response_model=IssueApproveResponse)
async def approve_issue_triage(
    id: str,
    payload: IssueApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> IssueApproveResponse:
    """
    Approves the triage recommendation. Applies labels and posts comment to GitHub
    if a write token exists, otherwise applies locally and returns the comment for manual copying.
    """
    try:
        issue_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Issue '{id}' not found.")

    stmt = select(Issue).where(Issue.id == issue_uuid)
    res = await db.execute(stmt)
    issue = res.scalar_one_or_none()
    if issue is None:
        raise NotFoundError(f"Issue '{id}' not found.")

    stmt_repo = select(Repository).where(Repository.id == issue.repo_id)
    res_repo = await db.execute(stmt_repo)
    repo = res_repo.scalar_one_or_none()
    if repo is None:
        raise NotFoundError("Repository associated with this issue was not found.")

    stmt_set = select(Setting).where(Setting.id == 1)
    res_set = await db.execute(stmt_set)
    settings_row = res_set.scalar_one_or_none()

    res = await approve_issue(
        session=db,
        issue=issue,
        repo=repo,
        settings_row=settings_row,
        labels=payload.labels,
        comment=payload.comment,
        post_to_github=payload.post_to_github,
    )

    return IssueApproveResponse(
        status=res["status"],
        issue_id=res["issue_id"],
        labels=res["labels"],
        comment=res["comment"],
        posted_to_github=res["posted_to_github"],
    )


@router.post("/issues/{id}/reject")
async def reject_issue_triage(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Rejects the triage recommendation and marks the issue status as rejected."""
    try:
        issue_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Issue '{id}' not found.")

    stmt = select(Issue).where(Issue.id == issue_uuid)
    res = await db.execute(stmt)
    issue = res.scalar_one_or_none()
    if issue is None:
        raise NotFoundError(f"Issue '{id}' not found.")

    return await reject_issue(session=db, issue=issue, repo_id=issue.repo_id)
