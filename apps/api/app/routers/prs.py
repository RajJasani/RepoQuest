from __future__ import annotations

from datetime import datetime
import logging
import time
from typing import Any, Optional
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import ConflictError, NotFoundError
from app.core.security import decrypt_token
from app.models.core import Repository, Setting
from app.models.features import PRReview, PullRequest, SpamAssessment
from app.routers.system import get_provider
from app.schemas.prs import (
    PRDetailResponse,
    PRListResponse,
    PRPostReviewResponse,
    PRReviewResponse,
    PRSyncResponse,
    SpamAssessmentResponse,
)
from app.services.audit import record_audit
from app.services.github import GitHubClient
from app.services.review import format_review_markdown, stream_pr_review_sse

logger = logging.getLogger("app.routers.prs")

router = APIRouter(prefix="", tags=["prs"])


def _parse_gh_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _build_review_response(rev: Optional[PRReview]) -> Optional[PRReviewResponse]:
    if rev is None:
        return None

    if isinstance(rev.summary, list):
        summary_list = rev.summary
    elif isinstance(rev.summary, str):
        summary_list = [s.strip() for s in rev.summary.splitlines() if s.strip()]
    else:
        summary_list = []

    return PRReviewResponse(
        id=str(rev.id),
        pr_id=str(rev.pr_id),
        status=rev.status,
        summary=summary_list,
        risk_level=rev.risk_level,
        risk_reasons=rev.checks.get("risk_reasons", []) if isinstance(rev.checks, dict) and "risk_reasons" in rev.checks else [],
        checks=rev.checks if isinstance(rev.checks, dict) else {},
        file_comments=rev.file_comments if isinstance(rev.file_comments, list) else [],
        newcomer_explainer=rev.newcomer_explainer,
        verdict=rev.verdict,
        model=rev.model,
        prompt_version=rev.prompt_version,
        created_at=rev.created_at,
    )


def _build_spam_response(spam: Optional[SpamAssessment]) -> Optional[SpamAssessmentResponse]:
    if spam is None:
        return None
    return SpamAssessmentResponse(
        id=str(spam.id),
        pr_id=str(spam.pr_id),
        spam_score=spam.spam_score,
        reasons=spam.reasons if isinstance(spam.reasons, list) else [],
        rule_signals=spam.rule_signals if isinstance(spam.rule_signals, dict) else {},
        recommended_action=spam.recommended_action,
        polite_comment=spam.polite_comment,
        created_at=spam.created_at,
    )


@router.post("/repos/{id}/prs/sync", response_model=PRSyncResponse)
async def sync_repo_prs(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> PRSyncResponse:
    """
    Pulls open PRs from GitHub, detects if author is first time contributor,
    embeds title and body, and persists pull requests.
    """
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    stmt = select(Repository).where(Repository.id == repo_uuid)
    res = await db.execute(stmt)
    repo = res.scalar_one_or_none()
    if repo is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    # Get settings for GitHub token
    settings_stmt = select(Setting).where(Setting.id == 1)
    settings_res = await db.execute(settings_stmt)
    settings_row = settings_res.scalar_one_or_none()
    token = decrypt_token(settings_row.github_token_enc) if settings_row and settings_row.github_token_enc else None

    gh = GitHubClient(token=token)
    gh_prs = await gh.get_open_pull_requests(repo.owner, repo.name)

    provider = await get_provider(db)

    synced_count = 0
    for pr_item in gh_prs:
        number = pr_item.get("number")
        if not number:
            continue

        title = pr_item.get("title", "")
        body = pr_item.get("body") or ""
        state = pr_item.get("state", "open")
        author = pr_item.get("user", {}).get("login") if pr_item.get("user") else None
        html_url = pr_item.get("html_url")
        head_sha = pr_item.get("head", {}).get("sha") if pr_item.get("head") else None

        author_assoc = pr_item.get("author_association", "")
        author_is_first_time = author_assoc in ("FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER")

        # Embed title and body as per task requirement
        try:
            t0 = time.perf_counter()
            await provider.embed([f"{title}\n\n{body}"])
            t1 = time.perf_counter()
            await record_audit(
                session=db,
                feature="embeddings",
                action="embed_pr_sync",
                repo_id=repo.id,
                ref_type="pull_request",
                ref_id=str(number),
                model=getattr(provider, "embed_model", "nomic-embed-text"),
                prompt_version="v1",
                tokens_in=len(f"{title}\n\n{body}") // 4,
                tokens_out=0,
                latency_ms=max(int((t1 - t0) * 1000), 1),
                outcome="ok",
            )
        except Exception as exc:
            logger.warning("Failed to embed PR #%s: %s", number, exc)

        # Check existing PR in database
        stmt_pr = select(PullRequest).where(
            PullRequest.repo_id == repo.id,
            PullRequest.number == number,
        )
        res_pr = await db.execute(stmt_pr)
        existing_pr = res_pr.scalar_one_or_none()

        if existing_pr:
            existing_pr.title = title
            existing_pr.body = body
            existing_pr.state = state
            existing_pr.author = author
            existing_pr.author_is_first_time = author_is_first_time
            existing_pr.html_url = html_url
            existing_pr.head_sha = head_sha
            existing_pr.updated_at_gh = _parse_gh_datetime(pr_item.get("updated_at"))
        else:
            new_pr = PullRequest(
                id=uuid.uuid4(),
                repo_id=repo.id,
                number=number,
                title=title,
                body=body,
                state=state,
                author=author,
                author_is_first_time=author_is_first_time,
                html_url=html_url,
                head_sha=head_sha,
                created_at_gh=_parse_gh_datetime(pr_item.get("created_at")),
                updated_at_gh=_parse_gh_datetime(pr_item.get("updated_at")),
            )
            db.add(new_pr)

        synced_count += 1

    await db.commit()
    return PRSyncResponse(synced_prs=synced_count)


@router.get("/repos/{id}/prs", response_model=PRListResponse)
async def list_repo_prs(
    id: str,
    state: Optional[str] = Query(None, description="Filter by state (open, closed, etc.)"),
    page: int = Query(1, ge=1, description="Page number (>=1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (1-100)"),
    db: AsyncSession = Depends(get_db),
) -> PRListResponse:
    """Returns paginated list of pull requests with latest review and spam assessment."""
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    filters = [PullRequest.repo_id == repo_uuid]
    if state:
        filters.append(PullRequest.state == state)

    stmt_count = select(func.count(PullRequest.id)).where(*filters)
    res_count = await db.execute(stmt_count)
    total = res_count.scalar() or 0

    stmt = (
        select(PullRequest)
        .where(*filters)
        .order_by(PullRequest.number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    res = await db.execute(stmt)
    prs = res.scalars().all()

    items: list[PRDetailResponse] = []
    for pr in prs:
        # Fetch latest review
        stmt_rev = (
            select(PRReview)
            .where(PRReview.pr_id == pr.id)
            .order_by(PRReview.created_at.desc())
            .limit(1)
        )
        res_rev = await db.execute(stmt_rev)
        latest_rev = res_rev.scalar_one_or_none()

        # Fetch latest spam assessment
        stmt_spam = (
            select(SpamAssessment)
            .where(SpamAssessment.pr_id == pr.id)
            .order_by(SpamAssessment.created_at.desc())
            .limit(1)
        )
        res_spam = await db.execute(stmt_spam)
        latest_spam = res_spam.scalar_one_or_none()

        items.append(
            PRDetailResponse(
                id=str(pr.id),
                repo_id=str(pr.repo_id),
                number=pr.number,
                title=pr.title,
                body=pr.body,
                state=pr.state,
                author=pr.author,
                author_is_first_time=bool(pr.author_is_first_time),
                additions=pr.additions or 0,
                deletions=pr.deletions or 0,
                changed_files=pr.changed_files or 0,
                merged=bool(pr.merged),
                html_url=pr.html_url,
                head_sha=pr.head_sha,
                diff_hash=pr.diff_hash,
                created_at_gh=pr.created_at_gh,
                updated_at_gh=pr.updated_at_gh,
                latest_review=_build_review_response(latest_rev),
                latest_spam_assessment=_build_spam_response(latest_spam),
            )
        )

    return PRListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/prs/{id}", response_model=PRDetailResponse)
async def get_pr_detail(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> PRDetailResponse:
    """Returns PR details along with latest review and spam assessment if present."""
    try:
        pr_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Pull request '{id}' not found.")

    stmt = select(PullRequest).where(PullRequest.id == pr_uuid)
    res = await db.execute(stmt)
    pr = res.scalar_one_or_none()
    if pr is None:
        raise NotFoundError(f"Pull request '{id}' not found.")

    # Latest review
    stmt_rev = (
        select(PRReview)
        .where(PRReview.pr_id == pr.id)
        .order_by(PRReview.created_at.desc())
        .limit(1)
    )
    res_rev = await db.execute(stmt_rev)
    latest_rev = res_rev.scalar_one_or_none()

    # Latest spam assessment
    stmt_spam = (
        select(SpamAssessment)
        .where(SpamAssessment.pr_id == pr.id)
        .order_by(SpamAssessment.created_at.desc())
        .limit(1)
    )
    res_spam = await db.execute(stmt_spam)
    latest_spam = res_spam.scalar_one_or_none()

    return PRDetailResponse(
        id=str(pr.id),
        repo_id=str(pr.repo_id),
        number=pr.number,
        title=pr.title,
        body=pr.body,
        state=pr.state,
        author=pr.author,
        author_is_first_time=bool(pr.author_is_first_time),
        additions=pr.additions or 0,
        deletions=pr.deletions or 0,
        changed_files=pr.changed_files or 0,
        merged=bool(pr.merged),
        html_url=pr.html_url,
        head_sha=pr.head_sha,
        diff_hash=pr.diff_hash,
        created_at_gh=pr.created_at_gh,
        updated_at_gh=pr.updated_at_gh,
        latest_review=_build_review_response(latest_rev),
        latest_spam_assessment=_build_spam_response(latest_spam),
    )


@router.post("/prs/{id}/review")
async def stream_review_pr(
    id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Streams file-by-file review progress, ending with the merged review result as SSE.
    """
    try:
        pr_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Pull request '{id}' not found.")

    stmt = select(PullRequest).where(PullRequest.id == pr_uuid)
    res = await db.execute(stmt)
    pr = res.scalar_one_or_none()
    if pr is None:
        raise NotFoundError(f"Pull request '{id}' not found.")

    stmt_repo = select(Repository).where(Repository.id == pr.repo_id)
    res_repo = await db.execute(stmt_repo)
    repo = res_repo.scalar_one_or_none()
    if repo is None:
        raise NotFoundError(f"Repository for PR '{id}' not found.")

    # Get GitHub token
    settings_stmt = select(Setting).where(Setting.id == 1)
    settings_res = await db.execute(settings_stmt)
    settings_row = settings_res.scalar_one_or_none()
    token = decrypt_token(settings_row.github_token_enc) if settings_row and settings_row.github_token_enc else None

    gh = GitHubClient(token=token)
    raw_diff = await gh.get_pull_request_diff(repo.owner, repo.name, pr.number)

    provider = await get_provider(db)

    async def sse_event_generator():
        async for chunk in stream_pr_review_sse(db, pr, repo, raw_diff, provider):
            if await request.is_disconnected():
                logger.info("Client disconnected during PR review SSE stream.")
                break
            yield chunk

    return EventSourceResponse(
        sse_event_generator(),
        ping=15,
        ping_message_factory=lambda: ServerSentEvent(comment="ping"),
    )


@router.post("/prs/{id}/review/post", response_model=PRPostReviewResponse)
async def post_review_to_github(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> PRPostReviewResponse:
    """
    Creates ONE review with inline comments on GitHub if a write token exists.
    If no token exists, returns 409 Conflict with a Markdown version to copy.
    """
    try:
        pr_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Pull request '{id}' not found.")

    stmt = select(PullRequest).where(PullRequest.id == pr_uuid)
    res = await db.execute(stmt)
    pr = res.scalar_one_or_none()
    if pr is None:
        raise NotFoundError(f"Pull request '{id}' not found.")

    stmt_repo = select(Repository).where(Repository.id == pr.repo_id)
    res_repo = await db.execute(stmt_repo)
    repo = res_repo.scalar_one_or_none()
    if repo is None:
        raise NotFoundError(f"Repository for PR '{id}' not found.")

    stmt_rev = (
        select(PRReview)
        .where(PRReview.pr_id == pr.id)
        .order_by(PRReview.created_at.desc())
        .limit(1)
    )
    res_rev = await db.execute(stmt_rev)
    review = res_rev.scalar_one_or_none()
    if review is None:
        raise NotFoundError(f"No review found for PR #{pr.number}. Generate a review first.")

    settings_stmt = select(Setting).where(Setting.id == 1)
    settings_res = await db.execute(settings_stmt)
    settings_row = settings_res.scalar_one_or_none()

    if not settings_row or not settings_row.github_token_enc:
        md_text = format_review_markdown(pr, review)
        raise ConflictError(
            message="No GitHub token configured. Review cannot be posted automatically.",
            details={"markdown": md_text},
        )

    token = decrypt_token(settings_row.github_token_enc)
    gh = GitHubClient(token=token)

    # Format inline comments for GitHub API
    gh_comments: list[dict[str, Any]] = []
    file_comments = review.file_comments or []
    for c in file_comments:
        c_body = f"**[{c.get('severity', 'info').upper()}]** {c.get('comment', '')}"
        if c.get("suggestion"):
            c_body += f"\n\n```suggestion\n{c['suggestion']}\n```"

        target_line = c.get("line_end") or c.get("line_start") or 1
        gh_comments.append({
            "path": c.get("file"),
            "line": int(target_line),
            "body": c_body,
        })

    # Map verdict
    if review.verdict == "approve_ready":
        gh_event = "APPROVE"
    elif review.verdict == "needs_changes":
        gh_event = "REQUEST_CHANGES"
    else:
        gh_event = "COMMENT"

    summary_text = review.summary or "Automated review generated by RepoQuest."
    if isinstance(summary_text, list):
        summary_text = "\n".join(f"- {s}" for s in summary_text)

    review_body = (
        f"## RepoQuest Review for #{pr.number}\n\n"
        f"**Verdict:** {review.verdict}\n"
        f"**Risk Level:** {review.risk_level}\n\n"
        f"### Summary\n{summary_text}\n\n"
        f"### Newcomer Explainer\n{review.newcomer_explainer or 'N/A'}"
    )

    try:
        await gh.create_pull_request_review(
            owner=repo.owner,
            repo=repo.name,
            pull_number=pr.number,
            body=review_body,
            event=gh_event,
            comments=gh_comments,
        )
    except Exception as exc:
        logger.error("Failed to post review to GitHub: %s", exc)
        raise

    review.status = "posted"
    await record_audit(
        session=db,
        feature="review",
        action="post_review",
        repo_id=repo.id,
        ref_type="pr",
        ref_id=str(pr.id),
        outcome="ok",
    )
    await db.commit()

    return PRPostReviewResponse(
        status="posted",
        review_id=str(review.id),
    )
