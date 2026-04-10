"""
Intelliwrite API — FastAPI entry point.

Start with:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Literal, Optional

# ── Validate env vars BEFORE any heavy imports ────────────────────────────────
# This gives a clear error message if required vars are missing, before
# the pipeline tries to connect to Qdrant / Gemini.
from aeo_blog_engine.config.settings import validate_config
validate_config()

# ── Now safe to import the rest ───────────────────────────────────────────────
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from qdrant_client import QdrantClient

from aeo_blog_engine.config.settings import Config
from aeo_blog_engine.knowledge.ingest import ingest_docs
from aeo_blog_engine.pipeline.blog_workflow import AEOBlogPipeline, langfuse

logger = logging.getLogger("intelliwrite-api")


# ── App lifecycle ─────────────────────────────────────────────────────────────

_executor = ThreadPoolExecutor(max_workers=4)
_pipeline: Optional[AEOBlogPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pipeline
    logger.info("ThreadPoolExecutor initialized with %d workers", _executor._max_workers)
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

# CORS: explicit production + local dev origins.
# allow_origins=["*"] with allow_credentials=True is invalid per the spec and
# can cause silent browser-side failures — use an explicit list instead.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://intelliwrite-neon.vercel.app",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

Platform = Literal["linkedin", "twitter", "reddit"]


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="Raw user prompt — a topic will be generated from it")
    brand_name: str = Field(..., description="Brand name for context")
    company_url: str = Field(..., description="Company URL for context")
    platforms: List[Platform] = Field(
        default=["linkedin", "twitter"],
        description="Social platforms to generate posts for (linkedin, twitter, reddit)",
    )

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v):
        if not v.strip():
            raise ValueError("prompt must not be empty")
        return v.strip()


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


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["meta"])
async def root():
    return {"service": "Intelliwrite API", "version": "1.0.0", "status": "running"}


@app.get("/health", tags=["meta"])
async def health():
    """Health check — always returns 200. Reports Qdrant status in the body."""
    qdrant_status = "connected"
    qdrant_error = None
    try:
        client = QdrantClient(
            url=Config.QDRANT_URL,
            api_key=Config.QDRANT_API_KEY,
            timeout=5,
        )
        client.get_collections()
    except Exception as exc:
        qdrant_status = "unreachable"
        qdrant_error = str(exc)
        logger.warning("Health check: Qdrant unreachable — %s", qdrant_error)
    return {
        "status": "ok" if qdrant_status == "connected" else "degraded",
        "api": "healthy",
        "qdrant": qdrant_status,
        "qdrant_error": qdrant_error,
    }


@app.post("/generate", response_model=GenerateResponse, tags=["content"])
async def generate(request: GenerateRequest):
    """
    Generate an AEO-optimized blog post and social media content from a prompt.

    The pipeline:
    1. Converts the prompt to a precise blog topic
    2. Runs the full 5-step AEO blog pipeline (research → plan → write → optimize → finalize)
    3. Generates a platform-specific social post for each requested platform
    """
    loop = asyncio.get_running_loop()

    def _run() -> Dict:
        # Generate topic once — shared across blog pipeline and all social posts
        topic = _pipeline.generate_topic_only(request.prompt)

        # Full AEO blog pipeline
        blog_markdown = _pipeline.run(topic=topic)

        # Social posts for each requested platform
        social_posts: Dict[str, str] = {}
        for platform in request.platforms:
            social_posts[platform] = _pipeline.run_social_post(topic=topic, platform=platform)

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


@app.post("/generate/stream", tags=["content"])
async def generate_stream(request: GenerateRequest):
    """
    Streaming variant of POST /generate.
    Emits SSE events as each agent completes, keeping the connection alive
    past Vercel's timeout window.
    """
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def _progress(agent_name: str):
        loop.call_soon_threadsafe(queue.put_nowait, {"event": "agent_done", "agent": agent_name})

    def _run() -> Dict:
        topic = _pipeline.generate_topic_only(request.prompt)
        _progress("topic_generator")

        blog_markdown = _pipeline.run(topic=topic, progress_callback=_progress)

        social_posts: Dict[str, str] = {}
        for platform in request.platforms:
            social_posts[platform] = _pipeline.run_social_post(
                topic=topic, platform=platform, progress_callback=_progress,
            )
        return {"blog_markdown": blog_markdown, "social_posts": social_posts}

    async def event_stream():
        task = loop.run_in_executor(_executor, _run)
        try:
            while True:
                # Wait for either a progress event or the pipeline to finish
                done_futures = {task}
                get_task = asyncio.ensure_future(queue.get())
                finished, _ = await asyncio.wait(
                    {task, get_task}, return_when=asyncio.FIRST_COMPLETED,
                )
                if get_task in finished:
                    event = get_task.result()
                    yield f"data: {json.dumps(event)}\n\n"
                else:
                    get_task.cancel()

                if task in finished:
                    # Drain any remaining events in the queue
                    while not queue.empty():
                        event = queue.get_nowait()
                        yield f"data: {json.dumps(event)}\n\n"
                    result = task.result()
                    yield f"data: {json.dumps({'event': 'complete', 'result': result})}\n\n"
                    return
        except Exception as exc:
            yield f"data: {json.dumps({'event': 'error', 'detail': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(_executor, lambda: ingest_docs(upload_dir=upload_dir))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={"error": "Ingestion failed", "details": str(exc)},
        )

    return IngestResponse(status="ok", message=f"Ingestion complete for: {request.file_path}")
