"""
Health and root API endpoints.

Provides lightweight operational endpoints that do not require external
service connectivity. The health check confirms the application process is
running and returns basic version metadata.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from regularag import __version__
from regularag.core.config import get_settings

router = APIRouter(tags=["health"])

# Record the process start time once at import.
_START_TIME: float = time.monotonic()


class HealthResponse(BaseModel):
    """Response schema for the health check endpoint."""

    status: str
    version: str
    environment: str
    uptime_seconds: float


class RootResponse(BaseModel):
    """Response schema for the root endpoint."""

    name: str
    version: str
    description: str
    docs_url: str
    health_url: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application health check",
    description=(
        "Returns the application status, version, current environment, and "
        "uptime in seconds. This endpoint does not require database connectivity."
    ),
)
async def health_check() -> dict[str, Any]:
    """Return application health status."""
    settings = get_settings()
    return {
        "status": "healthy",
        "version": __version__,
        "environment": settings.app_env,
        "uptime_seconds": round(time.monotonic() - _START_TIME, 3),
    }


@router.get(
    "/",
    response_model=RootResponse,
    summary="API root",
    description="Returns API metadata and links to documentation and health endpoints.",
)
async def root() -> dict[str, Any]:
    """Return API root metadata."""
    settings = get_settings()
    prefix = settings.api_prefix
    return {
        "name": settings.app_name,
        "version": __version__,
        "description": "AI-Powered Regulatory Intelligence & Compliance Analysis Platform",
        "docs_url": "/docs",
        "health_url": f"{prefix}/health",
    }
