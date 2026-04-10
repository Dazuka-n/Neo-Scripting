# Intelliwrite — Full Resolution Guide
### Approach, Solution & Claude Code Prompts for Every Issue

---

## How to Use This Document

Each section maps to one GitHub issue. For every problem you will find:
- **Approach** — what to understand before touching code
- **Solution** — exact steps and files to change
- **Claude Code Prompt** — paste this directly into Claude Code to execute the fix

Work through issues in this order: **MCP → Backend → Frontend → Docs**. The MCP SSE fix and the Backend streaming fix are co-dependent — do them in the same session.

---

---

# ISSUE 1 — MCP Server

---

## Problem 1 — SSE Handshake Not Completing

### Approach

The MCP protocol requires a JSON-RPC `initialize` / `initialized` handshake the moment a client connects over SSE. Claude.ai opens the SSE connection and sends `initialize` expecting the server to reply with its `protocolVersion` and a `capabilities` object listing all tools. If the server never replies, Claude.ai times out and shows an empty tool list.

The current `server.py` uses raw Starlette SSE and manually constructs event streams. It likely never handles the `initialize` message at all. The cleanest fix is to replace the manual SSE plumbing with the official `mcp` Python SDK which handles the full protocol handshake, session management, and tool dispatch automatically.

### Solution

1. Add `mcp>=1.0.0` to `intelliwrite-mcp/requirements.txt`
2. Rewrite `server.py` to use `mcp.server.fastmcp.FastMCP` or `mcp.server.Server` with `SSEServerTransport`
3. Register the three tools (`generate_blog`, `ingest_document`, `check_backend_health`) using the SDK's `@mcp.tool()` decorator
4. Keep all HTTP proxy logic in `tools.py` — only the transport layer changes in `server.py`
5. Test with `curl -N -H "Accept: text/event-stream" http://localhost:8080/sse` — you must see a `data:` event within 2 seconds

### Claude Code Prompt

```
I need you to fix the MCP server in the `intelliwrite-mcp/` directory so that Claude.ai
can discover its tools via the SSE connector tab.

CONTEXT
- The server currently uses raw Starlette SSE (server.py) and manually emits events
- Claude.ai requires a proper MCP JSON-RPC handshake (initialize → initialized → tools/list)
- The server exposes 3 tools: generate_blog, ingest_document, check_backend_health
- Tool HTTP proxy logic lives in tools.py and should stay there
- The server runs on Railway via Docker; start command is: uvicorn server:starlette_app --host 0.0.0.0 --port $PORT

TASK
1. Read the current intelliwrite-mcp/server.py and intelliwrite-mcp/tools.py in full
2. Add `mcp>=1.0.0` to intelliwrite-mcp/requirements.txt
3. Rewrite server.py to use the official MCP Python SDK.
   Use FastMCP (from mcp.server.fastmcp import FastMCP) — it is the simplest path.
   Example structure:
     from mcp.server.fastmcp import FastMCP
     mcp = FastMCP("intelliwrite")

     @mcp.tool()
     async def generate_blog(prompt: str, brand_name: str = "", ...) -> dict:
         ...

     if __name__ == "__main__":
         mcp.run(transport="sse")

4. Wire each @mcp.tool() handler to call the corresponding function already in tools.py
   (do not duplicate the HTTP proxy logic — import and call it)
5. Preserve the starlette_app export so the existing uvicorn start command still works:
     starlette_app = mcp.get_asgi_app()
6. Write a smoke test: a bash one-liner using curl that connects to /sse and asserts
   the first data event is received within 3 seconds
7. Update intelliwrite-mcp/README or docstring to document the new structure

Do not change tools.py HTTP logic. Do not change the Dockerfile. Only touch server.py
and requirements.txt.
```

---

## Problem 2 — No Authentication on MCP Server

### Approach

The Railway URL is public. Without a shared secret, anyone who finds the URL can call `generate_blog` in a loop, burning your Gemini quota at no cost to them. The simplest production-safe approach is a shared `MCP_SECRET` env var that the MCP server checks on every incoming SSE connection via a request header.

Claude.ai lets you set custom headers per connector in the connector settings — so the client side is covered without any SDK changes.

### Solution

1. Add an `X-MCP-Secret` header check in `server.py` before the SSE session is established
2. Use `hmac.compare_digest` (constant-time) to avoid timing attacks
3. Return `401` if the header is missing or wrong
4. Add `MCP_SECRET` to `intelliwrite-mcp/.env.example` and Railway env vars
5. Document in README how to set the header in Claude.ai connector settings

### Claude Code Prompt

```
I need you to add shared-secret authentication to the MCP server in intelliwrite-mcp/server.py.

CONTEXT
- The server is publicly hosted on Railway with no auth
- Claude.ai connectors support custom request headers per connector config
- We want to validate an X-MCP-Secret header on every incoming SSE connection
- MCP_SECRET will be set as a Railway environment variable

TASK
1. Read intelliwrite-mcp/server.py
2. Add authentication middleware that:
   - Reads MCP_SECRET from os.environ (default empty string if not set)
   - On every request to /sse, checks the X-MCP-Secret header
   - Uses hmac.compare_digest for constant-time comparison
   - Returns a plain 401 Response if the header is missing or wrong
   - Passes through if the secret matches or if MCP_SECRET is not set (dev mode)
3. Add a startup log message: if MCP_SECRET is empty, log a WARNING:
   "MCP_SECRET not set — server is unauthenticated. Set this in production."
4. Create intelliwrite-mcp/.env.example if it does not exist and add:
   MCP_SECRET=your-shared-secret-here
5. Add a comment in server.py explaining how to set the header in Claude.ai:
   # In Claude.ai connector settings → Headers → add: X-MCP-Secret: <your-secret>

Keep changes minimal — only touch server.py and .env.example.
```

---

## Problem 3 — `ingest_document` Passes Local File Path

### Approach

SSE is a text transport. You cannot send binary file data through it as a path string and expect the remote container to resolve it. The tool schema needs to change from accepting a filesystem path to accepting either a **public URL** (Option A, simplest) or **base64-encoded content** (Option B, flexible).

Option A is the right starting point — it covers 90% of real use cases (GitHub raw URLs, Google Drive share links, S3 pre-signed URLs) with zero complexity on the client side.

### Solution

1. Change the `ingest_document` tool parameter from `file_path: str` to `file_url: str`
2. In `tools.py`, download the file from the URL using `httpx.AsyncClient` before passing it to `POST /ingest`
3. Stream the downloaded bytes as a multipart upload to the FastAPI `/ingest` endpoint
4. Update the tool description string so Claude knows to pass a URL

### Claude Code Prompt

```
I need you to fix the ingest_document MCP tool so it works when called from a remote
Claude.ai client (not a local filesystem).

CONTEXT
- Current tools.py accepts file_path (local path) — unusable over remote SSE
- The FastAPI backend has a POST /ingest endpoint that accepts a file upload
- We want to accept a public HTTPS URL instead and proxy the download to /ingest
- API_BASE_URL is available via os.environ

TASK
1. Read intelliwrite-mcp/tools.py and intelliwrite-mcp/server.py in full
2. Change the ingest_document tool to accept file_url: str instead of file_path
3. In the tool handler:
   a. Use httpx.AsyncClient to GET the file_url and read the response bytes
   b. Infer the filename from the URL path (last segment after /)
   c. Infer the content-type from the URL extension:
      .md / .txt → text/plain
      .pdf → application/pdf
   d. POST the bytes as a multipart upload to {API_BASE_URL}/ingest
      using httpx multipart form: files={"file": (filename, content, content_type)}
   e. Return the JSON response from /ingest
4. Update the tool's description string to say:
   "Ingest a document into the Qdrant knowledge base. Pass a public HTTPS URL
    to a .md, .txt, or .pdf file."
5. Add httpx to intelliwrite-mcp/requirements.txt if not already present
6. Add a try/except around the download step — if the URL is unreachable return a
   clear error dict: {"error": "Could not download file", "url": file_url, "detail": str(e)}

Only touch tools.py and requirements.txt.
```

---

---

# ISSUE 2 — Backend API

---

## Problem 1 — Vercel Serverless Timeout

### Approach

Vercel kills serverless functions at 10s (Hobby) or 60s (Pro). The 10-agent pipeline takes 90–180s. There are two parallel tracks:

**Track A (quick, buy time):** Set `maxDuration: 300` in `vercel.json`. This only works on Pro and only extends to 5 minutes — still risky for slow prompts.

**Track B (proper fix):** Switch `POST /generate` to a `StreamingResponse` using Server-Sent Events. As each agent completes, flush a `data:` event. Vercel treats streaming responses differently — the connection stays alive as long as data is flowing. This also unlocks real-time progress in the frontend.

Do both — Track A as an immediate safeguard, Track B as the architectural fix.

### Solution

1. Add `maxDuration: 300` to `vercel.json` under the `api/index.py` function config
2. Add a `POST /generate/stream` endpoint in `main.py` that returns `StreamingResponse`
3. Modify `AEOBlogPipeline` (or `blog_workflow.py`) to support a generator/async-generator mode that yields progress events
4. Keep `POST /generate` (non-streaming) working for backward compatibility and for the MCP tool
5. Emit structured SSE events: `{"event": "agent_done", "agent": "researcher"}` and finally `{"event": "complete", "result": {...}}`

### Claude Code Prompt

```
I need to fix a critical timeout issue: the FastAPI backend on Vercel times out before
the 10-agent pipeline finishes. I need two things: a vercel.json maxDuration fix and
a proper streaming endpoint.

CONTEXT
- main.py has POST /generate which runs AEOBlogPipeline synchronously in a ThreadPoolExecutor
- The pipeline in aeo_blog_engine/pipeline/blog_workflow.py takes 90-180 seconds
- Vercel kills functions at 60s on Pro; streaming connections stay alive as long as data flows
- The MCP tool generate_blog calls POST /generate (non-streaming) — keep that working
- The React frontend will be updated separately to consume the streaming endpoint

TASK — Part 1: vercel.json
1. Read vercel.json
2. Add maxDuration: 300 to the api/index.py function config:
   {
     "functions": {
       "api/index.py": { "maxDuration": 300 }
     }
   }

TASK — Part 2: Streaming endpoint
1. Read main.py and aeo_blog_engine/pipeline/blog_workflow.py in full
2. Add a new endpoint POST /generate/stream that:
   a. Accepts the same GenerateRequest body as POST /generate
   b. Returns StreamingResponse with media_type="text/event-stream"
   c. Emits SSE events in this format:
      data: {"event": "agent_done", "agent": "topic_generator"}\n\n
      data: {"event": "agent_done", "agent": "researcher"}\n\n
      data: {"event": "agent_done", "agent": "planner"}\n\n
      data: {"event": "agent_done", "agent": "writer"}\n\n
      data: {"event": "agent_done", "agent": "optimizer"}\n\n
      data: {"event": "agent_done", "agent": "final_editor"}\n\n
      data: {"event": "agent_done", "agent": "social_researcher"}\n\n
      data: {"event": "agent_done", "agent": "social_writer"}\n\n
      data: {"event": "agent_done", "agent": "social_qa"}\n\n
      data: {"event": "complete", "result": {"blog_markdown": "...", "social_posts": {...}}}\n\n
3. To emit agent_done events, instrument blog_workflow.py to accept an optional
   progress_callback: Optional[Callable[[str], None]] = None parameter on the
   pipeline run method, and call it after each agent step completes
4. In the streaming endpoint, use asyncio.Queue to bridge the sync pipeline thread
   and the async generator:
   - Run the pipeline in run_in_executor with a queue.put progress callback
   - The async generator awaits queue.get() and yields SSE events
5. Keep POST /generate (non-streaming, returns full JSON) working exactly as before
6. Add a CORS header check — ensure text/event-stream responses also pass CORS

Do not change agent logic. Only touch main.py, blog_workflow.py, and vercel.json.
```

---

## Problem 2 — Agno Pipeline in `ThreadPoolExecutor` Cold-Start Latency

### Approach

The current code likely creates a new `ThreadPoolExecutor` inside the request handler on every call. On Vercel cold starts this creates a fresh pool with no warm threads. The fix is a single module-level executor instance that persists across warm requests (Vercel reuses the same process for concurrent requests within a deployment window).

### Solution

1. Move `ThreadPoolExecutor` to module level in `blog_workflow.py` or `main.py`
2. Set `max_workers=4` (enough for concurrent social pipeline branches)
3. Swap `asyncio.get_event_loop()` for `asyncio.get_running_loop()` (correct in async context)
4. Where Agno/Qdrant expose async clients, use them

### Claude Code Prompt

```
I need to fix cold-start latency in the FastAPI backend caused by a per-request
ThreadPoolExecutor and blocking I/O patterns.

CONTEXT
- The Agno pipeline is synchronous and runs in a ThreadPoolExecutor
- A new executor is likely created per request — this is wasteful on Vercel
- asyncio.get_event_loop() is deprecated in async context; use get_running_loop()
- Qdrant client may have an async variant available

TASK
1. Read main.py and aeo_blog_engine/pipeline/blog_workflow.py
2. Find every ThreadPoolExecutor instantiation that happens inside a function or
   request handler
3. Move the executor to module level with max_workers=4:
     from concurrent.futures import ThreadPoolExecutor
     _EXECUTOR = ThreadPoolExecutor(max_workers=4)
4. Replace all asyncio.get_event_loop().run_in_executor(...) calls with:
     asyncio.get_running_loop().run_in_executor(_EXECUTOR, ...)
5. Check aeo_blog_engine/knowledge/knowledge_base.py — if QdrantClient is used,
   check if qdrant-client supports AsyncQdrantClient (it does as of v1.7).
   If the knowledge base does sync Qdrant calls inside the async path, note this
   with a TODO comment and wrap those specific calls in run_in_executor as well.
6. Add a startup log in main.py lifespan or startup event:
     logger.info(f"ThreadPoolExecutor initialized with {_EXECUTOR._max_workers} workers")

Only touch main.py, blog_workflow.py, and knowledge_base.py. No logic changes.
```

---

## Problem 3 — CORS Not Confirmed

### Approach

CORS is a browser-enforced policy. The backend must explicitly respond to preflight `OPTIONS` requests with the right headers. On Vercel serverless, the middleware must be registered before any routes. A common silent failure is having the right code but wrong origin string (trailing slash, wrong subdomain, HTTP vs HTTPS).

### Solution

1. Verify `CORSMiddleware` is present in `main.py` with the exact production origin
2. Add `http://localhost:5173` for local dev
3. Add `OPTIONS` to `allow_methods`
4. Test with a curl preflight from the terminal

### Claude Code Prompt

```
I need to audit and fix CORS configuration in the FastAPI backend.

CONTEXT
- Frontend is at: https://intelliwrite-neon.vercel.app
- Backend is a separate Vercel deployment
- Browser blocks cross-origin requests if CORS headers are missing or wrong
- This must be verified and hardened, not just assumed to be correct

TASK
1. Read main.py in full
2. Check if CORSMiddleware is present. If it is, verify:
   a. allow_origins includes exactly "https://intelliwrite-neon.vercel.app" (no trailing slash)
   b. allow_origins includes "http://localhost:5173" for local dev
   c. allow_methods includes "OPTIONS" (required for preflight)
   d. allow_headers is ["*"] or explicitly includes "Content-Type"
   e. The middleware is added BEFORE any route definitions
3. If CORSMiddleware is missing or misconfigured, add/fix it:
     from fastapi.middleware.cors import CORSMiddleware
     app.add_middleware(
         CORSMiddleware,
         allow_origins=[
             "https://intelliwrite-neon.vercel.app",
             "http://localhost:5173",
         ],
         allow_methods=["GET", "POST", "OPTIONS"],
         allow_headers=["*"],
     )
4. After making changes, write a bash smoke test in a new file scripts/test_cors.sh:
     curl -v -X OPTIONS https://<your-backend-url>/generate \
       -H "Origin: https://intelliwrite-neon.vercel.app" \
       -H "Access-Control-Request-Method: POST" \
       -H "Access-Control-Request-Headers: Content-Type"
   The response must include: Access-Control-Allow-Origin: https://intelliwrite-neon.vercel.app
5. Add a comment above the middleware explaining why both origins are listed

Only touch main.py and create scripts/test_cors.sh.
```

---

## Problem 4 — `GET /health` Crashes if Qdrant Is Unreachable

### Approach

A health endpoint should never return `5xx`. Its job is to report what is healthy and what is degraded. Wrap the Qdrant check in a `try/except`, return `200` always, and let the consumer decide what to do with a `degraded` status.

### Solution

1. Wrap the Qdrant ping in `try/except Exception`
2. Return a structured JSON with separate `api` and `qdrant` fields
3. Use `status: "degraded"` (not 500) when Qdrant is down
4. Include `qdrant_error` field for debugging

### Claude Code Prompt

```
I need to fix the GET /health endpoint in main.py so it never returns 5xx even
when Qdrant is unreachable.

CONTEXT
- Current /health does a live Qdrant ping; if Qdrant is down it raises and returns 500
- This causes uptime monitors and the MCP check_backend_health tool to report the API as down
- The fix is graceful degradation: always return 200, report component status in the body

TASK
1. Read main.py and find the GET /health endpoint
2. Rewrite it to:
     @app.get("/health")
     async def health():
         qdrant_status = "ok"
         qdrant_error = None
         try:
             # existing Qdrant connectivity check here
         except Exception as e:
             qdrant_status = "unreachable"
             qdrant_error = str(e)
         return {
             "status": "ok" if qdrant_status == "ok" else "degraded",
             "api": "healthy",
             "qdrant": qdrant_status,
             "qdrant_error": qdrant_error,
         }
3. The HTTP status code must always be 200 — never raise from this endpoint
4. Add a log line when Qdrant is unreachable:
     logger.warning(f"Health check: Qdrant unreachable — {qdrant_error}")
5. If the existing Qdrant check is async, keep it async. If it's sync, wrap it in
   run_in_executor using the module-level _EXECUTOR (from Problem 2 fix).

Only touch main.py.
```

---

---

# ISSUE 3 — Frontend

---

## Problem 1 — Hard Refresh on `/result` Loses All Content

### Approach

React Router `location.state` is in-memory only — it does not survive a page reload. The fix is to mirror the result to `sessionStorage` the moment it arrives, and read from `sessionStorage` as a fallback when `location.state` is null on mount. `sessionStorage` is scoped to the browser tab and clears when the tab closes — the right tradeoff for generated content.

### Solution

1. On mount in `Result.jsx`, if `state` is present, write it to `sessionStorage`
2. If `state` is null (page was refreshed), read from `sessionStorage`
3. If both are null, show a friendly "No result" message with a link back to the form
4. Clear `sessionStorage` when the user starts a new generation in `Home.jsx`

### Claude Code Prompt

```
I need to fix Result.jsx so generated content survives a browser page refresh.

CONTEXT
- The app navigates to /result via React Router navigate('/result', { state: data })
- On refresh, location.state is null and the page breaks
- Fix: persist result to sessionStorage on arrival, restore on mount if state is missing
- Stack: React 18, React Router DOM v6, Vite

TASK
1. Read frontend/src/pages/Result.jsx in full
2. Add sessionStorage persistence:
     const STORAGE_KEY = "intelliwrite_last_result"

     useEffect(() => {
       if (state) {
         sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
         setResult(state)
       } else {
         const saved = sessionStorage.getItem(STORAGE_KEY)
         if (saved) {
           try { setResult(JSON.parse(saved)) }
           catch { sessionStorage.removeItem(STORAGE_KEY) }
         }
       }
     }, [state])
3. Add a null-result UI:
   if (!result) return a div with: "No result found." and an <a href="/">Generate new content</a> link
4. Read frontend/src/pages/Home.jsx — at the start of the form submit handler, add:
     sessionStorage.removeItem("intelliwrite_last_result")
   so stale results are cleared when a new generation starts
5. Do not change the result rendering logic — only add the persistence layer

Only touch Result.jsx and Home.jsx.
```

---

## Problem 2 — No Timeout or Cancel on `POST /generate`

### Approach

`AbortController` is the native browser API for cancelling fetch requests. Attach its `signal` to the fetch call, set a `setTimeout` to call `abort()` after 120 seconds, and clear the timeout on success. Expose a Cancel button in the UI while the request is in-flight.

### Solution

1. Create an `AbortController` at the start of `handleSubmit`
2. Store it in state so the JSX can call `controller.abort()` from a button
3. Set a 120-second timeout that auto-aborts
4. In the catch block, distinguish `AbortError` from other errors and show appropriate messages
5. Clear the controller and timeout in a `finally` block

### Claude Code Prompt

```
I need to add request timeout and cancel functionality to the POST /generate fetch
call in the React frontend.

CONTEXT
- Home.jsx has a form submit handler that calls POST /generate
- There is no AbortController, no timeout, and no cancel button
- The backend can take 90-180 seconds; users need to be able to cancel
- Stack: React 18, hooks only (no class components)

TASK
1. Read frontend/src/pages/Home.jsx in full
2. Add an abortController state: const [controller, setController] = useState(null)
3. In the submit handler:
   a. Create a new AbortController at the start
   b. Store it: setController(ac)
   c. Set a 120-second auto-abort: const tid = setTimeout(() => ac.abort(), 120_000)
   d. Pass signal: ac.signal to the fetch options
   e. In finally: clearTimeout(tid); setController(null)
4. In the catch block, handle AbortError specifically:
     if (err.name === "AbortError") {
       setError("Request was cancelled or timed out. Please try again.")
     } else {
       setError("Something went wrong. Please check your connection and try again.")
     }
5. In the JSX loading state, render a Cancel button when controller is not null:
     {isLoading && controller && (
       <button
         onClick={() => controller.abort()}
         type="button"
       >
         Cancel
       </button>
     )}
6. Make sure the Cancel button is visually distinct from the Submit button
   (use a secondary/outline style — check the existing Tailwind classes used in the file)

Only touch Home.jsx.
```

---

## Problem 3 — `StepTracker` Shows Fake Progress

### Approach

This is a two-phase fix. Phase 1 (do now, 10 minutes): remove the fake timer and replace with an honest indeterminate spinner + elapsed time counter. Phase 2 (do after Backend Problem 1 streaming is merged): wire `StepTracker` to real SSE events from `POST /generate/stream`.

Both phases are documented below. Start with Phase 1 — it ships immediately. Phase 2 is the Claude Code prompt to run after the streaming backend is live.

### Solution — Phase 1 (Immediate)

Replace the timer-based advancement with an elapsed-time display.

### Claude Code Prompt — Phase 1

```
I need to fix StepTracker.jsx to remove fake timer-based progress and replace it
with an honest indeterminate state + elapsed time counter.

CONTEXT
- StepTracker advances through pipeline steps on a fixed timer, not real events
- This is misleading — it shows "Writer complete" while the researcher may still run
- Phase 1 fix: remove the timer, show a spinner and elapsed seconds counter
- Phase 2 (separate PR): wire to real SSE events after streaming backend ships

TASK
1. Read frontend/src/components/StepTracker.jsx in full
2. Remove all setTimeout / setInterval based step advancement logic
3. Replace the component body with:
   - A simple indeterminate spinner (use the existing spinner component if one exists,
     otherwise a Tailwind animate-spin div)
   - An elapsed time counter that starts at 0 when isLoading becomes true:
       const [elapsed, setElapsed] = useState(0)
       useEffect(() => {
         if (!isLoading) { setElapsed(0); return }
         const id = setInterval(() => setElapsed(s => s + 1), 1000)
         return () => clearInterval(id)
       }, [isLoading])
   - Display text: "Generating your content... ({elapsed}s)"
   - A subtext: "This takes 1-3 minutes. Please keep this tab open."
4. Keep the component's props interface (whatever isLoading / steps props exist)
   so the parent does not need to change
5. Do not delete the step list rendering entirely — comment it out with a TODO:
   // TODO: Phase 2 — uncomment and wire to real SSE events from POST /generate/stream

Only touch StepTracker.jsx.
```

### Claude Code Prompt — Phase 2 (run after streaming backend is deployed)

```
The backend now emits SSE progress events from POST /generate/stream. I need to
wire StepTracker.jsx and Home.jsx to consume these real events.

CONTEXT
- POST /generate/stream emits SSE events:
    data: {"event": "agent_done", "agent": "researcher"}
    data: {"event": "agent_done", "agent": "planner"}
    ... (one per agent)
    data: {"event": "complete", "result": {"blog_markdown": "...", "social_posts": {...}}}
- The current Home.jsx uses a regular fetch to POST /generate
- StepTracker.jsx was updated in Phase 1 to show elapsed time (not real steps)
- Stack: React 18, hooks, Vite, VITE_API_BASE_URL env var

TASK
1. Read Home.jsx, StepTracker.jsx, and Result.jsx in full
2. In Home.jsx, replace the fetch call with an EventSource connection to POST /generate/stream.
   Since EventSource is GET-only, use fetch with a ReadableStream instead:
     const response = await fetch(`${API_BASE}/generate/stream`, {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify(formData),
       signal: controller.signal,
     })
     const reader = response.body.getReader()
     const decoder = new TextDecoder()
     while (true) {
       const { done, value } = await reader.read()
       if (done) break
       const lines = decoder.decode(value).split("\n")
       for (const line of lines) {
         if (line.startsWith("data: ")) {
           const parsed = JSON.parse(line.slice(6))
           if (parsed.event === "agent_done") setCompletedAgents(prev => [...prev, parsed.agent])
           if (parsed.event === "complete") { navigate("/result", { state: parsed.result }); return }
         }
       }
     }
3. Pass completedAgents as a prop to StepTracker
4. In StepTracker.jsx, uncomment the step list and render each agent name as a step,
   marking it complete when its name appears in completedAgents:
   const STEPS = ["topic_generator","researcher","planner","writer","optimizer",
                  "final_editor","social_researcher","social_writer","social_qa"]
5. Keep the elapsed time counter running alongside the step list
6. Keep the AbortController cancel button from the previous fix

Only touch Home.jsx and StepTracker.jsx.
```

---

---

# ISSUE 4 — Documentation & DX

---

## Problem 1 — Missing `intelliwrite-mcp/.env.example`

### Approach

Simple file creation. The `.env.example` is the canonical reference for what environment variables a service needs. It should be comprehensive, commented, and committed to the repo. Treat it as documentation, not just a template.

### Claude Code Prompt

```
I need to create a .env.example file for the MCP server sub-package.

TASK
1. Read intelliwrite-mcp/server.py and intelliwrite-mcp/tools.py to identify every
   os.environ.get() or os.getenv() call
2. Also read the root .env.example to understand the existing format/style
3. Create intelliwrite-mcp/.env.example with all discovered variables, formatted as:
   - Required variables first, with a comment explaining what they connect to
   - Optional variables second, with their default value shown in a comment
   - A section at the bottom for variables that will be required after upcoming PRs
     (MCP_SECRET from the auth fix)
   - Match the comment style of the root .env.example
4. The file must include at minimum:
   API_BASE_URL, PORT, LOG_LEVEL, and a commented-out MCP_SECRET
5. After creating the file, update README.md Step 5 (MCP Server section) to add:
   "Copy intelliwrite-mcp/.env.example to intelliwrite-mcp/.env and fill in your values."
   directly below the "Prerequisites" or setup heading in that section

Create intelliwrite-mcp/.env.example and update README.md only.
```

---

## Problem 2 — Railway Start Command Undocumented

### Approach

`railway.toml` should be the single source of truth for how the service starts. The README should mirror this exactly so contributors know what Railway will run without having to read the TOML file. Both need to be consistent.

### Claude Code Prompt

```
I need to document and verify the Railway start command for the MCP server.

TASK
1. Read intelliwrite-mcp/railway.toml, intelliwrite-mcp/Dockerfile,
   and intelliwrite-mcp/server.py
2. Determine the correct start command:
   - If server.py exports starlette_app, the command is:
     uvicorn server:starlette_app --host 0.0.0.0 --port $PORT
   - If it uses FastMCP's mcp.run(), it may be: python server.py
   - Use whatever matches the actual server.py entrypoint
3. Update railway.toml to have an explicit startCommand:
     [deploy]
     startCommand = "<correct command>"
     healthcheckPath = "/health"
     healthcheckTimeout = 10
4. Update README.md in the MCP Server section (Step 5 or equivalent) to add a
   sub-section "Railway Deployment" that shows:
   - The exact start command
   - Required Railway environment variables (as a table)
   - A note that PORT is injected automatically by Railway
5. If the Dockerfile has a CMD that conflicts with railway.toml, reconcile them
   so they agree on the same command

Touch railway.toml and README.md only. Do not change server.py.
```

---

## Problem 3 — No Input Validation on `platforms` Field

### Approach

Pydantic `Literal` types are the cleanest way to enforce an enum on a list field. One line of change gives you automatic `422` responses with human-readable error messages. No custom validators needed.

### Claude Code Prompt

```
I need to add Pydantic input validation to the platforms field in POST /generate.

CONTEXT
- main.py has a GenerateRequest Pydantic model
- The platforms field is currently list[str] with no validation
- Passing "instagram" or a typo causes a silent failure or 500 deep in the pipeline
- Fix: use Literal types so Pydantic returns a 422 with a clear message

TASK
1. Read main.py and find the GenerateRequest model
2. Change the platforms field type:
     from typing import Literal

     Platform = Literal["linkedin", "twitter", "reddit"]

     class GenerateRequest(BaseModel):
         prompt: str
         brand_name: str = ""
         company_url: str = ""
         platforms: list[Platform] = ["linkedin", "twitter", "reddit"]
3. Also add validation for prompt — it should not be empty:
     from pydantic import field_validator

     @field_validator("prompt")
     @classmethod
     def prompt_not_empty(cls, v):
         if not v.strip():
             raise ValueError("prompt must not be empty")
         return v.strip()
4. Write a test in a new file tests/test_validation.py using httpx.AsyncClient
   and pytest-asyncio that asserts:
   - POST /generate with platforms: ["instagram"] returns 422
   - POST /generate with prompt: "" returns 422
   - POST /generate with platforms: ["linkedin"] passes validation
5. Add pytest and pytest-asyncio to requirements.txt if not present
   (only if a tests/ directory does not already exist with a different test runner)

Only touch main.py and create tests/test_validation.py.
```

---

---

## Suggested PR Order

| PR | Branch name | Depends on |
|----|-------------|------------|
| 1 | `fix/mcp-sse-handshake` | nothing |
| 2 | `fix/mcp-auth` | PR 1 |
| 3 | `fix/mcp-ingest-url` | PR 1 |
| 4 | `fix/backend-streaming` | nothing |
| 5 | `fix/backend-cors` | nothing |
| 6 | `fix/backend-executor` | nothing |
| 7 | `fix/backend-health` | nothing |
| 8 | `fix/frontend-result-persist` | nothing |
| 9 | `fix/frontend-cancel` | nothing |
| 10 | `fix/frontend-steptracker-phase1` | nothing |
| 11 | `fix/frontend-steptracker-phase2` | PR 4 + PR 10 |
| 12 | `docs/mcp-env-example` | PR 1, PR 2 |
| 13 | `docs/railway-start-command` | PR 1 |
| 14 | `fix/api-validation` | nothing |
