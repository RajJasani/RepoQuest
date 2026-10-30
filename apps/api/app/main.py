from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import RequestIDMiddleware, setup_logging
from app.core.startup import run_startup
from app.routers import audit, benchmark, chat, demo, explorer, issues, prs, repos, settings, system
from app.worker import start_worker, stop_worker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Run startup initialization and checks
    await run_startup()
    await start_worker()
    try:
        yield
    finally:
        await stop_worker()


def create_app() -> FastAPI:
    app_settings = get_settings()
    setup_logging()

    app = FastAPI(
        title="RepoQuest API",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware order: Starlette executes middleware in reverse addition order,
    # so CORSMiddleware is added outer, RequestIDMiddleware inner.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins_list,
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
    api_v1_router.include_router(settings.router)
    api_v1_router.include_router(repos.router)
    api_v1_router.include_router(chat.router)
    api_v1_router.include_router(explorer.router)
    api_v1_router.include_router(issues.router)
    api_v1_router.include_router(prs.router)
    api_v1_router.include_router(demo.router)
    api_v1_router.include_router(audit.router)
    api_v1_router.include_router(benchmark.router)
    app.include_router(api_v1_router)

    return app


app = create_app()
