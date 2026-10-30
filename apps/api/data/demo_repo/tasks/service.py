"""Task service providing CRUD operations."""

import sqlite3
from typing import List, Optional

from tasks.models import Task
from utils.formatters import format_task_summary


class TaskService:
    def __init__(self, connection: sqlite3.Connection):
        self.conn = connection

    def create_task(self, title: str, description: Optional[str] = None, assignee_id: Optional[int] = None) -> Task:
        """Creates a new task in backlog state."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO tasks (title, description, status, assignee_id) VALUES (?, ?, 'backlog', ?)",
            (title.strip(), description.strip() if description else None, assignee_id),
        )
        self.conn.commit()
        task_id = cursor.lastrowid
        return Task(
            id=task_id,
            title=title,
            description=description,
            status="backlog",
            assignee_id=assignee_id,
        )

    def get_task(self, task_id: int) -> Optional[Task]:
        """Retrieves a single task by id."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, title, description, status, assignee_id, created_at, updated_at FROM tasks WHERE id = ?",
            (task_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            assignee_id=row["assignee_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """Lists all tasks with optional status filter."""
        cursor = self.conn.cursor()
        if status:
            cursor.execute(
                "SELECT id, title, description, status, assignee_id, created_at, updated_at FROM tasks WHERE status = ? ORDER BY id DESC",
                (status,),
            )
        else:
            cursor.execute(
                "SELECT id, title, description, status, assignee_id, created_at, updated_at FROM tasks ORDER BY id DESC"
            )

        rows = cursor.fetchall()
        return [
            Task(
                id=r["id"],
                title=r["title"],
                description=r["description"],
                status=r["status"],
                assignee_id=r["assignee_id"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    def update_task_status(self, task_id: int, new_status: str) -> Optional[Task]:
        """Updates task status and returns updated task."""
        valid_statuses = ("backlog", "in_progress", "completed")
        if new_status not in valid_statuses:
            raise ValueError(f"Status must be one of {valid_statuses}")

        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE tasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, task_id),
        )
        self.conn.commit()
        return self.get_task(task_id)

    def summarize(self, task: Task) -> str:
        """Returns formatted string representation using formatters."""
        return format_task_summary(task.to_dict())

