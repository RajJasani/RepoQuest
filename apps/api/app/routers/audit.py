from __future__ import annotations

import logging
import math
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError, ConflictError, NotFoundError
from app.core.security import decrypt_token
from app.models.core import AuditLog, Repository, Setting
from app.models.features import Issue
from app.schemas.audit import AuditItemResponse, AuditListResponse, AuditUndoResponse
from app.services.audit import record_audit
from app.services.github import GitHubClient

logger = logging.getLogger("app.routers.audit")

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditListResponse)
async def list_audit_logs(
    feature: Optional[str] = Query(None, description="Filter by feature name"),
    repo_id: Optional[str] = Query(None, description="Filter by repository UUID"),
    page: int = Query(1, ge=1, description="Page number (>=1)"),
    page_size: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    db: AsyncSession = Depends(get_db),
) -> AuditListResponse:
    """Returns paginated audit log entries ordered by timestamp descending."""
    stmt = select(AuditLog)

    if feature:
        stmt = stmt.where(AuditLog.feature == feature.strip())

    if repo_id:
        try:
            repo_uuid = uuid.UUID(repo_id.strip())
            stmt = stmt.where(AuditLog.repo_id == repo_uuid)
        except ValueError:
            raise NotFoundError(message=f"Invalid repository UUID '{repo_id}'")

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await db.execute(count_stmt)
    total = total_res.scalar_one() or 0

    stmt = stmt.order_by(AuditLog.ts.desc()).offset((page - 1) * page_size).limit(page_size)
    res = await db.execute(stmt)
    rows = res.scalars().all()

    pages = max(math.ceil(total / page_size), 1)

    return AuditListResponse(
        items=[AuditItemResponse.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post("/{id}/undo", response_model=AuditUndoResponse)
async def undo_audit_action(
    id: str,
    db: AsyncSession = Depends(get_db),
) -> AuditUndoResponse:
    """
    Undoes a previously applied action (e.g. applied labels).
    Removes applied labels through GitHubClient or simulated for demo repositories.
    Refuses to undo comments with a clear explanatory message.
    """
    try:
        audit_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(message=f"Invalid audit entry ID '{id}'")

    stmt = select(AuditLog).where(AuditLog.id == audit_uuid)
    res = await db.execute(stmt)
    entry = res.scalar_one_or_none()
    if not entry:
        raise NotFoundError(message=f"Audit entry '{id}' not found")

    if entry.undone:
        raise ConflictError(message="This action has already been undone.")

    # Refuse to undo comments with a clear message
    is_comment_action = entry.action in ("comment", "post_comment", "post_issue_comment", "review_comment")
    if is_comment_action:
        raise AppError(
            message="Comments cannot be un-posted automatically. Please delete the comment directly on GitHub.",
            code="cannot_undo",
            status_code=400,
        )

    payload = entry.undo_payload
    if not payload or not isinstance(payload, dict):
        raise AppError(
            message="This action does not have an undoable payload.",
            code="cannot_undo",
            status_code=400,
        )

    applied_labels = payload.get("applied_labels") or []
    previous_labels = payload.get("previous_labels") or []
    labels_to_remove = [lbl for lbl in applied_labels if lbl not in previous_labels]
    if not labels_to_remove and applied_labels:
        labels_to_remove = list(applied_labels)

    if not labels_to_remove:
        if payload.get("comment") or payload.get("suggested_reply"):
            raise AppError(
                message="Comments cannot be un-posted automatically. Please delete the comment directly on GitHub.",
                code="cannot_undo",
                status_code=400,
            )
        entry.undone = True
        await db.commit()
        return AuditUndoResponse(
            status="ok",
            message="Action marked undone (no labels required removal).",
            removed_labels=[],
            undone=True,
        )

    # Revert labels on GitHub (or simulated) and locally
    if entry.repo_id:
        repo = await db.get(Repository, entry.repo_id)
        if repo:
            is_demo = (repo.owner.lower() == "demo") or payload.get("simulated", False)
            if not is_demo:
                stmt_s = select(Setting).where(Setting.id == 1)
                res_s = await db.execute(stmt_s)
                setting = res_s.scalar_one_or_none()
                token = None
                if setting and setting.github_token_enc:
                    try:
                        token = decrypt_token(setting.github_token_enc)
                    except Exception:
                        pass
                gh = GitHubClient(token=token)
            else:
                gh = GitHubClient()

            issue_number = None
            if entry.ref_id:
                try:
                    issue_number = int(entry.ref_id)
                except ValueError:
                    pass

            if issue_number:
                for lbl in labels_to_remove:
                    try:
                        await gh.remove_label(repo.owner, repo.name, issue_number, lbl)
                    except Exception as exc:
                        logger.warning("Failed to remove label %s on GitHub: %s", lbl, exc)

                # Revert issue's labels in DB
                stmt_issue = select(Issue).where(
                    Issue.repo_id == repo.id,
                    Issue.number == issue_number,
                )
                res_issue = await db.execute(stmt_issue)
                issue_obj = res_issue.scalar_one_or_none()
                if issue_obj:
                    issue_obj.labels = previous_labels
                    issue_obj.triage_status = "untriaged"

    entry.undone = True

    # Record undo action in audit log
    await record_audit(
        session=db,
        feature=entry.feature,
        action="undo",
        repo_id=entry.repo_id,
        ref_type=entry.ref_type,
        ref_id=entry.ref_id,
        outcome="ok",
        undo_payload={"undone_audit_id": str(entry.id), "removed_labels": labels_to_remove},
    )

    await db.commit()

    return AuditUndoResponse(
        status="ok",
        message=f"Successfully removed labels: {', '.join(labels_to_remove)}",
        removed_labels=labels_to_remove,
        undone=True,
    )

