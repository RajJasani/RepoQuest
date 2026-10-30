from __future__ import annotations

from collections.abc import AsyncIterator
import json
import logging
from typing import Any, Literal, Optional
import uuid

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Chunk, File, Repository
from app.models.features import PRReview as PRReviewModel, PullRequest
from app.providers.base import LLMProvider
from app.schemas.llm import FileComment, FileReview, PRReview
from app.services.audit import record_audit
from app.services.diffparse import ParsedFileDiff, parse_unified_diff
from app.services.redact import SECRET_PATTERNS, redact_secrets, should_skip_file
from app.services.structured import run_structured_pipeline

logger = logging.getLogger("app.services.review")


class PRReviewMergeResult(BaseModel):
    summary: list[str] = Field(default_factory=list)
    risk_level: Literal["low", "medium", "high"] = "low"
    risk_reasons: list[str] = Field(default_factory=list)
    checks: dict[str, Optional[bool]] = Field(default_factory=dict)
    newcomer_explainer: str = ""
    verdict: Literal["approve_ready", "needs_changes", "needs_discussion"] = "needs_discussion"


def validate_file_comments(
    comments: list[FileComment],
    file_diff: ParsedFileDiff,
) -> list[FileComment]:
    """
    Validates per-file review comments in code:
    - Line numbers must exist in the diff hunks (valid_lines). Invalid ones are dropped.
    - Ensures file path matches.
    - Normalizes line ranges.
    """
    valid: list[FileComment] = []
    for c in comments:
        # Match file path
        c.file = file_diff.path

        # If both line_start and line_end are outside diff, drop
        if c.line_start not in file_diff.valid_lines and c.line_end not in file_diff.valid_lines:
            continue

        # Adjust one-sided outside lines
        if c.line_start in file_diff.valid_lines and c.line_end not in file_diff.valid_lines:
            c.line_end = c.line_start
        elif c.line_end in file_diff.valid_lines and c.line_start not in file_diff.valid_lines:
            c.line_start = c.line_end

        if c.line_start > c.line_end:
            c.line_start, c.line_end = c.line_end, c.line_start

        valid.append(c)

    return valid


async def retrieve_related_chunks_for_file(
    session: AsyncSession,
    repo_id: uuid.UUID,
    file_path: str,
    limit: int = 4,
) -> str:
    """Retrieves up to `limit` related code chunks for the given file path."""
    try:
        stmt = (
            select(Chunk.content)
            .join(File, Chunk.file_id == File.id)
            .where(File.repo_id == repo_id, File.path == file_path)
            .limit(limit)
        )
        res = await session.execute(stmt)
        chunks = res.scalars().all()
        if chunks:
            return "\n---\n".join(chunks)
    except Exception as exc:
        logger.debug("Could not retrieve chunks for file %s: %s", file_path, exc)

    return ""


def format_review_markdown(pr: PullRequest, review: Any) -> str:
    """Generates a complete Markdown review report suitable for copying or posting."""
    summary_raw = getattr(review, "summary", [])
    if isinstance(summary_raw, list):
        summary_lines = summary_raw
    else:
        summary_lines = str(summary_raw or "").splitlines()
    bullets = "\n".join(f"- {s.strip()}" for s in summary_lines if s.strip())

    checks = getattr(review, "checks", {}) or {}
    checks_str = ""
    for k, v in checks.items():
        val_str = "Passed" if v is True else ("Failed" if v is False else "N/A")
        checks_str += f"- **{k}**: {val_str}\n"

    comments_str = ""
    file_comments = getattr(review, "file_comments", []) or []
    if file_comments:
        for c in file_comments:
            if hasattr(c, "model_dump"):
                c = c.model_dump()
            f = c.get("file", "")
            ls = c.get("line_start", "")
            le = c.get("line_end", "")
            sev = c.get("severity", "info").upper()
            comment = c.get("comment", "")
            sug = c.get("suggestion")
            comments_str += f"\n#### `{f}` (lines {ls}-{le}) - [{sev}]\n{comment}\n"
            if sug:
                comments_str += f"```suggestion\n{sug}\n```\n"
    else:
        comments_str = "No inline comments."

    explainer = getattr(review, "newcomer_explainer", "") or "N/A"
    risk_level = getattr(review, "risk_level", "low")
    verdict = getattr(review, "verdict", "needs_discussion")

    return (
        f"## RepoQuest PR Review: #{pr.number} {pr.title}\n\n"
        f"**Verdict:** `{verdict}`\n"
        f"**Risk Level:** `{risk_level}`\n\n"
        f"### Summary\n{bullets or '- No summary provided.'}\n\n"
        f"### Checks\n{checks_str or '- None recorded.'}\n"
        f"### Newcomer Explanation\n{explainer}\n\n"
        f"### Inline Comments ({len(file_comments)})\n{comments_str}"
    )


async def execute_pr_review(
    session: AsyncSession,
    pr: PullRequest,
    repo: Repository,
    raw_diff: str,
    provider: LLMProvider,
) -> tuple[PRReviewModel, PRReview, list[dict[str, Any]]]:
    """
    Executes the full PR review pipeline:
    1. Parse diff, check secrets, handle >1,500 lines limit.
    2. File-by-file review with chunk context and line validation.
    3. Merge review into summary, checks, explainer, verdict.
    4. Save to pr_reviews and write audit row.
    Returns (PRReviewModel, PRReview, list_of_progress_steps).
    """
    all_files = parse_unified_diff(raw_diff)

    # Filter reviewable files (exclude deleted and binary)
    reviewable_files = [f for f in all_files if not f.is_binary and not f.is_deleted]

    total_changed = sum(f.changed_lines for f in all_files)
    diff_truncated = False
    files_to_review = reviewable_files

    if total_changed > 1500:
        diff_truncated = True
        files_to_review = sorted(reviewable_files, key=lambda f: f.changed_lines, reverse=True)[:10]

    # Secret check: regex patterns or sensitive filenames
    regex_found_secret = any(p.search(raw_diff) for p in SECRET_PATTERNS) or any(
        should_skip_file(f.path) for f in all_files
    )

    all_valid_comments: list[FileComment] = []
    progress_steps: list[dict[str, Any]] = []

    total_tokens_in = 0
    total_tokens_out = 0
    total_latency_ms = 0
    overall_outcome = "ok"

    # 1. Per-file review
    for idx, f in enumerate(files_to_review):
        related_chunks = await retrieve_related_chunks_for_file(session, repo.id, f.path)

        safe_patch = redact_secrets(f.patch)
        safe_context = redact_secrets(related_chunks)
        safe_body = redact_secrets(pr.body or "")

        file_prompt_context = (
            f"Pull Request #{pr.number}: {pr.title}\n"
            f"Author: {pr.author or 'Unknown'} "
            f"({'First-time contributor' if pr.author_is_first_time else 'Contributor'})\n"
            f"Description:\n{safe_body}\n\n"
            f"File: {f.path}\n"
            f"Diff:\n{safe_patch}\n\n"
        )
        if safe_context:
            file_prompt_context += f"Related Code Context:\n{safe_context}\n"

        try:
            res = await run_structured_pipeline(
                provider=provider,
                task_name="pr_review_file",
                context_text=file_prompt_context,
                schema=FileReview,
                fallback=FileReview(),
            )
            total_tokens_in += res.tokens_in or 0
            total_tokens_out += res.tokens_out or 0
            total_latency_ms += res.latency_ms or 0
            if res.outcome != "ok":
                overall_outcome = res.outcome

            raw_comments = res.data.file_comments
        except Exception as exc:
            logger.warning("File review failed for %s: %s", f.path, exc)
            raw_comments = []

        valid_comments = validate_file_comments(raw_comments, f)
        all_valid_comments.extend(valid_comments)

        percent = int(((idx + 1) / max(len(files_to_review), 1)) * 80)
        progress_steps.append({
            "stage": "reviewing",
            "percent": percent,
            "message": f"Reviewed {f.path} ({len(valid_comments)} comments)",
            "file": f.path,
            "index": idx + 1,
            "total": len(files_to_review),
            "comments_count": len(valid_comments),
        })

    # 2. Merge step
    merge_context = (
        f"Pull Request #{pr.number}: {pr.title}\n"
        f"Author: {pr.author or 'Unknown'} "
        f"({'First-time contributor' if pr.author_is_first_time else 'Contributor'})\n"
        f"Description:\n{redact_secrets(pr.body or '')}\n\n"
        f"Changed files reviewed: {[f.path for f in files_to_review]}\n"
        f"Total changed lines across PR: {total_changed}\n"
        f"Inline comments generated:\n{json.dumps([c.model_dump() for c in all_valid_comments], indent=2)}\n"
    )

    try:
        merge_res = await run_structured_pipeline(
            provider=provider,
            task_name="pr_review_merge",
            context_text=merge_context,
            schema=PRReviewMergeResult,
            fallback=PRReviewMergeResult(
                summary=["Unable to complete automated review due to model output errors."],
                risk_level="medium",
                risk_reasons=["Automated review could not be completed."],
                checks={},
                newcomer_explainer="Automated review is unavailable for this pull request.",
                verdict="needs_discussion",
            ),
        )
        total_tokens_in += merge_res.tokens_in or 0
        total_tokens_out += merge_res.tokens_out or 0
        total_latency_ms += merge_res.latency_ms or 0
        if merge_res.outcome != "ok":
            overall_outcome = merge_res.outcome

        merged = merge_res.data
    except Exception as exc:
        logger.warning("Merge step failed for PR #%s: %s", pr.number, exc)
        overall_outcome = "invalid_llm_output"
        merged = PRReviewMergeResult(
            summary=["Unable to complete automated review due to model output errors."],
            risk_level="medium",
            risk_reasons=["Automated review could not be completed."],
            checks={},
            newcomer_explainer="Automated review is unavailable for this pull request.",
            verdict="needs_discussion",
        )

    # Post-process checks and summary notices
    checks = dict(merged.checks)
    if regex_found_secret:
        checks["possible_secret"] = True
        if not any("secret" in r.lower() for r in merged.risk_reasons):
            merged.risk_reasons.append("Possible secret or credential detected in diff by pattern scanning.")
    elif "possible_secret" not in checks or checks["possible_secret"] is None:
        checks["possible_secret"] = False

    summary_bullets = list(merged.summary)
    if diff_truncated:
        notice = f"Notice: Diff exceeds 1,500 changed lines ({total_changed} lines). Reviewed the 10 most-changed files."
        if not any("1,500" in s for s in summary_bullets):
            summary_bullets.insert(0, notice)

    final_review = PRReview(
        summary=summary_bullets,
        risk_level=merged.risk_level,
        risk_reasons=merged.risk_reasons,
        checks=checks,
        file_comments=all_valid_comments,
        newcomer_explainer=merged.newcomer_explainer or "No newcomer explanation generated.",
        verdict=merged.verdict,
    )

    # 3. Store in DB
    model_name = getattr(provider, "chat_model", "gemma3:4b")
    review_record = PRReviewModel(
        id=uuid.uuid4(),
        pr_id=pr.id,
        status="done",
        summary="\n".join(final_review.summary),
        risk_level=final_review.risk_level,
        checks=final_review.checks,
        file_comments=[c.model_dump() for c in final_review.file_comments],
        newcomer_explainer=final_review.newcomer_explainer,
        verdict=final_review.verdict,
        model=model_name,
        prompt_version="v1",
    )
    session.add(review_record)
    await session.flush()

    # 4. Audit logging
    await record_audit(
        session=session,
        feature="review",
        action="pr_review",
        repo_id=repo.id,
        ref_type="pr",
        ref_id=str(pr.id),
        model=model_name,
        prompt_version="v1",
        tokens_in=total_tokens_in,
        tokens_out=total_tokens_out,
        latency_ms=total_latency_ms,
        outcome=overall_outcome,
    )
    await session.commit()

    return review_record, final_review, progress_steps


async def stream_pr_review_sse(
    session: AsyncSession,
    pr: PullRequest,
    repo: Repository,
    raw_diff: str,
    provider: LLMProvider,
) -> AsyncIterator[dict[str, Any]]:
    """
    Yields SSE formatted event dicts for PR review:
    1. progress per file
    2. result with the final review object
    3. done
    """
    all_files = parse_unified_diff(raw_diff)
    reviewable_files = [f for f in all_files if not f.is_binary and not f.is_deleted]
    total_changed = sum(f.changed_lines for f in all_files)
    diff_truncated = False
    files_to_review = reviewable_files

    if total_changed > 1500:
        diff_truncated = True
        files_to_review = sorted(reviewable_files, key=lambda f: f.changed_lines, reverse=True)[:10]

    regex_found_secret = any(p.search(raw_diff) for p in SECRET_PATTERNS) or any(
        should_skip_file(f.path) for f in all_files
    )

    all_valid_comments: list[FileComment] = []
    total_tokens_in = 0
    total_tokens_out = 0
    total_latency_ms = 0
    overall_outcome = "ok"

    # Stream per-file progress
    for idx, f in enumerate(files_to_review):
        percent = int(((idx + 1) / max(len(files_to_review), 1)) * 80)
        yield {
            "event": "progress",
            "data": json.dumps({
                "stage": "reviewing",
                "percent": percent,
                "message": f"Reviewing {f.path}...",
                "file": f.path,
                "index": idx + 1,
                "total": len(files_to_review),
            }),
        }

        related_chunks = await retrieve_related_chunks_for_file(session, repo.id, f.path)
        safe_patch = redact_secrets(f.patch)
        safe_context = redact_secrets(related_chunks)
        safe_body = redact_secrets(pr.body or "")

        file_prompt_context = (
            f"Pull Request #{pr.number}: {pr.title}\n"
            f"Author: {pr.author or 'Unknown'} "
            f"({'First-time contributor' if pr.author_is_first_time else 'Contributor'})\n"
            f"Description:\n{safe_body}\n\n"
            f"File: {f.path}\n"
            f"Diff:\n{safe_patch}\n\n"
        )
        if safe_context:
            file_prompt_context += f"Related Code Context:\n{safe_context}\n"

        try:
            res = await run_structured_pipeline(
                provider=provider,
                task_name="pr_review_file",
                context_text=file_prompt_context,
                schema=FileReview,
                fallback=FileReview(),
            )
            total_tokens_in += res.tokens_in or 0
            total_tokens_out += res.tokens_out or 0
            total_latency_ms += res.latency_ms or 0
            if res.outcome != "ok":
                overall_outcome = res.outcome
            raw_comments = res.data.file_comments
        except Exception:
            raw_comments = []

        valid_comments = validate_file_comments(raw_comments, f)
        all_valid_comments.extend(valid_comments)

    # Merge step
    yield {
        "event": "progress",
        "data": json.dumps({
            "stage": "merging",
            "percent": 90,
            "message": "Synthesizing final review report...",
        }),
    }

    merge_context = (
        f"Pull Request #{pr.number}: {pr.title}\n"
        f"Author: {pr.author or 'Unknown'} "
        f"({'First-time contributor' if pr.author_is_first_time else 'Contributor'})\n"
        f"Description:\n{redact_secrets(pr.body or '')}\n\n"
        f"Changed files reviewed: {[f.path for f in files_to_review]}\n"
        f"Total changed lines across PR: {total_changed}\n"
        f"Inline comments generated:\n{json.dumps([c.model_dump() for c in all_valid_comments], indent=2)}\n"
    )

    try:
        merge_res = await run_structured_pipeline(
            provider=provider,
            task_name="pr_review_merge",
            context_text=merge_context,
            schema=PRReviewMergeResult,
            fallback=PRReviewMergeResult(
                summary=["Unable to complete automated review due to model output errors."],
                risk_level="medium",
                risk_reasons=["Automated review could not be completed."],
                checks={},
                newcomer_explainer="Automated review is unavailable for this pull request.",
                verdict="needs_discussion",
            ),
        )
        total_tokens_in += merge_res.tokens_in or 0
        total_tokens_out += merge_res.tokens_out or 0
        total_latency_ms += merge_res.latency_ms or 0
        if merge_res.outcome != "ok":
            overall_outcome = merge_res.outcome
        merged = merge_res.data
    except Exception:
        overall_outcome = "invalid_llm_output"
        merged = PRReviewMergeResult(
            summary=["Unable to complete automated review due to model output errors."],
            risk_level="medium",
            risk_reasons=["Automated review could not be completed."],
            checks={},
            newcomer_explainer="Automated review is unavailable for this pull request.",
            verdict="needs_discussion",
        )

    checks = dict(merged.checks)
    if regex_found_secret:
        checks["possible_secret"] = True
        if not any("secret" in r.lower() for r in merged.risk_reasons):
            merged.risk_reasons.append("Possible secret or credential detected in diff by pattern scanning.")
    elif "possible_secret" not in checks or checks["possible_secret"] is None:
        checks["possible_secret"] = False

    summary_bullets = list(merged.summary)
    if diff_truncated:
        notice = f"Notice: Diff exceeds 1,500 changed lines ({total_changed} lines). Reviewed the 10 most-changed files."
        if not any("1,500" in s for s in summary_bullets):
            summary_bullets.insert(0, notice)

    final_review = PRReview(
        summary=summary_bullets,
        risk_level=merged.risk_level,
        risk_reasons=merged.risk_reasons,
        checks=checks,
        file_comments=all_valid_comments,
        newcomer_explainer=merged.newcomer_explainer or "No newcomer explanation generated.",
        verdict=merged.verdict,
    )

    model_name = getattr(provider, "chat_model", "gemma3:4b")
    review_record = PRReviewModel(
        id=uuid.uuid4(),
        pr_id=pr.id,
        status="done",
        summary="\n".join(final_review.summary),
        risk_level=final_review.risk_level,
        checks=final_review.checks,
        file_comments=[c.model_dump() for c in final_review.file_comments],
        newcomer_explainer=final_review.newcomer_explainer,
        verdict=final_review.verdict,
        model=model_name,
        prompt_version="v1",
    )
    session.add(review_record)
    await session.flush()

    await record_audit(
        session=session,
        feature="review",
        action="pr_review",
        repo_id=repo.id,
        ref_type="pr",
        ref_id=str(pr.id),
        model=model_name,
        prompt_version="v1",
        tokens_in=total_tokens_in,
        tokens_out=total_tokens_out,
        latency_ms=total_latency_ms,
        outcome=overall_outcome,
    )
    await session.commit()

    result_payload = {
        "id": str(review_record.id),
        "pr_id": str(pr.id),
        "status": review_record.status,
        "summary": final_review.summary,
        "risk_level": final_review.risk_level,
        "risk_reasons": final_review.risk_reasons,
        "checks": final_review.checks,
        "file_comments": [c.model_dump() for c in final_review.file_comments],
        "newcomer_explainer": final_review.newcomer_explainer,
        "verdict": final_review.verdict,
        "model": review_record.model,
        "prompt_version": review_record.prompt_version,
        "created_at": review_record.created_at.isoformat() if review_record.created_at else None,
    }

    yield {
        "event": "result",
        "data": json.dumps(result_payload),
    }
    yield {
        "event": "done",
        "data": json.dumps({"status": "done"}),
    }
