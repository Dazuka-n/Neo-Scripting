# [DOCS] Documentation & DX — 3 Issues Causing Contributor Friction

**Labels:** `documentation` `dx` `good-first-issue`  
**Affected files:** `README.md`, `.env.example`, `main.py`, `neo-scripting-mcp/railway.toml`

## Overview

Three documentation gaps slow down contributors and cause silent failures in production. These are low-effort, high-impact fixes that improve the experience for anyone setting up a local dev environment or deploying the MCP server for the first time.

| # | Problem | Severity |
|---|---------|----------|
| 1 | Missing `neo-scripting-mcp/.env.example` — silent Railway deploy failures | ℹ️ Info |
| 2 | Railway start command undocumented in README and `railway.toml` | ℹ️ Info |
| 3 | No input validation on `platforms` field in `POST /generate` | ℹ️ Info |

---

## Problem 1 — Missing `neo-scripting-mcp/.env.example`

**Files:** `neo-scripting-mcp/` (missing `.env.example`)

### Description

The root `.env.example` only covers FastAPI backend variables. The `neo-scripting-mcp/` directory has no `.env.example`. A contributor deploying the MCP server to Railway for the first time has no authoritative list of required env vars and will only discover missing values at runtime — when the server silently fails to connect to the backend API or listens on the wrong port.

**What is currently missing:**

| Variable | Required | Notes |
|----------|----------|-------|
| `API_BASE_URL` | Yes | No default will work — must be set |
| `PORT` | No | Railway injects automatically but should be documented |
| `LOG_LEVEL` | No | Defaults to `info` but undocumented |
| `MCP_SECRET` | Yes (once auth PR merges) | Required for authenticated MCP access |

### Fix

Create `neo-scripting-mcp/.env.example`:

```env
# neo-scripting-mcp/.env.example

# Required — URL of the running FastAPI backend
API_BASE_URL=http://localhost:8000

# Optional — overrides the default port (Railway sets this automatically)
PORT=8080

# Optional — logging verbosity: debug | info | warning | error
LOG_LEVEL=info

# Required when auth is enabled (see MCP issue Problem 2)
# MCP_SECRET=your-shared-secret-here
```

Also update README.md Step 5 (MCP Server setup) to reference this file explicitly.

---

## Problem 2 — Railway Start Command Not Documented

**Files:** `README.md`, `neo-scripting-mcp/railway.toml`

### Description

The README says "deploy on Railway (Docker)" but does not show the start command Railway uses. Contributors don't know whether the entrypoint is `uvicorn server:starlette_app`, `python server.py`, or something else. If `railway.toml` is missing the `startCommand`, Railway falls back to its auto-detect heuristic which may start the wrong file.

### Fix — Add to README.md under the MCP Server section

```markdown
## MCP Server — Railway Deploy

**Start command:** `uvicorn server:starlette_app --host 0.0.0.0 --port $PORT`

**Required Railway environment variables:**
- `API_BASE_URL` — your Vercel backend URL
- `PORT` — set automatically by Railway
```

### Fix — Verify `railway.toml` has an explicit start command

```toml
# neo-scripting-mcp/railway.toml
[deploy]
startCommand = "uvicorn server:starlette_app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 10
```

---

## Problem 3 — No Input Validation on `platforms` Field in `POST /generate`

**Files:** `main.py`, `aeo_blog_engine/pipeline/blog_workflow.py`

### Description

The `POST /generate` request body accepts a `platforms` array with no Pydantic enum or `Literal` validation. Passing an invalid value like `"instagram"`, `"tiktok"`, or a typo like `"tweeter"` either produces an empty social post entry silently or raises an unhandled `KeyError`/`AttributeError` deep inside the pipeline, returning a `500` with no useful error message.

### Current Schema (no validation)

```python
# main.py — current
class GenerateRequest(BaseModel):
    prompt: str
    brand_name: str = ""
    company_url: str = ""
    platforms: list[str] = ["linkedin", "twitter", "reddit"]  # no validation
```

### Fix

```python
# main.py — fixed
from typing import Literal

Platform = Literal["linkedin", "twitter", "reddit"]

class GenerateRequest(BaseModel):
    prompt: str
    brand_name: str = ""
    company_url: str = ""
    platforms: list[Platform] = ["linkedin", "twitter", "reddit"]
```

With this fix, an invalid platform name returns `HTTP 422 Unprocessable Entity` with a clear Pydantic error rather than a silent failure or a `500` deep in the pipeline.

---

## Acceptance Criteria

- [ ] `neo-scripting-mcp/.env.example` exists and documents all MCP server env vars with inline comments
- [ ] README.md Step 5 references the `.env.example` and shows the exact Railway start command
- [ ] `railway.toml` has an explicit `startCommand` matching the README docs
- [ ] `POST /generate` with `platforms: ["instagram"]` returns `HTTP 422` with a Pydantic validation error
- [ ] `POST /generate` with `platforms: ["linkedin"]` returns only a `linkedin` key in `social_posts`
