"""
Integration tests for the FastAPI application endpoints.

Tests are executed against the real application instance using the
HTTPX async test client. No external services (database, Elasticsearch,
Neo4j, LLM) are required.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from regularag.main import create_app


@pytest.fixture
def app():
    """Return a fresh application instance for each test."""
    return create_app()


@pytest.fixture
async def client(app):
    """Return an HTTPX async test client connected to the application."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac


@pytest.mark.integration
class TestHealthEndpoint:
    """Tests for GET /api/v1/health."""

    async def test_health_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200

    async def test_health_response_structure(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "uptime_seconds" in data

    async def test_health_status_is_healthy(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.json()["status"] == "healthy"

    async def test_health_version_matches_package(self, client: AsyncClient) -> None:
        from regularag import __version__

        response = await client.get("/api/v1/health")
        assert response.json()["version"] == __version__

    async def test_health_uptime_is_positive(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.json()["uptime_seconds"] >= 0


@pytest.mark.integration
class TestRootEndpoint:
    """Tests for GET /api/v1/."""

    async def test_root_returns_200(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/")
        assert response.status_code == 200

    async def test_root_response_structure(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/")
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "docs_url" in data
        assert "health_url" in data

    async def test_root_name_is_regularag(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/")
        assert response.json()["name"] == "RegulaRAG"

    async def test_root_health_url_is_correct(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/")
        assert response.json()["health_url"] == "/api/v1/health"


@pytest.mark.integration
class TestApplicationStartup:
    """Verify the application starts cleanly."""

    def test_create_app_returns_fastapi_instance(self) -> None:
        from fastapi import FastAPI

        app = create_app()
        assert isinstance(app, FastAPI)

    def test_app_has_routes(self) -> None:
        app = create_app()
        paths = list(app.openapi()["paths"].keys())
        assert any("/health" in p for p in paths)

    async def test_unknown_route_returns_404(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404
