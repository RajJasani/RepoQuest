"""Main entry point for TaskBoard server."""

from http.server import HTTPServer
import logging

from api.middleware import LoggingMiddleware
from api.routes_auth import AuthHandler
from api.routes_tasks import TaskHandler
from auth.service import AuthService
from config import DEBUG, PORT
from db.session import get_db_connection
from tasks.service import TaskService

logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger("taskboard.main")


def create_app():
    """Initializes and wires application components."""
    conn = get_db_connection()
    auth_service = AuthService(conn)
    task_service = TaskService(conn)
    return {
        "auth_service": auth_service,
        "task_service": task_service,
    }


def run_server():
    """Starts the HTTP server."""
    logger.info("Starting TaskBoard on port %d...", PORT)
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, LoggingMiddleware)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping server...")
        httpd.server_close()


if __name__ == "__main__":
    create_app()
    run_server()
