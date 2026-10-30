"""Data formatting utilities."""

from typing import Any, Mapping


def format_task_summary(task_data: Mapping[str, Any]) -> str:
    """Formats a task mapping into a clean human-readable string."""
    task_id = task_data.get("id", "?")
    title = task_data.get("title", "Untitled")
    status = task_data.get("status", "unknown").upper()
    return f"[{status}] #{task_id} - {title}"


def slugify(text: str) -> str:
    """Converts a title or label into a url-friendly slug."""
    return "-".join(text.lower().strip().split())
