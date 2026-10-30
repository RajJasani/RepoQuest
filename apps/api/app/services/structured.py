from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Any, Callable, Generic, Optional, TypeVar, Union

from pydantic import BaseModel, ValidationError

from app.core.errors import InvalidLLMOutputError
from app.providers.base import LLMProvider, Msg
from app.services.redact import redact_secrets

logger = logging.getLogger("app.services.structured")

T = TypeVar("T", bound=BaseModel)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "v1"


def load_prompt_text(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def extract_json_from_text(text: str) -> Any:
    """Extracts and parses JSON from text, handling markdown code fences if present."""
    trimmed = text.strip()
    if trimmed.startswith("```"):
        # Strip opening fence (```json or ```)
        lines = trimmed.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            if lines[-1].strip() == "```":
                trimmed = "\n".join(lines[1:-1]).strip()
            else:
                trimmed = "\n".join(lines[1:]).strip()
    return json.loads(trimmed)


@dataclass
class StructuredResult(Generic[T]):
    data: T
    raw_content: str
    outcome: str  # "ok" or "invalid_llm_output"
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    latency_ms: Optional[int] = None
    retries: int = 0
    error: Optional[str] = None


async def run_structured_pipeline(
    provider: LLMProvider,
    task_name: str,
    context_text: str,
    schema: type[T],
    *,
    system_preamble: Optional[str] = None,
    post_validate: Optional[Callable[[T], T]] = None,
    fallback: Optional[Union[T, Callable[[], T]]] = None,
    max_retries: int = 2,
    temperature: float = 0.2,
) -> StructuredResult[T]:
    """
    Executes the 5-step structured output pipeline from PRD §12.2:
    1. Build messages from versioned prompt file (prompts/v1/<task>.md) and preamble.
    2. Call chat with schema as format, temperature 0.2.
    3. Parse JSON, validate with Pydantic. Retry up to 2 times on error with repair message.
    4. Post-validate in code (drop or fix invalid items).
    5. Return safe fallback on failure and record outcome.
    """
    preamble = system_preamble or load_prompt_text("preamble")
    task_instructions = load_prompt_text(task_name)
    sanitized_context = redact_secrets(context_text)

    user_prompt = f"{task_instructions}\n\n=== CONTEXT ===\n{sanitized_context}"

    messages: list[Msg] = [
        Msg(role="system", content=preamble),
        Msg(role="user", content=user_prompt),
    ]

    json_schema = schema.model_json_schema()

    total_tokens_in = 0
    total_tokens_out = 0
    total_latency_ms = 0
    last_raw_content = ""
    last_error_msg = ""

    for attempt in range(max_retries + 1):
        chat_res = await provider.chat(
            messages=messages,
            schema=json_schema,
            temperature=temperature,
        )

        last_raw_content = chat_res.content
        if chat_res.tokens_in:
            total_tokens_in += chat_res.tokens_in
        if chat_res.tokens_out:
            total_tokens_out += chat_res.tokens_out
        if chat_res.latency_ms:
            total_latency_ms += chat_res.latency_ms

        try:
            parsed_json = extract_json_from_text(chat_res.content)
            validated_obj = schema.model_validate(parsed_json)

            if post_validate is not None:
                validated_obj = post_validate(validated_obj)

            return StructuredResult(
                data=validated_obj,
                raw_content=last_raw_content,
                outcome="ok",
                tokens_in=total_tokens_in if total_tokens_in > 0 else None,
                tokens_out=total_tokens_out if total_tokens_out > 0 else None,
                latency_ms=total_latency_ms if total_latency_ms > 0 else None,
                retries=attempt,
                error=None,
            )
        except (json.JSONDecodeError, ValidationError, Exception) as exc:
            last_error_msg = str(exc)
            logger.warning(
                "Structured output validation failed on attempt %d for task %s: %s",
                attempt,
                task_name,
                last_error_msg,
            )

            if attempt < max_retries:
                repair_prompt = (
                    f"Your previous response failed validation with the following error:\n"
                    f"{last_error_msg}\n"
                    f"Please correct the output. Respond ONLY with valid JSON conforming strictly to the requested schema."
                )
                messages.append(Msg(role="assistant", content=chat_res.content))
                messages.append(Msg(role="user", content=repair_prompt))

    # All retries failed
    logger.error(
        "Structured output pipeline failed after %d retries for task %s. Error: %s",
        max_retries,
        task_name,
        last_error_msg,
    )

    if fallback is not None:
        fallback_data = fallback() if callable(fallback) else fallback
        return StructuredResult(
            data=fallback_data,
            raw_content=last_raw_content,
            outcome="invalid_llm_output",
            tokens_in=total_tokens_in if total_tokens_in > 0 else None,
            tokens_out=total_tokens_out if total_tokens_out > 0 else None,
            latency_ms=total_latency_ms if total_latency_ms > 0 else None,
            retries=max_retries,
            error=last_error_msg,
        )

    raise InvalidLLMOutputError(
        message=f"Structured output pipeline failed after {max_retries} retries: {last_error_msg}",
        details={"task": task_name, "raw_content": last_raw_content},
    )
