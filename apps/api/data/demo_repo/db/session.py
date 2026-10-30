"""SQLite database connection and initialization."""

import sqlite3
from config import DATABASE_PATH
from db.base import SCHEMA_TASKS_SQL, SCHEMA_USERS_SQL


def get_db_connection() -> sqlite3.Connection:
    """Creates a new database connection with dictionary row access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes tables in the SQLite database."""
    conn = get_db_connection()
    with conn:
        conn.execute(SCHEMA_USERS_SQL)
        conn.execute(SCHEMA_TASKS_SQL)
    conn.close()
