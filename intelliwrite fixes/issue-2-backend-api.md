# [BUG] Backend API — 4 Issues Affecting Production Reliability

**Labels:** `bug` `backend` `critical` `help-wanted`  
**Affected files:** `main.py`, `vercel.json`, `aeo_blog_engine/pipeline/blog_workflow.py`

## Overview

The FastAPI backend deployed on Vercel has four bugs ranging from a pipeline-killing timeout to a silent CORS misconfiguration. Together they mean `POST /generate` may never return a result in production, and the health endpoint may false-alarm under normal load.

| # | Problem | Severity |
|---|---------|----------|
| 1 | Vercel function timeout — 10-agent pipeline always exceeds the limit | 🔴 Critical |
| 2 | Agno pipeline in `ThreadPoolExecutor` causes cold-start latency spikes | 🟠 High |
| 3 | CORS not confirmed — cross-origin `POST /generate` silently blocked | 🟠 High |
| 4 | `GET /health` Qdrant ping crashes the health check if Qdrant is down | 🔵 Medium |

---

## Problem 1 — Vercel Serverless Timeout on `POST /generate`

**Files:** `main.py`, `vercel.json`

### Description

Vercel Hobby tier kills serverless functions after **10 seconds**. Vercel Pro default is **60 seconds**. The 10-agent pipeline (Topic Generator + 5 blog agents + 3 social agents + QA) with DuckDuckGo searches, Qdrant RAG queries, and Gemini Flash calls routinely takes **90–180 seconds**. The function is terminated mid-pipeline and the user receives a `504 Gateway Timeout` with no content.

### Immediate Workaround (Pro plan only)

```json
// vercel.json
{
  "functions": {
    "api/index.py": {
      "maxDuration": 300
    }
  }
}
```

### Proper Fix — StreamingResponse

Switch `POST /generate` to a `StreamingResponse` so partial output is flushed as each agent completes, keeping the connection alive past Vercel's timeout window:

```python
# main.py
from fastapi.responses import StreamingResponse
import json

@app.post("/generate")
async def generate(req: GenerateRequest):
    async def event_stream():
        async for update in pipeline.run_streaming(req):
            yield f"data: {json.dumps(update)}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

> **Alternative:** If migrating the backend to Railway or Render is preferred, that removes the timeout constraint entirely. Document the change in `README.md`.

---

## Problem 2 — Agno Pipeline in `ThreadPoolExecutor`; Cold-Start Latency Spikes

**File:** `aeo_blog_engine/pipeline/blog_workflow.py`

### Description

The Agno pipeline is synchronous and is wrapped in `asyncio.get_event_loop().run_in_executor(ThreadPoolExecutor)`. On Vercel's cold-start model, a new `ThreadPoolExecutor` is created per invocation rather than reused — adding 1–3 seconds of overhead per cold request. Qdrant cloud calls and Gemini embedding calls are I/O bound and would benefit from native async rather than threading.

### Fix

Pin a single global executor at module level so it persists across warm requests:

```python
# blog_workflow.py
from concurrent.futures import ThreadPoolExecutor

_EXECUTOR = ThreadPoolExecutor(max_workers=4)  # module-level, reused across warm requests

# In the async endpoint:
result = await asyncio.get_event_loop().run_in_executor(_EXECUTOR, run_pipeline, req)
```

Additionally, use `AsyncQdrantClient` for Qdrant queries where Agno exposes async hooks, and consider replacing `run_in_executor` with `anyio.to_thread.run_sync` for better async compatibility.

---

## Problem 3 — CORS Not Confirmed; Cross-Origin Requests May Be Silently Blocked

**File:** `main.py`

### Description

The React SPA is hosted at `https://neo-scripting-neon.vercel.app` and makes `POST` requests to the FastAPI backend (a separate Vercel deployment). If `CORSMiddleware` is absent or misconfigured, the browser blocks all cross-origin requests with a CORS policy error — appearing as a generic network failure in the UI with no useful message. The API returns `200` on a direct `curl` hit while being completely broken to the frontend.

### How to Diagnose

Open browser DevTools → Network tab → trigger a `/generate` call → look for a CORS error on the preflight `OPTIONS` request.

### Required Configuration

Verify this is present in `main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://neo-scripting-neon.vercel.app",
        "http://localhost:5173",  # local dev
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

Common mistakes: trailing slash in the origin, wrong subdomain, or `allow_origins=["*"]` being shadowed by a more restrictive setting.

---

## Problem 4 — `GET /health` Crashes if Qdrant Is Unreachable

**File:** `main.py`

### Description

The `/health` endpoint performs a live Qdrant connectivity check. If Qdrant Cloud is temporarily unavailable, the health check raises an unhandled exception and returns `HTTP 500` — causing uptime monitors, the MCP `check_backend_health` tool, and Railway health probes to mark the entire API as down, even when FastAPI itself is fully operational.

### Current Behaviour

```
GET /health → 500 Internal Server Error
{"detail": "Connection refused / Qdrant timeout"}
```

### Fix — Graceful Degradation

```python
@app.get("/health")
async def health():
    qdrant_status = "ok"
    qdrant_error = None
    try:
        await qdrant_client.get_collections()
    except Exception as e:
        qdrant_status = "unreachable"
        qdrant_error = str(e)
    return {
        "status": "ok" if qdrant_status == "ok" else "degraded",
        "api": "healthy",
        "qdrant": qdrant_status,
        "qdrant_error": qdrant_error,
    }
```

The endpoint should always return `200`. Consumers can inspect the `qdrant` field to determine if the knowledge base is available.

---

## Acceptance Criteria

- [ ] `POST /generate` on a realistic prompt completes and returns `blog_markdown` + `social_posts` without a `504`
- [ ] Cold-start overhead measured below 4 seconds on Vercel Pro
- [ ] Browser DevTools shows no CORS errors on `POST /generate` from the React SPA origin
- [ ] `GET /health` returns `200` with a `degraded` status object even when Qdrant is offline
- [ ] All four fixes covered by at least one integration test or curl smoke test in CI
