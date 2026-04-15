# Neo Scripting MCP Server

A standalone [Model Context Protocol](https://modelcontextprotocol.io) server that wraps the Neo Scripting FastAPI backend and exposes its AEO blog generation capabilities as MCP tools. Any MCP-compatible agent — Claude Desktop, Claude Code, Cursor, Windsurf — can connect to this server over HTTP/SSE and call the tools directly, without writing a single line of integration code.

---

## Tools Exposed

| Tool | Description |
|---|---|
| `generate_blog` | Run the full 6-agent AEO/GEO pipeline — research, plan, write, optimize, QA — and return a publish-ready blog + social posts |
| `ingest_document` | Add a `.md`, `.txt`, or `.pdf` file to the Qdrant knowledge base used by the researcher agent |
| `check_backend_health` | Verify the FastAPI backend and Qdrant are online |

---

## Prerequisites

- Python 3.10+
- The Neo Scripting FastAPI backend running (see the main project)
- Your backend URL (local: `http://localhost:8000`, or deployed URL)

---

## Environment Setup

```bash
cp .env.example .env
```

Open `.env` and set:

```env
API_BASE_URL=http://localhost:8000   # or your deployed backend URL
```

---

## Local Run

```bash
pip install -r requirements.txt
uvicorn server:starlette_app --host 0.0.0.0 --port 8080
```

The server starts at `http://localhost:8080` with:
- `GET  /sse`      — SSE connection endpoint for MCP clients
- `POST /messages` — Message posting endpoint
- `GET  /health`   — Health check for the MCP server itself

---

## Connecting MCP Clients

> Replace `http://localhost:8080` with your deployed Railway URL once live.

### Claude Desktop

Add to `claude_desktop_config.json`:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "neo-scripting": {
      "type": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Restart Claude Desktop after saving.

---

### Claude Code

```bash
claude mcp add neo-scripting --transport sse http://localhost:8080/sse
```

Verify it was added:

```bash
claude mcp list
```

---

### Cursor

1. Open **Settings** → **Features** → **MCP**
2. Click **Add New MCP Server**
3. Set **Name**: `neo-scripting`
4. Set **Type**: `SSE`
5. Set **URL**: `http://localhost:8080/sse`
6. Save and restart Cursor

---

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "neo-scripting": {
      "serverUrl": "http://localhost:8080/sse"
    }
  }
}
```

Restart Windsurf after saving.

---

## Example Prompts

Once connected, use natural language — your agent handles the tool calls:

```
Generate a blog about AI automation in logistics for my brand at mycompany.com
```

```
Check if the Neo Scripting backend is online
```

```
Ingest /path/to/brand-guidelines.pdf into the knowledge base
```

```
Write a blog post about sustainable packaging trends for EcoBox at ecobox.io,
and generate posts for LinkedIn and Twitter
```

---

## Deploying to Railway

1. Push this directory to a GitHub repo
2. Create a new Railway project → **Deploy from GitHub**
3. Add environment variable: `API_BASE_URL=<your-fastapi-backend-url>`
4. Railway auto-detects the `Dockerfile` and deploys

Once deployed, update your MCP client config:
```
https://your-project.up.railway.app/sse
```

---

## Project Structure

```
neo-scripting-mcp/
├── server.py        ← Starlette app + MCP server + SSE transport wiring
├── tools.py         ← Tool definitions (schemas) and async handlers
├── config.py        ← Env var loading, validation, backend health probe
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env.example
└── README.md
```
