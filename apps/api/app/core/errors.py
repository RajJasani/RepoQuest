import logging
import re
from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.core.errors")

TOKEN_PATTERN = re.compile(r"(ghp_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|Bearer\s+[A-Za-z0-9\-._~+/]+=*)")


def sanitize_value(val: Any) -> Any:
    if isinstance(val, str):
        return TOKEN_PATTERN.sub("[REDACTED]", val)
    if isinstance(val, dict):
        sanitized = {}
        for k, v in val.items():
            if any(secret_term in str(k).lower() for secret_term in ("token", "secret", "password", "key")):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_value(v)
        return sanitized
    if isinstance(val, list):
        return [sanitize_value(item) for item in val]
    return val


class AppError(Exception):
    code: str = "internal_error"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        details: Optional[Any] = None,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = sanitize_value(message)
        self.details = sanitize_value(details if details is not None else {})
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code


class ValidationError(AppError):
    code = "validation_error"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, message: str = "Validation failed", details: Optional[Any] = None):
        super().__init__(message=message, details=details)


class NotFoundError(AppError):
    code = "not_found"
    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, message: str = "Resource not found", details: Optional[Any] = None):
        super().__init__(message=message, details=details)


class GitHubError(AppError):
    code = "github_error"
    status_code = status.HTTP_502_BAD_GATEWAY

    def __init__(self, message: str = "GitHub API error", details: Optional[Any] = None):
        super().__init__(message=message, details=details)


class RateLimitedError(AppError):
    code = "rate_limited"
    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Any] = None):
        super().__init__(message=message, details=details)


class LLMUnavailableError(AppError):
    code = "llm_unavailable"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    def __init__(self, message: str = "LLM service is unavailable", details: Optional[Any] = None):
        super().__init__(message=message, details=details)


class InvalidLLMOutputError(AppError):
    code = "invalid_llm_output"
    status_code = status.HTTP_502_BAD_GATEWAY

    def __init__(self, message: str = "Invalid response received from LLM", details: Optional[Any] = None):
        super().__init__(message=message, details=details)


class ConflictError(AppError):
    code = "conflict"
    status_code = status.HTTP_409_CONFLICT

    def __init__(self, message: str = "Resource conflict", details: Optional[Any] = None):
        super().__init__(message=message, details=details)


class InternalError(AppError):
    code = "internal_error"
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str = "Internal server error", details: Optional[Any] = None):
        super().__init__(message=message, details=details)


def format_error_response(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": sanitize_value(message),
            "details": sanitize_value(details if details is not None else {}),
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=format_error_response(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        clean_errors = []
        for err in exc.errors():
            clean_err = {
                "type": err.get("type"),
                "loc": err.get("loc"),
                "msg": err.get("msg"),
            }
            clean_errors.append(clean_err)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=format_error_response(
                code="validation_error",
                message="Request validation failed",
                details=clean_errors,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        status_code = exc.status_code
        detail_msg = str(exc.detail) if exc.detail else "HTTP error"

        if status_code == status.HTTP_404_NOT_FOUND:
            code = "not_found"
            if detail_msg == "Not Found" or not detail_msg:
                detail_msg = f"Path '{request.url.path}' not found"
        elif status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            code = "not_found"
            detail_msg = f"Method '{request.method}' not allowed on '{request.url.path}'"
        elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            code = "rate_limited"
        elif status_code == status.HTTP_409_CONFLICT:
            code = "conflict"
        elif status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
            code = "validation_error"
        elif status_code == status.HTTP_502_BAD_GATEWAY:
            code = "github_error"
        elif status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            code = "llm_unavailable"
        else:
            code = "internal_error"

        return JSONResponse(
            status_code=status_code,
            content=format_error_response(
                code=code,
                message=detail_msg,
                details={},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception while processing request: %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=format_error_response(
                code="internal_error",
                message="Internal server error",
                details={},
            ),
        )
