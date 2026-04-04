"""
Intelliwrite API — FastAPI entry point.

Start with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional

# ── Validate env vars BEFORE any heavy imports ────────────────────────────────
# This gives a clear error message if required vars are missing, before
# the pipeline tries to connect to Qdrant / Gemini.
from aeo_blog_engine.config.settings import validate_config
validate_config()

# ── Now safe to import the rest ───────────────────────────────────────────────
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from aeo_blog_engine.config.settings import Config
from aeo_blog_engine.knowledge.ingest import ingest_docs
from aeo_blog_engine.pipeline.blog_workflow import AEOBlogPipeline, langfuse


# ── App lifecycle ─────────────────────────────────────────────────────────────

_executor = ThreadPoolExecutor()
_pipeline: Optional[AEOBlogPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    _pipeline = AEOBlogPipeline()
    yield
    _executor.shutdown(wait=False)
    if langfuse:
        try:
            langfuse.flush()
        except Exception:
            pass


app = FastAPI(
    title="Intelliwrite API",
    version="1.0.0",
    description="AI-powered AEO/GEO blog generation engine",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Raw user prompt — a topic will be generated from it")
    brand_name: str = Field(..., description="Brand name for context")
    company_url: str = Field(..., description="Company URL for context")
    platforms: List[str] = Field(
        default=["linkedin", "twitter"],
        description="Social platforms to generate posts for (linkedin, twitter, reddit)",
    )


class GenerateResponse(BaseModel):
    blog_markdown: str
    social_posts: Dict[str, str]


class IngestRequest(BaseModel):
    file_path: str = Field(
        ...,
        description="Absolute path to a file (.md/.txt/.pdf) or directory to ingest into the knowledge base",
    )


class IngestResponse(BaseModel):
    status: str
    message: str


class HealthResponse(BaseModel):
    status: str
    qdrant: str


# ── Constants ─────────────────────────────────────────────────────────────────

VALID_PLATFORMS = {"linkedin", "twitter", "reddit"}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["meta"])
async def root():
    return {"service": "Intelliwrite API", "version": "1.0.0", "status": "running"}


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health():
    """Health check — also verifies live Qdrant connectivity."""
    try:
        client = QdrantClient(
            url=Config.QDRANT_URL,
            api_key=Config.QDRANT_API_KEY,
            timeout=5,
        )
        client.get_collections()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "qdrant": f"unreachable: {exc}"},
        )
    return HealthResponse(status="ok", qdrant="connected")


@app.post("/generate", response_model=GenerateResponse, tags=["content"])
async def generate(request: GenerateRequest):
    """
    Generate an AEO-optimized blog post and social media content from a prompt.

    The pipeline:
    1. Converts the prompt to a precise blog topic
    2. Runs the full 5-step AEO blog pipeline (research → plan → write → optimize → finalize)
    3. Generates a platform-specific social post for each requested platform
    """
    invalid = [p for p in request.platforms if p.lower() not in VALID_PLATFORMS]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid platforms: {invalid}. Valid options: {sorted(VALID_PLATFORMS)}",
        )

    loop = asyncio.get_event_loop()

    def _run() -> Dict:
        # Generate topic once — shared across blog pipeline and all social posts
        topic = _pipeline.generate_topic_only(request.prompt)

        # Full AEO blog pipeline
        blog_markdown = _pipeline.run(topic=topic)

        # Social posts for each requested platform
        social_posts: Dict[str, str] = {}
        for platform in request.platforms:
            p = platform.lower()
            if p in VALID_PLATFORMS:
                social_posts[p] = _pipeline.run_social_post(topic=topic, platform=p)

        return {"blog_markdown": blog_markdown, "social_posts": social_posts}

    try:
        result = await loop.run_in_executor(_executor, _run)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Pipeline failed",
                "details": str(exc),
                "hint": "Likely a Gemini quota or rate-limit issue. Retry after a short wait.",
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Pipeline error", "details": str(exc)},
        )

    return GenerateResponse(**result)


@app.post("/ingest", response_model=IngestResponse, tags=["knowledge"])
async def ingest(request: IngestRequest):
    """
    Ingest a file or directory into the Qdrant knowledge base.

    Accepts .md, .txt, and .pdf files. Pass a single file path or a directory
    path to batch-ingest all supported files within it.
    """
    path = Path(request.file_path)
    if not path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Path not found: {request.file_path}",
        )

    # If a single file is given, ingest from its parent directory (ingest_docs scans dirs)
    upload_dir = str(path.parent) if path.is_file() else str(path)

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(_executor, lambda: ingest_docs(upload_dir=upload_dir))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Ingestion failed", "details": str(exc)},
        )

    return IngestResponse(status="ok", message=f"Ingestion complete for: {request.file_path}")
