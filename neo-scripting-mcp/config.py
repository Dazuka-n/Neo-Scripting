"""
config.py — Environment configuration and startup validation.
"""

import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    # ── Required ────────────────────────────────────────────────────────────
    API_BASE_URL: str = os.getenv("API_BASE_URL", "").rstrip("/")

    # ── Optional ────────────────────────────────────────────────────────────
    PORT: int = int(os.getenv("PORT", "8080"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").upper()


def validate_config() -> None:
    """
    Validate required environment variables.
    Raises EnvironmentError with a clear message if any are missing.
    """
    if not Config.API_BASE_URL:
        raise EnvironmentError(
            "\n[neo-scripting-mcp] Startup failed — missing required environment variable:\n"
            "  - API_BASE_URL  (e.g. https://api.neo-scripting.ai or http://localhost:8000)\n\n"
            "Set it in your .env file. See .env.example for reference."
        )


async def check_backend_reachable() -> bool:
    """
    Hit API_BASE_URL/health to verify the FastAPI backend is reachable.
    Logs a warning (but does NOT raise) if it is not — the MCP server
    should still start so clients can connect and get a clear error from
    the tool handler rather than a connection-refused at the MCP level.
    """
    health_url = f"{Config.API_BASE_URL}/health"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(health_url)
            if resp.status_code == 200:
                logger.info("Backend reachable at %s ✓", Config.API_BASE_URL)
                return True
            else:
                logger.warning(
                    "Backend at %s returned HTTP %s — proceeding anyway.",
                    Config.API_BASE_URL,
                    resp.status_code,
                )
                return False
    except Exception as exc:
        logger.warning(
            "Backend unreachable at %s (%s) — MCP server will still start. "
            "Tool calls will fail until the backend is available.",
            Config.API_BASE_URL,
            exc,
        )
        return False
