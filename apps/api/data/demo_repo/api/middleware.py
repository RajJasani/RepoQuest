"""Request middleware and logging handler."""

from http.server import SimpleHTTPRequestHandler
import json
import logging

logger = logging.getLogger("taskboard.api")


class LoggingMiddleware(SimpleHTTPRequestHandler):
    """Custom request handler that logs requests and routes API calls."""

    def _send_json(self, status_code: int, data: dict):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_GET(self):
        logger.info("GET request received: %s", self.path)
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok", "app": "TaskBoard"})
        else:
            super().do_GET()

