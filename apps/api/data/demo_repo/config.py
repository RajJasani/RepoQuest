"""Application configuration settings."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = os.environ.get("TASKBOARD_DB_PATH", str(BASE_DIR / "taskboard.db"))
SECRET_KEY = os.environ.get("TASKBOARD_SECRET_KEY", "demo-insecure-secret-key-12345")
PORT = int(os.environ.get("TASKBOARD_PORT", "8000"))
DEBUG = os.environ.get("TASKBOARD_DEBUG", "1") == "1"

