from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import time
from typing import Any, Optional
import uuid

from sqlalchemy import select

from app.core.db import get_sessionmaker
from app.models.features import BenchmarkRun
from app.providers.base import LLMProvider
from app.providers.ollama import OllamaProvider
from app.schemas.llm import TriageResult
from app.services.structured import run_structured_pipeline

logger = logging.getLogger("app.services.benchmark")

BENCHMARK_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "benchmark_issues.json"

_cancelled_runs: set[uuid.UUID] = set()
_active_tasks: dict[uuid.UUID, asyncio.Task[Any]] = {}
_custom_provider_factories: dict[str, Any] = {}


def register_benchmark_provider(model_name: str, provider: LLMProvider) -> None:
    """Used in testing to mock providers for specific model names."""
    _custom_provider_factories[model_name] = provider


def unregister_benchmark_providers() -> None:
    _custom_provider_factories.clear()


def is_benchmark_cancelled(run_id: uuid.UUID) -> bool:
    return run_id in _cancelled_runs


def cancel_benchmark_run(run_id: uuid.UUID) -> bool:
    """Signals cancellation to a running benchmark and cancels its task if active."""
    _cancelled_runs.add(run_id)
    task = _active_tasks.get(run_id)
    if task and not task.done():
        task.cancel()
        return True
    return False


def load_benchmark_issues() -> list[dict[str, Any]]:
    if not BENCHMARK_FILE.exists():
        logger.error("Benchmark issues file not found at %s", BENCHMARK_FILE)
        return []
    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        return []


async def run_benchmark_for_model(
    run_id: uuid.UUID,
    model_name: str,
    sample_size: Optional[int] = None,
    provider: Optional[LLMProvider] = None,
) -> None:
    """Executes the triage task over benchmark_issues.json for a single model."""
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as session:
        stmt = select(BenchmarkRun).where(BenchmarkRun.id == run_id)
        res = await session.execute(stmt)
        run_record = res.scalar_one_or_none()
        if not run_record:
            logger.warning("Benchmark run %s not found in database", run_id)
            return

        if run_record.status == "cancelled" or is_benchmark_cancelled(run_id):
            run_record.status = "cancelled"
            await session.commit()
            return

        all_issues = load_benchmark_issues()
        if sample_size and sample_size > 0:
            selected_issues = all_issues[:sample_size]
        else:
            selected_issues = all_issues

        total_samples = len(selected_issues)
        run_record.sample_count = total_samples
        run_record.status = "running"
        run_record.details = {
            "completed": 0,
            "total": total_samples,
            "type_correct": 0,
            "severity_correct": 0,
            "json_valid_count": 0,
            "running_type_accuracy": 0.0,
            "running_severity_accuracy": 0.0,
        }
        await session.commit()

    # Determine provider
    llm_provider = provider
    if llm_provider is None:
        if model_name in _custom_provider_factories:
            llm_provider = _custom_provider_factories[model_name]
        elif "*" in _custom_provider_factories:
            llm_provider = _custom_provider_factories["*"]
        else:
            llm_provider = OllamaProvider(chat_model=model_name)

    type_correct = 0
    severity_correct = 0
    json_valid_count = 0
    sample_errors = 0
    last_sample_error: Optional[str] = None
    latencies_ms: list[int] = []
    tokens_out_list: list[int] = []
    start_time = time.perf_counter()

    try:
        for idx, item in enumerate(selected_issues):
            if is_benchmark_cancelled(run_id):
                async with sessionmaker() as session:
                    run_obj = await session.get(BenchmarkRun, run_id)
                    if run_obj:
                        run_obj.status = "cancelled"
                        await session.commit()
                return

            expected_type = str(item.get("expected_type", "")).strip().lower()
            expected_sev = str(item.get("expected_severity", "")).strip().upper()

            context_text = (
                f"Issue Number: #{item.get('number', idx + 1)}\n"
                f"Issue Title: {item.get('title', '')}\n"
                f"Issue Body:\n{item.get('body', '')}\n\n"
                f"Allowed Repository Labels:\n{json.dumps(['bug', 'feature', 'question', 'docs', 'chore', 'spam'])}\n\n"
                f"CONTRIBUTING Guidelines:\nPlease include clear reproduction steps and tests.\n\n"
                f"Candidate Duplicates (Similarity >= 0.82):\nNone found above 0.82 similarity threshold.\n"
            )

            fallback_triage = TriageResult(
                type="bug",
                severity="P2",
                labels=[],
                summary="Fallback triage for benchmark",
                missing_info=[],
                duplicates=[],
                good_first_issue_score=0,
                suggested_reply="Thank you for reporting.",
                confidence=0.0,
            )

            t0 = time.perf_counter()
            try:
                structured_res = await run_structured_pipeline(
                    provider=llm_provider,
                    task_name="triage",
                    context_text=context_text,
                    schema=TriageResult,
                    fallback=fallback_triage,
                    max_retries=1,
                )
                sample_latency = max(int((time.perf_counter() - t0) * 1000), 1)
                latencies_ms.append(sample_latency)

                if structured_res.outcome == "ok":
                    json_valid_count += 1

                tokens_out = structured_res.tokens_out or max(len(structured_res.raw_content) // 4, 1)
                tokens_out_list.append(tokens_out)

                res_data = structured_res.data
                actual_type = (res_data.type or "").strip().lower()
                actual_sev = (res_data.severity or "").strip().upper()

                if actual_type == expected_type:
                    type_correct += 1
                if actual_sev == expected_sev:
                    severity_correct += 1

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                sample_latency = max(int((time.perf_counter() - t0) * 1000), 1)
                latencies_ms.append(sample_latency)
                tokens_out_list.append(0)
                sample_errors += 1
                last_sample_error = str(exc)
                logger.warning("Sample %d failed on model %s: %s", idx, model_name, exc)

            completed = idx + 1
            # Update live progress details for UI polling
            async with sessionmaker() as session:
                run_obj = await session.get(BenchmarkRun, run_id)
                if run_obj:
                    if run_obj.status == "cancelled" or is_benchmark_cancelled(run_id):
                        run_obj.status = "cancelled"
                        await session.commit()
                        return
                    run_obj.details = {
                        "completed": completed,
                        "total": total_samples,
                        "type_correct": type_correct,
                        "severity_correct": severity_correct,
                        "json_valid_count": json_valid_count,
                        "running_type_accuracy": round(type_correct / completed, 4),
                        "running_severity_accuracy": round(severity_correct / completed, 4),
                    }
                    await session.commit()

        if is_benchmark_cancelled(run_id):
            async with sessionmaker() as session:
                run_obj = await session.get(BenchmarkRun, run_id)
                if run_obj:
                    run_obj.status = "cancelled"
                    await session.commit()
            return

        if sample_errors == total_samples and total_samples > 0:
            async with sessionmaker() as session:
                run_obj = await session.get(BenchmarkRun, run_id)
                if run_obj and run_obj.status != "cancelled":
                    run_obj.status = "failed"
                    run_obj.details = {"error": f"All {total_samples} samples failed: {last_sample_error}"}
                    await session.commit()
            return

        elapsed = max(time.perf_counter() - start_time, 0.001)
        async with sessionmaker() as session:
            run_obj = await session.get(BenchmarkRun, run_id)
            if run_obj and run_obj.status != "cancelled":
                run_obj.type_accuracy = round(type_correct / total_samples, 4) if total_samples > 0 else 0.0
                run_obj.severity_accuracy = round(severity_correct / total_samples, 4) if total_samples > 0 else 0.0
                run_obj.json_valid_rate = round(json_valid_count / total_samples, 4) if total_samples > 0 else 0.0
                run_obj.avg_latency_ms = int(sum(latencies_ms) / len(latencies_ms)) if latencies_ms else 0
                total_tokens = sum(tokens_out_list)
                run_obj.tokens_per_sec = round(total_tokens / elapsed, 2)
                run_obj.status = "done"
                await session.commit()

    except asyncio.CancelledError:
        logger.info("Benchmark run %s cancelled mid-run", run_id)
        async with sessionmaker() as session:
            run_obj = await session.get(BenchmarkRun, run_id)
            if run_obj:
                run_obj.status = "cancelled"
                await session.commit()
    except Exception as exc:
        logger.exception("Benchmark run %s failed: %s", run_id, exc)
        async with sessionmaker() as session:
            run_obj = await session.get(BenchmarkRun, run_id)
            if run_obj and run_obj.status != "cancelled":
                run_obj.status = "failed"
                run_obj.details = {"error": str(exc)}
                await session.commit()
    finally:
        _active_tasks.pop(run_id, None)
        _cancelled_runs.discard(run_id)


def start_benchmark_task(
    run_id: uuid.UUID,
    model_name: str,
    sample_size: Optional[int] = None,
    provider: Optional[LLMProvider] = None,
) -> asyncio.Task[None]:
    task = asyncio.create_task(
        run_benchmark_for_model(
            run_id=run_id,
            model_name=model_name,
            sample_size=sample_size,
            provider=provider,
        )
    )
    _active_tasks[run_id] = task
    return task
