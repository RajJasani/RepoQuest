from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import RequestIDMiddleware, setup_logging
from app.routers import system


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()

    app = FastAPI(
        title="RepoQuest API",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    # Middleware order: Starlette executes middleware in reverse addition order,
    # so CORSMiddleware is added outer, RequestIDMiddleware inner.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)

    # Error handlers
    register_error_handlers(app)

    # Routers under /api/v1
    api_v1_router = APIRouter(prefix="/api/v1")
    api_v1_router.include_router(system.router)
    app.include_router(api_v1_router)

    return app


app = create_app()
