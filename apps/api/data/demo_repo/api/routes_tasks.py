"""Task API endpoint handlers."""

from typing import Tuple
from auth.service import AuthService
from tasks.filters import filter_tasks_by_status
from tasks.service import TaskService


class TaskHandler:
    def __init__(self, task_service: TaskService, auth_service: AuthService):
        self.task_service = task_service
        self.auth_service = auth_service

    def handle_list_tasks(self, status: str = None) -> Tuple[int, dict]:
        """Lists tasks, optionally filtering by status."""
        tasks = self.task_service.list_tasks(status=status)
        return 200, {"tasks": [t.to_dict() for t in tasks]}

    def handle_create_task(self, payload: dict) -> Tuple[int, dict]:
        """Creates a new task."""
        title = payload.get("title")
        if not title:
            return 400, {"error": "Title is required"}
        desc = payload.get("description")
        assignee_id = payload.get("assignee_id")

        task = self.task_service.create_task(title=title, description=desc, assignee_id=assignee_id)
        return 201, {"task": task.to_dict()}

    def handle_update_status(self, task_id: int, payload: dict) -> Tuple[int, dict]:
        """Updates the status of an existing task."""
        new_status = payload.get("status")
        if not new_status:
            return 400, {"error": "Status is required"}
        try:
            updated = self.task_service.update_task_status(task_id, new_status)
            if not updated:
                return 404, {"error": "Task not found"}
            return 200, {"task": updated.to_dict()}
        except ValueError as exc:
            return 400, {"error": str(exc)}

