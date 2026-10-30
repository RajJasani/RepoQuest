"""Shared test fixtures and database helpers."""

import sqlite3
import unittest
from db.base import SCHEMA_TASKS_SQL, SCHEMA_USERS_SQL


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        """Create an in-memory SQLite database for testing."""
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        with self.conn:
            self.conn.execute(SCHEMA_USERS_SQL)
            self.conn.execute(SCHEMA_TASKS_SQL)

    def tearDown(self):
        self.conn.close()

