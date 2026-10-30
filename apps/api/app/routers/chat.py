from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
from typing import Any
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from app.core.db import get_db
from app.core.errors import NotFoundError
from app.models.core import Repository
from app.models.features import ChatMessage, ChatSession
from app.providers.factory import get_provider
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatMessageResponse,
    ChatSessionCreateRequest,
    ChatSessionDetailResponse,
    ChatSessionResponse,
)
from app.services.rag import (
    build_rag_prompt,
    process_citations,
    retrieve_rag_context,
)

logger = logging.getLogger("app.routers.chat")

router = APIRouter(tags=["chat"])


@router.post("/repos/{id}/chat/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    id: str,
    payload: ChatSessionCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """Creates a new chat session for a repository with mode (newcomer/expert) and language."""
    try:
        repo_uuid = uuid.UUID(id)
    except ValueError:
        raise NotFoundError(f"Repository '{id}' not found.")

    # Verify repository exists
    stmt = select(Repository.id).where(Repository.id == repo_uuid)
    res = await db.execute(stmt)
    if res.scalar_one_or_none() is None:
        raise NotFoundError(f"Repository '{id}' not found.")

    session_obj = ChatSession(
        repo_id=repo_uuid,
        mode=payload.mode,
        language=payload.language,
    )
    db.add(session_obj)
    await db.commit()
    await db.refresh(session_obj)

    now = datetime.now(timezone.utc)
    return ChatSessionResponse(
        id=str(session_obj.id),
        repo_id=str(session_obj.repo_id),
        mode=session_obj.mode,
        language=session_obj.language,
        created_at=session_obj.created_at or now,
    )


@router.get("/chat/sessions/{sid}", response_model=ChatSessionDetailResponse)
async def get_chat_session(
    sid: str,
    db: AsyncSession = Depends(get_db),
) -> ChatSessionDetailResponse:
    """Retrieves session details and its full conversation message history."""
    try:
        session_uuid = uuid.UUID(sid)
    except ValueError:
        raise NotFoundError(f"Chat session '{sid}' not found.")

    stmt = select(ChatSession).where(ChatSession.id == session_uuid)
    res = await db.execute(stmt)
    session_obj = res.scalar_one_or_none()
    if session_obj is None:
        raise NotFoundError(f"Chat session '{sid}' not found.")

    stmt_msgs = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_uuid)
        .order_by(ChatMessage.created_at.asc())
    )
    res_msgs = await db.execute(stmt_msgs)
    messages = res_msgs.scalars().all()

    return ChatSessionDetailResponse(
        id=str(session_obj.id),
        repo_id=str(session_obj.repo_id),
        mode=session_obj.mode,
        language=session_obj.language,
        created_at=session_obj.created_at,
        messages=[
            ChatMessageResponse(
                id=str(m.id),
                session_id=str(m.session_id),
                role=m.role,
                content=m.content,
                citations=m.citations or [],
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/chat/sessions/{sid}")
async def delete_chat_session(
    sid: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Deletes a chat session and cascades all messages."""
    try:
        session_uuid = uuid.UUID(sid)
    except ValueError:
        raise NotFoundError(f"Chat session '{sid}' not found.")

    stmt = select(ChatSession).where(ChatSession.id == session_uuid)
    res = await db.execute(stmt)
    session_obj = res.scalar_one_or_none()
    if session_obj is None:
        raise NotFoundError(f"Chat session '{sid}' not found.")

    await db.delete(session_obj)
    await db.commit()

    return {"status": "deleted", "id": str(session_uuid)}


@router.post("/chat/sessions/{sid}/messages")
async def send_chat_message(
    sid: str,
    payload: ChatMessageCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Appends a user message and streams the assistant response via Server-Sent Events.
    Events: token, citation, done. Ping sent every 15s. Stops when client disconnects.
    """
    try:
        session_uuid = uuid.UUID(sid)
    except ValueError:
        raise NotFoundError(f"Chat session '{sid}' not found.")

    stmt = select(ChatSession).where(ChatSession.id == session_uuid)
    res = await db.execute(stmt)
    session_obj = res.scalar_one_or_none()
    if session_obj is None:
        raise NotFoundError(f"Chat session '{sid}' not found.")

    # Persist user message
    user_msg = ChatMessage(
        session_id=session_uuid,
        role="user",
        content=payload.content,
        citations=[],
    )
    db.add(user_msg)
    await db.commit()

    # Load recent conversation history (last 6 messages)
    stmt_history = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_uuid)
        .order_by(ChatMessage.created_at.desc())
        .limit(6)
    )
    res_history = await db.execute(stmt_history)
    history_rows = list(reversed(res_history.scalars().all()))
    history: list[dict[str, str]] = [
        {"role": m.role, "content": m.content}
        for m in history_rows
        if m.id != user_msg.id
    ]

    provider = await get_provider(db)

    # Retrieve RAG context
    rag_ctx = await retrieve_rag_context(
        session=db,
        repo_id=session_obj.repo_id,
        query=payload.content,
        provider=provider,
    )

    async def event_generator():
        accumulated_chunks: list[str] = []
        assistant_msg_id = uuid.uuid4()

        if rag_ctx.is_low_confidence:
            fallback = rag_ctx.fallback_answer or "I could not find this in the repo."
            # Stream fallback tokens
            words = fallback.split(" ")
            for i, word in enumerate(words):
                if await request.is_disconnected():
                    return
                token = word if i == 0 else f" {word}"
                accumulated_chunks.append(token)
                yield {
                    "event": "token",
                    "data": json.dumps({"text": token}),
                }
                await asyncio.sleep(0.01)

            # Persist assistant response
            full_text = "".join(accumulated_chunks)
            asst_msg = ChatMessage(
                id=assistant_msg_id,
                session_id=session_uuid,
                role="assistant",
                content=full_text,
                citations=[],
            )
            db.add(asst_msg)
            await db.commit()

            yield {
                "event": "done",
                "data": json.dumps({"message_id": str(assistant_msg_id)}),
            }
            return

        # Normal confidence RAG generation
        messages = build_rag_prompt(
            context=rag_ctx,
            user_query=payload.content,
            mode=session_obj.mode,
            language=session_obj.language,
            history=history,
        )

        try:
            async for token in provider.chat_stream(messages):
                if await request.is_disconnected():
                    logger.info("Client disconnected during chat generation")
                    return
                accumulated_chunks.append(token)
                yield {
                    "event": "token",
                    "data": json.dumps({"text": token}),
                }
        except Exception as exc:
            logger.error("Chat generation failed: %s", exc)
            yield {
                "event": "error",
                "data": json.dumps({"code": "llm_unavailable", "message": str(exc)}),
            }
            yield {
                "event": "done",
                "data": json.dumps({"message_id": str(assistant_msg_id)}),
            }
            return

        raw_response = "".join(accumulated_chunks)
        cleaned_text, valid_citations = process_citations(raw_response, rag_ctx.excerpt_map)

        # Stream citation events
        for citation in valid_citations:
            if await request.is_disconnected():
                return
            yield {
                "event": "citation",
                "data": json.dumps(citation),
            }

        # Persist assistant message with citations
        asst_msg = ChatMessage(
            id=assistant_msg_id,
            session_id=session_uuid,
            role="assistant",
            content=cleaned_text,
            citations=valid_citations,
        )
        db.add(asst_msg)
        await db.commit()

        yield {
            "event": "done",
            "data": json.dumps({"message_id": str(assistant_msg_id)}),
        }

    return EventSourceResponse(
        event_generator(),
        ping=15,
        ping_message_factory=lambda: ServerSentEvent(comment="ping"),
    )
