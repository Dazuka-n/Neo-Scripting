import os
from typing import Optional
import requests

from agno.vectordb.qdrant import Qdrant
from agno.knowledge.embedder.openai import OpenAIEmbedder
from aeo_blog_engine.config.settings import Config

EMBEDDER_PROVIDER = os.getenv("EMBEDDER_PROVIDER", "auto").lower()

_cached_vector_db: Optional[object] = None


class OpenAICompatEmbedder:
    """Generic HTTP embedder for providers with an OpenAI-compatible /embeddings endpoint."""

    def __init__(
        self,
        *,
        model_id: str,
        api_key: str,
        base_url: str,
        dimensions: int | None = None,
        extra_headers: Optional[dict] = None,
    ):
        self.model_id = model_id
        self.api_key = api_key
        self.dimensions = dimensions
        self.base_url = base_url.rstrip("/") + "/embeddings"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if extra_headers:
            self.headers.update(extra_headers)

    def get_embedding(self, text: str):
        response = requests.post(
            self.base_url,
            json={"model": self.model_id, "input": text},
            headers=self.headers,
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("data"):
            raise ValueError(f"No embedding returned for {self.model_id}: {data}")
        return data["data"][0]["embedding"]


def get_knowledge_base():
    """
    Return the Qdrant vector DB instance.

    Raises RuntimeError with a descriptive message if Qdrant is unreachable.
    Qdrant is REQUIRED — there is no in-memory fallback.
    """
    global _cached_vector_db
    if _cached_vector_db:
        return _cached_vector_db

    embedder = _select_embedder()

    try:
        db = Qdrant(
            collection=Config.COLLECTION_NAME,
            url=Config.QDRANT_URL,
            api_key=Config.QDRANT_API_KEY,
            embedder=embedder,
        )
        # Verify the connection is live
        if hasattr(db, "client"):
            db.client.get_collections()
        _cached_vector_db = db
        return _cached_vector_db
    except Exception as exc:
        raise RuntimeError(
            f"[Intelliwrite] Cannot connect to Qdrant at '{Config.QDRANT_URL}'.\n"
            "Please ensure:\n"
            "  1. Qdrant is running (docker run -p 6333:6333 qdrant/qdrant)\n"
            "  2. QDRANT_URL and QDRANT_API_KEY are set correctly in your .env\n"
            f"Original error: {exc}"
        ) from exc


def _select_embedder():
    """Select the best available embedder based on EMBEDDER_PROVIDER and available keys."""
    preference = EMBEDDER_PROVIDER
    if preference == "openrouter":
        provider_order = ["openrouter", "openai", "gemini"]
    elif preference == "gemini":
        provider_order = ["gemini", "openrouter", "openai"]
    elif preference == "openai":
        provider_order = ["openai", "openrouter", "gemini"]
    else:
        provider_order = ["openai", "openrouter", "gemini"]

    for provider in provider_order:
        if provider == "openai" and Config.OPENAI_API_KEY:
            return OpenAIEmbedder(
                id="text-embedding-3-small",
                api_key=Config.OPENAI_API_KEY,
                dimensions=1536,
            )
        if provider == "openrouter" and Config.OPENROUTER_API_KEY:
            return OpenAICompatEmbedder(
                model_id="text-embedding-3-large",
                api_key=Config.OPENROUTER_API_KEY,
                base_url=Config.OPENROUTER_BASE_URL,
                dimensions=3072,
                extra_headers={
                    "HTTP-Referer": os.getenv("OPENROUTER_APP_URL", "https://localhost"),
                    "X-Title": os.getenv("OPENROUTER_APP_NAME", "Intelliwrite"),
                },
            )
        if provider == "gemini" and Config.GEMINI_API_KEY:
            return OpenAICompatEmbedder(
                model_id="models/text-embedding-004",
                api_key=Config.GEMINI_API_KEY,
                base_url=Config.GEMINI_BASE_URL,
                dimensions=3072,
            )

    raise ValueError(
        "[Intelliwrite] No embedder could be initialized.\n"
        "Set at least one of: OPENAI_API_KEY, OPENROUTER_API_KEY, or GEMINI_API_KEY."
    )
