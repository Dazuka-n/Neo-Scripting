"""
Tests for Pydantic input validation on POST /generate.
Covers Issue 4.3: platforms Literal validation and prompt validation.
Also covers Issue 2.3: CORS, Issue 2.4: /health graceful degradation.

These tests mock the Qdrant knowledge base to avoid requiring a running
Qdrant instance.
"""
import os
import sys
from unittest.mock import MagicMock, patch

# Ensure the project root is on the path so `main` can be imported.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set required env vars before importing main (which calls validate_config on import)
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("QDRANT_API_KEY", "local")

# Mock the knowledge base before any agent imports try to connect to Qdrant
mock_kb = MagicMock()
mock_kb.search.return_value = []
with patch("aeo_blog_engine.knowledge.knowledge_base.get_knowledge_base", return_value=mock_kb):
    from main import app

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ── Issue 4.3: Platform validation ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_platform_returns_422(client):
    """POST /generate with platforms: ["instagram"] should return 422."""
    resp = await client.post("/generate", json={
        "prompt": "Test topic",
        "brand_name": "TestBrand",
        "company_url": "https://example.com",
        "platforms": ["instagram"],
    })
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body


@pytest.mark.asyncio
async def test_typo_platform_returns_422(client):
    """POST /generate with platforms: ["tweeter"] should return 422."""
    resp = await client.post("/generate", json={
        "prompt": "Test topic",
        "brand_name": "TestBrand",
        "company_url": "https://example.com",
        "platforms": ["tweeter"],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_empty_prompt_returns_422(client):
    """POST /generate with prompt: "" should return 422."""
    resp = await client.post("/generate", json={
        "prompt": "   ",
        "brand_name": "TestBrand",
        "company_url": "https://example.com",
        "platforms": ["linkedin"],
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_valid_platforms_pass_validation(client):
    """POST /generate with platforms: ["linkedin"] should pass validation (not 422).
    It may fail with a 5xx if the pipeline isn't configured, but it should NOT be 422."""
    resp = await client.post("/generate", json={
        "prompt": "Test topic for validation",
        "brand_name": "TestBrand",
        "company_url": "https://example.com",
        "platforms": ["linkedin"],
    })
    assert resp.status_code != 422


@pytest.mark.asyncio
async def test_multiple_valid_platforms_pass(client):
    """All three valid platforms should pass validation."""
    resp = await client.post("/generate", json={
        "prompt": "Test all platforms",
        "brand_name": "TestBrand",
        "company_url": "https://example.com",
        "platforms": ["linkedin", "twitter", "reddit"],
    })
    assert resp.status_code != 422


@pytest.mark.asyncio
async def test_streaming_endpoint_rejects_invalid_platform(client):
    """POST /generate/stream with invalid platform should return 422."""
    resp = await client.post("/generate/stream", json={
        "prompt": "Test topic",
        "brand_name": "TestBrand",
        "company_url": "https://example.com",
        "platforms": ["tiktok"],
    })
    assert resp.status_code == 422


# ── Issue 2.4: Health endpoint graceful degradation ─────────────────────────


@pytest.mark.asyncio
async def test_health_always_returns_200(client):
    """GET /health should always return 200, even if Qdrant is unreachable."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert "api" in body
    assert body["api"] == "healthy"
    assert body["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_health_returns_qdrant_field(client):
    """GET /health response includes qdrant status field."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "qdrant" in body
    assert body["qdrant"] in ("connected", "unreachable")


@pytest.mark.asyncio
async def test_health_has_qdrant_error_field(client):
    """GET /health includes qdrant_error field (null when ok, string when unreachable)."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert "qdrant_error" in body
    if body["qdrant"] == "connected":
        assert body["qdrant_error"] is None
    else:
        assert isinstance(body["qdrant_error"], str)


# ── Issue 2.3: CORS configuration ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_cors_headers_for_production_origin(client):
    """OPTIONS preflight from production frontend origin should get CORS headers."""
    resp = await client.options("/generate", headers={
        "Origin": "https://intelliwrite-neon.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    })
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
    assert resp.headers["access-control-allow-origin"] == "https://intelliwrite-neon.vercel.app"


@pytest.mark.asyncio
async def test_cors_headers_for_localhost(client):
    """OPTIONS preflight from localhost dev origin should get CORS headers."""
    resp = await client.options("/generate", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    })
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.asyncio
async def test_cors_rejects_unknown_origin(client):
    """OPTIONS preflight from an unknown origin should NOT get CORS headers."""
    resp = await client.options("/generate", headers={
        "Origin": "https://evil.example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    })
    # FastAPI CORS middleware returns 400 for disallowed origins
    assert "access-control-allow-origin" not in resp.headers or \
           resp.headers.get("access-control-allow-origin") != "https://evil.example.com"


# ── Root endpoint ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """GET / should return service info."""
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "Intelliwrite API"
    assert body["version"] == "1.0.0"
