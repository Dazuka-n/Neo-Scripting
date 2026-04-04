"""
server.py — Intelliwrite MCP Server (SSE transport).

Exposes three MCP tools:
  • generate_blog
  • ingest_document
  • check_backend_health

Start with:
    uvicorn server:starlette_app --host 0.0.0.0 --port 8080

Or via Docker / Railway using the Dockerfile / railway.toml.
"""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from config import Config, check_backend_reachable, validate_config
from tools import TOOL_DEFINITIONS, dispatch_tool

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("intelliwrite-mcp")

# ── Config validation (fail fast before binding any port) ─────────────────────
validate_config()

# ── MCP server instance ───────────────────────────────────────────────────────
mcp_server = Server(name="intelliwrite", version="1.0.0")


# ── Tool registry ─────────────────────────────────────────────────────────────

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name=t["name"],
            description=t["description"],
            inputSchema=t["inputSchema"],
        )
        for t in TOOL_DEFINITIONS
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    timestamp = datetime.now(timezone.utc).isoformat()
    logger.info("[%s] Tool called: %s | args keys: %s", timestamp, name, list(arguments.keys()))

    result = await dispatch_tool(name, arguments)

    logger.info("[%s] Tool '%s' completed (%d chars)", timestamp, name, len(result))
    return [TextContent(type="text", text=result)]


# ── SSE transport ─────────────────────────────────────────────────────────────
sse_transport = SseServerTransport("/messages")


async def sse_endpoint(request: Request) -> None:
    """
    GET /sse — Clients connect here to open an SSE stream.
    Each connection runs a full MCP server session.
    """
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options(),
        )


async def messages_endpoint(request: Request) -> None:
    """
    POST /messages — Clients post MCP messages here, linked to their SSE session.
    """
    await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )


async def health_endpoint(_request: Request) -> JSONResponse:
    """GET /health — Liveness probe for the MCP server itself."""
    return JSONResponse(
        {"status": "ok", "server": "intelliwrite-mcp", "version": "1.0.0"}
    )


# ── Lifespan (replaces on_startup in Starlette >= 0.37) ──────────────────────

@asynccontextmanager
async def lifespan(_app: Starlette):
    logger.info("=== Intelliwrite MCP Server 1.0.0 ===")
    logger.info("Backend URL:  %s", Config.API_BASE_URL)
    logger.info("SSE endpoint: GET  /sse")
    logger.info("Messages:     POST /messages")
    logger.info("Health:       GET  /health")
    await check_backend_reachable()
    logger.info("MCP server ready -- waiting for client connections.")
    yield
    logger.info("MCP server shutting down.")


# ── Starlette app ─────────────────────────────────────────────────────────────
starlette_app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/sse", endpoint=sse_endpoint),
        Route("/messages", endpoint=messages_endpoint, methods=["POST"]),
        Route("/health", endpoint=health_endpoint),
        # Mount handles /messages/<session_id> with trailing slash variants
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
)
