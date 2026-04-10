# [BUG] MCP Server — 3 Issues Blocking Claude.ai Integration

**Labels:** `bug` `mcp` `critical` `help-wanted`  
**Affected files:** `intelliwrite-mcp/server.py`, `intelliwrite-mcp/tools.py`

## Overview

The MCP server deployed on Railway has three bugs that prevent Claude.ai from discovering and safely using IntelliWrite tools via the connector tab. All three must be resolved for the MCP integration to work end-to-end.

| # | Problem | Severity |
|---|---------|----------|
| 1 | SSE handshake not completing — Claude.ai cannot discover tools | 🔴 Critical |
| 2 | No authentication on MCP server — open relay to backend API | 🔴 Critical |
| 3 | `ingest_document` passes a local file path — unusable from remote client | 🟠 High |

---

## Problem 1 — SSE Handshake Not Completing

**File:** `intelliwrite-mcp/server.py`

### Description

When Claude.ai adds the MCP connector tab and opens the SSE connection, it immediately sends a JSON-RPC `initialize` request expecting a capability-discovery response. If `server.py` only emits raw events without handling this handshake, the tab registers but zero tools load. This is the root cause of the connector tab appearing empty in Claude.ai.

### Steps to Reproduce

1. Add the Railway MCP URL as a connector in Claude.ai settings
2. Open a conversation — no IntelliWrite tools appear in the tool list
3. Run the curl test below — the SSE stream hangs with no initial data event

```bash
curl -N -H "Accept: text/event-stream" https://your-railway-url.railway.app/sse

# Expected within 2 seconds:
data: {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{...}}}

# Actual: no output / connection hangs
```

### Expected Behaviour

On SSE connection open, the server must respond with a well-formed JSON-RPC `initialize` result that includes `protocolVersion` and a `capabilities` object listing all three tools (`generate_blog`, `ingest_document`, `check_backend_health`).

### Fix Guidance

Use the MCP Python SDK (`mcp>=1.0.0`) which provides a built-in `SSEServerTransport` that handles the handshake automatically. Verify with the curl test above before deploying.

---

## Problem 2 — No Authentication on MCP Server

**File:** `intelliwrite-mcp/server.py`

### Description

The MCP server proxies all tool calls to the FastAPI backend with no token, API key, or HMAC signature. Any actor who discovers the Railway URL can call `generate_blog` or `ingest_document` freely — burning Gemini API quota and writing arbitrary documents into the Qdrant knowledge base.

**Attack surface:**
- `generate_blog` — unlimited Gemini Flash calls at your cost
- `ingest_document` — arbitrary content injected into shared Qdrant collection
- `check_backend_health` — information leak about infrastructure state

### Proposed Fix

```python
# intelliwrite-mcp/server.py
import os, hmac
MCP_SECRET = os.environ.get("MCP_SECRET", "")

async def verify_secret(request):
    token = request.headers.get("X-MCP-Secret", "")
    if not hmac.compare_digest(token, MCP_SECRET):
        return Response("Unauthorized", status_code=401)
```

Add `MCP_SECRET=<shared-random-hex>` to Railway environment variables and to the Claude.ai connector header config.

---

## Problem 3 — `ingest_document` Passes Local File Path; Unusable from Remote Client

**File:** `intelliwrite-mcp/tools.py`

### Description

The `ingest_document` MCP tool accepts a `file_path` parameter mapping to a local filesystem path. When called from Claude.ai in the browser, there is no mechanism to resolve a local path on a remote Railway container. Every call fails with a file-not-found error.

### Current Broken Schema (inferred)

```json
{
  "name": "ingest_document",
  "parameters": {
    "file_path": { "type": "string", "description": "Local path to .md/.txt/.pdf file" }
  }
}
```

### Required Schema Change

**Option A — accept a public URL (recommended, simplest):**

```json
{ "file_url": { "type": "string", "description": "Public HTTPS URL of the document to ingest" } }
```

**Option B — accept base64-encoded content + filename:**

```json
{
  "filename": { "type": "string" },
  "content_base64": { "type": "string" },
  "mime_type": { "type": "string", "enum": ["text/markdown", "text/plain", "application/pdf"] }
}
```

Implement Option A first. Option B can follow as an enhancement.

---

## Acceptance Criteria

- [ ] `curl` test against `/sse` returns an `initialize` JSON-RPC result within 2 seconds
- [ ] Claude.ai connector tab shows all three tools: `generate_blog`, `ingest_document`, `check_backend_health`
- [ ] Unauthenticated requests to `/sse` return HTTP 401
- [ ] `ingest_document` called with a valid public URL successfully ingests the document into Qdrant
- [ ] All three tools callable end-to-end from Claude.ai with no errors
