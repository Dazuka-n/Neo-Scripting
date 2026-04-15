"""
Tests for MCP server changes:
- Issue 1.2: Authentication (X-MCP-Secret) — unit test the verify function
- Issue 1.3: ingest_document schema change (file_url instead of file_path)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "neo-scripting-mcp"))

# Set required env vars
os.environ.setdefault("API_BASE_URL", "http://localhost:8000")

import pytest
from httpx import AsyncClient, ASGITransport


# ── Issue 1.2: MCP Authentication (unit tests on _verify_secret) ────────────


def test_verify_secret_passes_when_no_secret_configured():
    """When MCP_SECRET is empty, all requests should pass."""
    import server as srv
    srv.MCP_SECRET = ""

    class FakeRequest:
        headers = {}

    result = srv._verify_secret(FakeRequest())
    assert result is None  # None means "pass"


def test_verify_secret_rejects_missing_header():
    """When MCP_SECRET is set and header is missing, should return 401."""
    import server as srv
    srv.MCP_SECRET = "test-secret-123"

    class FakeRequest:
        headers = {}

    result = srv._verify_secret(FakeRequest())
    assert result is not None
    assert result.status_code == 401

    # Reset
    srv.MCP_SECRET = ""


def test_verify_secret_rejects_wrong_header():
    """When MCP_SECRET is set and header has wrong value, should return 401."""
    import server as srv
    srv.MCP_SECRET = "test-secret-123"

    class FakeRequest:
        headers = {"X-MCP-Secret": "wrong-value"}

    result = srv._verify_secret(FakeRequest())
    assert result is not None
    assert result.status_code == 401

    srv.MCP_SECRET = ""


def test_verify_secret_passes_correct_header():
    """When MCP_SECRET is set and header matches, should return None (pass)."""
    import server as srv
    srv.MCP_SECRET = "test-secret-123"

    class FakeRequest:
        headers = {"X-MCP-Secret": "test-secret-123"}

    result = srv._verify_secret(FakeRequest())
    assert result is None

    srv.MCP_SECRET = ""


# ── MCP /health (no auth required) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_mcp_health_endpoint():
    """GET /health on MCP server should return 200."""
    from server import starlette_app
    transport = ASGITransport(app=starlette_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["server"] == "neo-scripting-mcp"


# ── Issue 1.3: ingest_document schema ────────────────────────────────────────


def test_ingest_tool_schema_uses_file_url():
    """The ingest_document tool schema should use file_url, not file_path."""
    from tools import TOOL_DEFINITIONS

    ingest_tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "ingest_document")
    props = ingest_tool["inputSchema"]["properties"]
    required = ingest_tool["inputSchema"]["required"]

    assert "file_url" in props, "ingest_document should have file_url parameter"
    assert "file_path" not in props, "ingest_document should NOT have file_path parameter"
    assert "file_url" in required


def test_ingest_tool_description_mentions_url():
    """The ingest_document tool description should mention URLs."""
    from tools import TOOL_DEFINITIONS

    ingest_tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "ingest_document")
    desc = ingest_tool["description"].lower()
    assert "url" in desc


def test_all_three_tools_present():
    """All three MCP tools should be defined."""
    from tools import TOOL_DEFINITIONS

    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert names == {"generate_blog", "ingest_document", "check_backend_health"}


def test_generate_blog_schema_has_enum_platforms():
    """The generate_blog tool schema should enforce enum on platforms."""
    from tools import TOOL_DEFINITIONS

    gen_tool = next(t for t in TOOL_DEFINITIONS if t["name"] == "generate_blog")
    platforms_schema = gen_tool["inputSchema"]["properties"]["platforms"]
    assert "items" in platforms_schema
    assert "enum" in platforms_schema["items"]
    assert set(platforms_schema["items"]["enum"]) == {"linkedin", "twitter", "reddit"}
