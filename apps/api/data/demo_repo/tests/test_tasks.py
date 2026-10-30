"""Tests for task service operations."""

import unittest
from tasks.service import TaskService
from tests.conftest import BaseTestCase


class TestTasks(BaseTestCase):
    def test_create_and_list_tasks(self):
        service = TaskService(self.conn)
        task = service.create_task("Write documentation", "Detail run commands")
        self.assertEqual(task.title, "Write documentation")
        self.assertEqual(task.status, "backlog")

        tasks = service.list_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, task.id)

    def test_update_status(self):
        service = TaskService(self.conn)
        task = service.create_task("Fix bug")
        updated = service.update_task_status(task.id, "in_progress")
        self.assertEqual(updated.status, "in_progress")


if __name__ == "__main__":
    unittest.main()
