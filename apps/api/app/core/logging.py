import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.errors import AppError, format_error_response

request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        req_id = request_id_ctx_var.get()
        if req_id:
            log_obj["request_id"] = req_id

        if record.exc_info:
            log_obj["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers
    if not any(isinstance(h.formatter, JSONFormatter) for h in root_logger.handlers):
        root_logger.handlers = [handler]

    # Suppress verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = str(uuid.uuid4())

        token = request_id_ctx_var.set(req_id)
        request.state.request_id = req_id

        start_time = time.perf_counter()
        logger = logging.getLogger("app.access")

        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.info(
                "%s %s -> %s in %sms",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
        except AppError as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                "%s %s -> AppError(%s) in %sms",
                request.method,
                request.url.path,
                exc.code,
                duration_ms,
            )
            response = JSONResponse(
                status_code=exc.status_code,
                content=format_error_response(exc.code, exc.message, exc.details),
            )
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception(
                "%s %s failed with unhandled exception in %sms",
                request.method,
                request.url.path,
                duration_ms,
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=format_error_response("internal_error", "Internal server error", {}),
            )
        finally:
            request_id_ctx_var.reset(token)

        response.headers["X-Request-ID"] = req_id
        return response
