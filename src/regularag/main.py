"""
RegulaRAG — FastAPI application factory and entry point.

Provides ``create_app`` for creating the FastAPI application instance and
``main`` as the CLI entry point for Uvicorn. The application starts without
requiring PostgreSQL, Elasticsearch, Neo4j, or an LLM API key.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from regularag import __description__, __version__
from regularag.api.health import router as health_router
from regularag.core.config import get_settings
from regularag.core.exceptions import RegulaRAGError
from regularag.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Returns:
        A fully configured :class:`fastapi.FastAPI` instance ready to be
        served by Uvicorn.
    """
    settings = get_settings()

    configure_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None, None]:  # noqa: ARG001
        logger.info(
            "RegulaRAG starting",
            version=__version__,
            environment=settings.app_env,
            debug=settings.app_debug,
        )
        yield
        logger.info("RegulaRAG shutting down")

    app = FastAPI(
        title=settings.app_name,
        description=__description__,
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # CORS middleware
    # -------------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------------------
    # Exception handlers
    # -------------------------------------------------------------------------
    @app.exception_handler(RegulaRAGError)
    async def regularag_exception_handler(
        request: Request,  # noqa: ARG001
        exc: RegulaRAGError,
    ) -> JSONResponse:
        logger.warning(
            "Application error",
            error_type=type(exc).__name__,
            message=exc.message,
            **exc.context,
        )
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": type(exc).__name__, "message": exc.message},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,  # noqa: ARG001
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"error": "InternalServerError", "message": "An unexpected error occurred."},
        )

    # -------------------------------------------------------------------------
    # Routers
    # -------------------------------------------------------------------------
    app.include_router(health_router, prefix=settings.api_prefix)

    return app


# Module-level application instance used by Uvicorn when invoked as a module.
app = create_app()


def main() -> None:
    """CLI entry point — start Uvicorn programmatically.

    This is registered as the ``regularag`` console script in pyproject.toml.
    """
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "regularag.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
