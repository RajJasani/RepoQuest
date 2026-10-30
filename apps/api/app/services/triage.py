from __future__ import annotations

import json
import logging
from typing import Any, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_token
from app.models.core import Repository, Setting
from app.models.features import Issue, IssueAnalysis
from app.providers.base import LLMProvider
from app.schemas.llm import TriageResult
from app.services.audit import record_audit
from app.services.github import GitHubClient
from app.services.rag import cosine_sim
from app.services.structured import run_structured_pipeline

logger = logging.getLogger("app.services.triage")

PROMPT_VERSION = "v1"


async def find_candidate_duplicates(
    session: AsyncSession,
    repo_id: uuid.UUID,
    issue_id: uuid.UUID,
    query_embedding: list[float],
) -> list[tuple[Issue, float]]:
    """
    Finds candidate duplicates using the Section 10 SQL query:
    SELECT id, number, title, 1 - (embedding <=> :q) AS sim
    FROM issues
    WHERE repo_id = :repo AND id <> :self AND embedding IS NOT NULL
    ORDER BY embedding <=> :q LIMIT 5;
    Filters candidates with sim >= 0.82.
    """
    if not query_embedding:
        return []

    candidates: list[tuple[Issue, float]] = []
    try:
        stmt = (
            select(
                Issue,
                (1.0 - Issue.embedding.cosine_distance(query_embedding)).label("sim"),
            )
            .where(
                Issue.repo_id == repo_id,
                Issue.id != issue_id,
                Issue.embedding.isnot(None),
            )
            .order_by(Issue.embedding.cosine_distance(query_embedding).asc())
            .limit(5)
        )
        res = await session.execute(stmt)
        for row in res.all():
            cand_issue = row[0]
            sim = float(row[1]) if row[1] is not None else 0.0
            if sim >= 0.82:
                candidates.append((cand_issue, round(sim, 3)))
        if candidates:
            return candidates
    except Exception:
        pass

    # Python calculation fallback for SQLite / mocks
    try:
        stmt = select(Issue).where(
            Issue.repo_id == repo_id,
            Issue.id != issue_id,
            Issue.embedding.isnot(None),
        )
        res = await session.execute(stmt)
        scored = []
        for cand_issue in res.scalars().all():
            if cand_issue.embedding:
                sim = cosine_sim(query_embedding, cand_issue.embedding)
                if sim >= 0.82:
                    scored.append((cand_issue, round(sim, 3)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:5]
    except Exception:
        return candidates


def build_triage_context(
    issue: Issue,
    repo: Repository,
    duplicate_candidates: list[tuple[Issue, float]],
) -> str:
    """Formats context for the triage prompt template."""
    allowed_labels = repo.labels or []
    dup_lines = [
        f"- Issue #{cand.number}: '{cand.title}' (Similarity: {sim})"
        for cand, sim in duplicate_candidates
    ]
    duplicates_text = "\n".join(dup_lines) if dup_lines else "None found above 0.82 similarity threshold."

    return (
        f"Issue Number: #{issue.number}\n"
        f"Issue Title: {issue.title}\n"
        f"Issue Author: {issue.author or 'Unknown'}\n"
        f"Issue Body:\n{issue.body or 'No description provided.'}\n\n"
        f"Allowed Repository Labels:\n{json.dumps(allowed_labels)}\n\n"
        f"CONTRIBUTING Guidelines:\n{repo.contributing_md or 'No specific contributing guidelines provided.'}\n\n"
        f"Candidate Duplicates (Similarity >= 0.82):\n{duplicates_text}\n"
    )


async def triage_issue(
    session: AsyncSession,
    issue: Issue,
    repo: Repository,
    provider: LLMProvider,
    settings_row: Optional[Setting] = None,
    github_client: Optional[GitHubClient] = None,
) -> IssueAnalysis:
    """
    Runs automated issue triage via the structured output pipeline:
    1. Embeds issue if not already embedded.
    2. Runs duplicate search (similarity >= 0.82).
    3. Calls structured output pipeline with TriageResult and up to 2 repair retries.
    4. Post-validates labels against repo.labels whitelist in code.
    5. Falls back to 'needs_human' on invalid LLM output.
    6. Stores IssueAnalysis and logs audit entry.
    7. Applies Auto mode if settings_row.triage_mode == 'auto'.
    """
    # 1. Ensure issue has an embedding
    if not issue.embedding:
        combo_text = f"{issue.title}\n{issue.body or ''}".strip()
        embs = await provider.embed([combo_text])
        if embs:
            issue.embedding = embs[0]
            await session.flush()

    # 2. Find duplicates
    candidate_dups = await find_candidate_duplicates(
        session=session,
        repo_id=repo.id,
        issue_id=issue.id,
        query_embedding=issue.embedding or [],
    )

    context_text = build_triage_context(issue, repo, candidate_dups)
    allowed_labels_set = set(repo.labels or [])

    # Post-validation: filter labels to repo whitelist
    def post_validate_triage(result: TriageResult) -> TriageResult:
        result.labels = [lbl for lbl in result.labels if lbl in allowed_labels_set]
        # Keep confirmed duplicates that were actually candidate duplicates
        candidate_numbers = {cand.number for cand, _ in candidate_dups}
        result.duplicates = [d for d in result.duplicates if d.number in candidate_numbers]
        return result

    # Fallback if LLM output fails after 2 repair retries
    fallback_result = TriageResult(
        type="bug",
        severity="P2",
        labels=[],
        summary="Automatic triage could not be determined. Needs human review.",
        missing_info=[],
        duplicates=[],
        good_first_issue_score=0,
        suggested_reply="Thank you for reporting this issue. A maintainer will review it shortly.",
        confidence=0.0,
    )

    # 3. Run structured pipeline
    structured_res = await run_structured_pipeline(
        provider=provider,
        task_name="triage",
        context_text=context_text,
        schema=TriageResult,
        post_validate=post_validate_triage,
        fallback=fallback_result,
        max_retries=2,
    )

    triage_data = structured_res.data
    chat_model = getattr(provider, "chat_model", "ollama")

    if structured_res.outcome == "invalid_llm_output":
        issue.triage_status = "needs_human"
    else:
        issue.triage_status = "suggested"

    # 4. Save IssueAnalysis record
    analysis = IssueAnalysis(
        id=uuid.uuid4(),
        issue_id=issue.id,
        type=triage_data.type,
        severity=triage_data.severity,
        labels=triage_data.labels,
        summary=triage_data.summary,
        missing_info=triage_data.missing_info,
        duplicates=[d.model_dump() for d in triage_data.duplicates],
        good_first_issue_score=triage_data.good_first_issue_score,
        suggested_reply=triage_data.suggested_reply,
        confidence=triage_data.confidence,
        model=chat_model,
        prompt_version=PROMPT_VERSION,
    )
    session.add(analysis)

    # 5. Record Audit log
    await record_audit(
        session=session,
        feature="triage",
        action="triage",
        repo_id=repo.id,
        ref_type="issue",
        ref_id=str(issue.number),
        model=chat_model,
        prompt_version=PROMPT_VERSION,
        tokens_in=structured_res.tokens_in,
        tokens_out=structured_res.tokens_out,
        latency_ms=structured_res.latency_ms,
        outcome=structured_res.outcome,
    )

    # 6. Check Auto mode: apply labels and post comment if settings.triage_mode == 'auto'
    if (
        structured_res.outcome == "ok"
        and settings_row
        and settings_row.triage_mode == "auto"
    ):
        await apply_auto_triage(
            session=session,
            issue=issue,
            repo=repo,
            analysis=analysis,
            settings_row=settings_row,
            github_client=github_client,
        )

    await session.commit()
    return analysis


async def apply_auto_triage(
    session: AsyncSession,
    issue: Issue,
    repo: Repository,
    analysis: IssueAnalysis,
    settings_row: Setting,
    github_client: Optional[GitHubClient] = None,
) -> None:
    """Applies labels and comment automatically in Auto mode if write token is present."""
    token: Optional[str] = None
    if settings_row.github_token_enc:
        try:
            token = decrypt_token(settings_row.github_token_enc)
        except Exception:
            pass

    original_labels = list(issue.labels or [])
    labels_to_apply = list(analysis.labels or [])
    undo_payload = {
        "previous_labels": original_labels,
        "applied_labels": labels_to_apply,
    }

    posted_to_github = False
    if token:
        gh = github_client or GitHubClient(token=token)
        try:
            if labels_to_apply:
                await gh.add_labels(repo.owner, repo.name, issue.number, labels_to_apply)
            if analysis.suggested_reply:
                await gh.post_issue_comment(repo.owner, repo.name, issue.number, analysis.suggested_reply)
            posted_to_github = True
        except Exception as exc:
            logger.warning("Auto triage GitHub write failed: %s", exc)

    issue.labels = labels_to_apply
    issue.triage_status = "applied" if posted_to_github else "approved"

    await record_audit(
        session=session,
        feature="triage",
        action="apply_auto",
        repo_id=repo.id,
        ref_type="issue",
        ref_id=str(issue.number),
        outcome="ok",
        undo_payload=undo_payload,
    )


async def approve_issue(
    session: AsyncSession,
    issue: Issue,
    repo: Repository,
    settings_row: Optional[Setting] = None,
    labels: Optional[list[str]] = None,
    comment: Optional[str] = None,
    post_to_github: bool = False,
    github_client: Optional[GitHubClient] = None,
) -> dict[str, Any]:
    """
    Approves an issue's triage results. Applies labels and posts comment to GitHub
    if write token exists, otherwise applies locally and returns comment for copying.
    Stores undo_payload in the audit log.
    """
    # Fetch latest analysis if fields not explicitly provided
    latest_analysis: Optional[IssueAnalysis] = None
    stmt_a = (
        select(IssueAnalysis)
        .where(IssueAnalysis.issue_id == issue.id)
        .order_by(IssueAnalysis.created_at.desc())
        .limit(1)
    )
    res_a = await session.execute(stmt_a)
    latest_analysis = res_a.scalar_one_or_none()

    # Determine final labels (whitelisted against repo.labels)
    allowed_labels = set(repo.labels or [])
    raw_labels = labels if labels is not None else (latest_analysis.labels if latest_analysis else issue.labels or [])
    final_labels = [lbl for lbl in raw_labels if lbl in allowed_labels]

    final_comment = comment if comment is not None else (
        latest_analysis.suggested_reply if latest_analysis else None
    )

    original_labels = list(issue.labels or [])
    undo_payload = {
        "previous_labels": original_labels,
        "applied_labels": final_labels,
    }

    posted_to_github_success = False

    if repo.owner.lower() == "demo":
        gh = github_client or GitHubClient()
        simulated_res = {}
        if final_labels:
            simulated_res["labels"] = await gh.add_labels(repo.owner, repo.name, issue.number, final_labels)
        if final_comment:
            simulated_res["comment"] = await gh.post_issue_comment(repo.owner, repo.name, issue.number, final_comment)

        issue.labels = final_labels
        issue.triage_status = "applied"
        undo_payload["simulated"] = True

        await record_audit(
            session=session,
            feature="triage",
            action="approve",
            repo_id=repo.id,
            ref_type="issue",
            ref_id=str(issue.number),
            outcome="ok",
            undo_payload=undo_payload,
        )
        await session.commit()

        return {
            "status": "Applied (demo)",
            "issue_id": str(issue.id),
            "labels": final_labels,
            "comment": final_comment,
            "posted_to_github": True,
            "simulated": True,
            "request": simulated_res,
        }

    if post_to_github:
        token: Optional[str] = None
        if settings_row and settings_row.github_token_enc:
            try:
                token = decrypt_token(settings_row.github_token_enc)
            except Exception:
                pass

        if token:
            gh = github_client or GitHubClient(token=token)
            if final_labels:
                await gh.add_labels(repo.owner, repo.name, issue.number, final_labels)
            if final_comment:
                await gh.post_issue_comment(repo.owner, repo.name, issue.number, final_comment)
            posted_to_github_success = True

    issue.labels = final_labels
    issue.triage_status = "applied" if posted_to_github_success else "approved"

    # Record audit log
    await record_audit(
        session=session,
        feature="triage",
        action="approve",
        repo_id=repo.id,
        ref_type="issue",
        ref_id=str(issue.number),
        outcome="ok",
        undo_payload=undo_payload,
    )
    await session.commit()

    return {
        "status": issue.triage_status,
        "issue_id": str(issue.id),
        "labels": final_labels,
        "comment": final_comment,
        "posted_to_github": posted_to_github_success,
    }


async def reject_issue(
    session: AsyncSession,
    issue: Issue,
    repo_id: uuid.UUID,
) -> dict[str, Any]:
    """Marks an issue as rejected and records audit entry."""
    issue.triage_status = "rejected"
    await record_audit(
        session=session,
        feature="triage",
        action="reject",
        repo_id=repo_id,
        ref_type="issue",
        ref_id=str(issue.number),
        outcome="ok",
    )
    await session.commit()
    return {"status": "rejected", "issue_id": str(issue.id)}
