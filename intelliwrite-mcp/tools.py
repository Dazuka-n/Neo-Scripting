"""
tools.py — MCP tool definitions and handlers for Intelliwrite.

Three tools are exposed:
  1. generate_blog        — Run the full AEO blog + social pipeline
  2. ingest_document      — Add a document to the Qdrant knowledge base
  3. check_backend_health — Verify the FastAPI backend and Qdrant are online
"""

import logging
from typing import Any

import httpx

from config import Config

logger = logging.getLogger(__name__)


# ── Tool schemas ──────────────────────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "generate_blog",
        "description": (
            "Generate a fully AEO/GEO-optimized blog article and social media posts "
            "using the Intelliwrite multi-agent pipeline. The pipeline runs 6 agents: "
            "topic structuring, research (Qdrant KB + DuckDuckGo), outline planning, "
            "writing, AEO optimization, and QA. Returns the full blog in markdown and "
            "social posts for selected platforms."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": (
                        "The topic or content brief for the blog article. Be specific — "
                        "include industry, audience, angle, and any keywords to target."
                    ),
                },
                "brand_name": {
                    "type": "string",
                    "description": "The brand or company name this article is being written for.",
                },
                "company_url": {
                    "type": "string",
                    "description": "The company website URL. Used for brand context in the pipeline.",
                },
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["linkedin", "twitter", "reddit"],
                    },
                    "description": (
                        "Social platforms to generate posts for. "
                        "Defaults to linkedin and twitter if not specified."
                    ),
                    "default": ["linkedin", "twitter"],
                },
            },
            "required": ["prompt", "brand_name", "company_url"],
        },
    },
    {
        "name": "ingest_document",
        "description": (
            "Ingest a document into the Intelliwrite Qdrant knowledge base. "
            "Once ingested, the document becomes part of the RAG context used "
            "by the researcher agent when generating future articles. "
            "Supports .md, .txt, and .pdf files."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": (
                        "Absolute path to the file to ingest (.md, .txt, or .pdf). "
                        "The file must be accessible on the server where the FastAPI "
                        "backend is running."
                    ),
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "check_backend_health",
        "description": (
            "Check the health status of the Intelliwrite backend API and its "
            "connected services (Qdrant vector database). Use this to verify "
            "the service is online before running a generation job."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ── Handlers ──────────────────────────────────────────────────────────────────

async def handle_generate_blog(arguments: dict[str, Any]) -> str:
    """POST /generate and format the blog + social posts response."""
    prompt = arguments.get("prompt", "")
    brand_name = arguments.get("brand_name", "")
    company_url = arguments.get("company_url", "")
    platforms = arguments.get("platforms", ["linkedin", "twitter"])

    payload = {
        "prompt": prompt,
        "brand_name": brand_name,
        "company_url": company_url,
        "platforms": platforms,
    }

    url = f"{Config.API_BASE_URL}/generate"
    logger.info("Calling POST %s (prompt=%r, platforms=%s)", url, prompt[:60], platforms)

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, json=payload)
    except httpx.TimeoutException:
        return (
            "✗ Request timed out after 180 seconds.\n"
            "The blog pipeline is multi-agent and can take 1–3 minutes. "
            "Please try again — if this persists, check backend logs."
        )
    except httpx.ConnectError:
        return (
            f"✗ Cannot connect to backend at {Config.API_BASE_URL}.\n"
            "Ensure the FastAPI server is running and API_BASE_URL is correct."
        )

    if resp.status_code != 200:
        _try_detail(resp)
        return _error_response("generate_blog", resp)

    data = resp.json()
    blog_markdown = data.get("blog_markdown", "")
    social_posts: dict = data.get("social_posts", {})

    lines = [
        "═══════════════════════════════════",
        "INTELLIWRITE — GENERATED ARTICLE",
        "═══════════════════════════════════",
        "",
        blog_markdown,
        "",
        "───────────────────────────────────",
        "SOCIAL POSTS",
        "───────────────────────────────────",
        "",
    ]

    platform_icons = {"linkedin": "📌 LINKEDIN", "twitter": "🐦 TWITTER", "reddit": "👽 REDDIT"}
    for platform, icon_label in platform_icons.items():
        if platform in social_posts:
            lines += [icon_label, social_posts[platform], ""]

    lines.append("═══════════════════════════════════")
    return "\n".join(lines)


async def handle_ingest_document(arguments: dict[str, Any]) -> str:
    """POST /ingest and return a confirmation message."""
    file_path = arguments.get("file_path", "")
    payload = {"file_path": file_path}

    url = f"{Config.API_BASE_URL}/ingest"
    logger.info("Calling POST %s (file_path=%r)", url, file_path)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
    except httpx.TimeoutException:
        return f"✗ Request timed out after 60 seconds while ingesting: {file_path}"
    except httpx.ConnectError:
        return (
            f"✗ Cannot connect to backend at {Config.API_BASE_URL}.\n"
            "Ensure the FastAPI server is running and API_BASE_URL is correct."
        )

    if resp.status_code != 200:
        return _error_response("ingest_document", resp)

    data = resp.json()
    message = data.get("message", "Ingestion complete.")
    return f"✓ Document ingested successfully: {file_path}\n{message}"


async def handle_check_backend_health(_arguments: dict[str, Any]) -> str:
    """GET /health and format a readable status report."""
    url = f"{Config.API_BASE_URL}/health"
    logger.info("Calling GET %s", url)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        return (
            f"✗ Backend unreachable at {Config.API_BASE_URL}\n"
            f"Error: {exc}"
        )

    if resp.status_code != 200:
        return (
            f"✗ Backend returned HTTP {resp.status_code}\n"
            f"URL: {Config.API_BASE_URL}\n"
            f"Response: {resp.text[:300]}"
        )

    data = resp.json()
    api_status = "✓ Online" if data.get("status") == "ok" else f"⚠ {data.get('status')}"
    qdrant_raw = data.get("qdrant", "unknown")
    qdrant_status = "✓ Connected" if qdrant_raw == "connected" else f"✗ {qdrant_raw}"

    return "\n".join([
        "Intelliwrite Backend Health",
        "──────────────────────────",
        f"API Status:    {api_status}",
        f"Qdrant Status: {qdrant_status}",
        f"Backend URL:   {Config.API_BASE_URL}",
    ])


# ── Dispatch ──────────────────────────────────────────────────────────────────

_HANDLERS = {
    "generate_blog": handle_generate_blog,
    "ingest_document": handle_ingest_document,
    "check_backend_health": handle_check_backend_health,
}


async def dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    """
    Route a tool call to its handler.
    All exceptions are caught here so the MCP server never crashes on a
    failed tool call — errors are returned as readable text to the agent.
    """
    handler = _HANDLERS.get(name)
    if handler is None:
        return f"✗ Unknown tool: '{name}'. Available tools: {', '.join(_HANDLERS)}"
    try:
        return await handler(arguments)
    except Exception as exc:
        logger.exception("Unhandled exception in tool '%s'", name)
        return f"✗ Tool '{name}' raised an unexpected error: {exc}"


# ── Utilities ─────────────────────────────────────────────────────────────────

def _try_detail(resp: httpx.Response) -> None:
    """Log response detail for debugging."""
    try:
        detail = resp.json()
        logger.debug("API error detail: %s", detail)
    except Exception:
        pass


def _error_response(tool: str, resp: httpx.Response) -> str:
    detail = ""
    try:
        body = resp.json()
        detail = body.get("detail") or body.get("error") or str(body)
    except Exception:
        detail = resp.text[:300]
    return (
        f"✗ Backend returned HTTP {resp.status_code} for tool '{tool}'.\n"
        f"Detail: {detail}"
    )
