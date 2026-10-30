"""Task filtering and query helper functions."""

from typing import Iterable, List
from tasks.models import Task


def filter_tasks_by_status(tasks: Iterable[Task], target_status: str) -> List[Task]:
    """Filters in-memory collection of tasks by status."""
    return [t for t in tasks if t.status == target_status]


def filter_unassigned_tasks(tasks: Iterable[Task]) -> List[Task]:
    """Returns all tasks without an assignee."""
    return [t for t in tasks if t.assignee_id is None]
