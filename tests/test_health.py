"""
StreetSense — Health Endpoint Tests
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_root(client):
    """Root endpoint returns app info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "StreetSense"
    assert "version" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_health(client):
    """Health check returns healthy status."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "development"


@pytest.mark.asyncio
async def test_complaints_stub(client):
    """Complaints stub endpoint responds."""
    response = await client.get("/api/v1/complaints/")
    assert response.status_code == 200
    data = response.json()
    assert "complaints" in data


@pytest.mark.asyncio
async def test_docs_accessible(client):
    """Swagger docs are available."""
    response = await client.get("/docs")
    assert response.status_code == 200
