from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import GitHubError, ValidationError
from app.core.security import encrypt_token
from app.models.core import Setting
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.services.github import verify_github_token

router = APIRouter(prefix="/settings", tags=["settings"])


class GitHubTokenRequest(BaseModel):
    token: str


def _to_response(setting: Setting) -> SettingsResponse:
    has_token = bool(setting.github_token_enc and setting.github_token_enc.strip())
    return SettingsResponse(
        ollama_base_url=setting.ollama_base_url,
        chat_model=setting.chat_model,
        embed_model=setting.embed_model,
        triage_mode=setting.triage_mode,
        spam_threshold=setting.spam_threshold,
        language=setting.language,
        offline_mode=setting.offline_mode,
        has_github_token=has_token,
        updated_at=setting.updated_at or datetime.now(timezone.utc),
    )


@router.get("", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsResponse:
    stmt = select(Setting).where(Setting.id == 1)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = Setting(id=1)
        db.add(setting)
        await db.commit()
        await db.refresh(setting)
    return _to_response(setting)


@router.put("", response_model=SettingsResponse)
async def update_settings(
    update: SettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    stmt = select(Setting).where(Setting.id == 1)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = Setting(id=1)
        db.add(setting)

    if update.ollama_base_url is not None:
        setting.ollama_base_url = update.ollama_base_url
    if update.chat_model is not None:
        setting.chat_model = update.chat_model
    if update.embed_model is not None:
        setting.embed_model = update.embed_model
    if update.triage_mode is not None:
        setting.triage_mode = update.triage_mode
    if update.spam_threshold is not None:
        setting.spam_threshold = update.spam_threshold
    if update.language is not None:
        setting.language = update.language
    if update.offline_mode is not None:
        setting.offline_mode = update.offline_mode

    setting.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(setting)
    return _to_response(setting)


@router.put("/github-token")
async def update_github_token(
    payload: GitHubTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    token = payload.token.strip()
    if not token:
        raise ValidationError("GitHub token cannot be empty")

    # Verify the token against GitHub before saving
    try:
        await verify_github_token(token)
    except GitHubError as exc:
        raise GitHubError(f"GitHub token verification failed: {exc.message}") from exc
    except Exception as exc:
        raise GitHubError(f"Failed to verify token with GitHub: {exc}") from exc

    stmt = select(Setting).where(Setting.id == 1)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = Setting(id=1)
        db.add(setting)

    setting.github_token_enc = encrypt_token(token)
    setting.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "ok", "has_github_token": True}


@router.delete("/github-token")
async def delete_github_token(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    stmt = select(Setting).where(Setting.id == 1)
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()
    if setting is not None:
        setting.github_token_enc = None
        setting.updated_at = datetime.now(timezone.utc)
        await db.commit()
    return {"status": "ok", "has_github_token": False}

