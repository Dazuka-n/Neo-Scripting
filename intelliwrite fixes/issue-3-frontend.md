# [BUG] Frontend — 3 Issues Affecting UX and Data Persistence

**Labels:** `bug` `frontend` `ux` `help-wanted`  
**Affected files:** `frontend/src/pages/Result.jsx`, `frontend/src/pages/Home.jsx`, `frontend/src/components/StepTracker.jsx`

## Overview

Three frontend bugs degrade the user experience significantly: generated content is lost on page refresh, the loading state has no cancel mechanism, and the progress tracker shows fabricated pipeline state. None of these require backend changes to fix.

| # | Problem | Severity |
|---|---------|----------|
| 1 | Hard refresh on `/result` loses all generated content | 🟠 High |
| 2 | No request timeout or cancel on `POST /generate` — spinner hangs forever | 🔵 Medium |
| 3 | `StepTracker` advances on a timer, not real pipeline events — misleading UX | 🔵 Medium |

---

## Problem 1 — Hard Refresh on `/result` Loses All Generated Content

**File:** `frontend/src/pages/Result.jsx`

### Description

After `POST /generate` completes, the app navigates to `/result` passing `blog_markdown` and `social_posts` via React Router's `location.state`. If the user refreshes the page, opens it in a new tab, or navigates back and forward, React Router state is gone — the page renders blank or throws a `Cannot read property of undefined` error. Users cannot share a result URL or return to their output after any navigation event.

### Steps to Reproduce

1. Fill the form and submit a prompt
2. Wait for the result page to load with full blog + social content
3. Press `F5` / `Cmd+R` to reload the page
4. **Result:** blank page or runtime error

### Fix

Persist the result to `sessionStorage` on arrival and restore it on mount:

```jsx
// Result.jsx
import { useEffect, useState } from "react"
import { useLocation } from "react-router-dom"

const STORAGE_KEY = "neo_scripting_last_result"

export default function Result() {
  const { state } = useLocation()
  const [result, setResult] = useState(null)

  useEffect(() => {
    if (state) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
      setResult(state)
    } else {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) setResult(JSON.parse(saved))
    }
  }, [state])

  if (!result) return <p>No result found. <a href="/">Generate one</a></p>
  // ... render blog_markdown and social_posts
}
```

---

## Problem 2 — No Request Timeout or Cancel on `POST /generate`

**File:** `frontend/src/pages/Home.jsx`

### Description

The `fetch` call to `POST /generate` has no `AbortController` and no timeout. If the backend hangs (Vercel cold timeout, Gemini rate limit, Qdrant outage), the loading spinner runs indefinitely with no way to cancel. Users are forced to close the browser tab. There is also no error state shown if the request ultimately fails silently.

### Fix

Add an `AbortController` with a 120-second timeout and a visible Cancel button:

```jsx
// Home.jsx
const [controller, setController] = useState(null)

const handleSubmit = async () => {
  const ac = new AbortController()
  setController(ac)
  const timeoutId = setTimeout(() => ac.abort(), 120_000)

  try {
    const res = await fetch(`${API_BASE}/generate`, {
      method: "POST",
      body: JSON.stringify(formData),
      headers: { "Content-Type": "application/json" },
      signal: ac.signal,
    })
    clearTimeout(timeoutId)
    // handle response...
  } catch (err) {
    if (err.name === "AbortError") {
      setError("Request timed out or was cancelled.")
    }
  } finally {
    setController(null)
  }
}

// In JSX while loading:
// {controller && <button onClick={() => controller.abort()}>Cancel</button>}
```

---

## Problem 3 — `StepTracker` Not Wired to Real Pipeline Events; Shows False Progress

**File:** `frontend/src/components/StepTracker.jsx`

### Description

The `StepTracker` component advances through pipeline steps (Researcher, Planner, Writer, Optimizer, etc.) on a **fixed timer**, not on real server-sent events. This means it can show "Writer complete" while the Researcher is still running. If the pipeline takes longer than the timer, all steps show green while the spinner is still active — eroding user trust.

### Option A — Remove fake progress (quick fix)

Replace `StepTracker` with a simple indeterminate spinner and elapsed time counter. Honest and zero-risk:

```jsx
// Replace StepTracker with:
<div>
  <Spinner />
  <p>Generating your content... ({elapsed}s)</p>
</div>
```

### Option B — Wire to real SSE events (proper fix, dependent on Backend Problem 1)

Once the backend emits streaming progress events, consume them in the frontend:

```python
# main.py — emit progress events per agent
yield f'data: {{"event": "agent_done", "agent": "researcher"}}\n\n'
yield f'data: {{"event": "agent_done", "agent": "planner"}}\n\n'
yield f'data: {{"event": "complete", "result": {json.dumps(result)}}}\n\n'
```

```jsx
// StepTracker.jsx — consume real events
useEffect(() => {
  const es = new EventSource(`${API_BASE}/generate/stream`)
  es.onmessage = (e) => {
    const { event, agent } = JSON.parse(e.data)
    if (event === "agent_done") setCompletedAgents(prev => [...prev, agent])
    if (event === "complete") { setResult(e.data.result); es.close() }
  }
  return () => es.close()
}, [])
```

> **Recommendation:** Implement Option A immediately to stop misleading users. Option B should be implemented in conjunction with the Backend streaming fix.

---

## Acceptance Criteria

- [ ] Pressing `F5` on `/result` restores the last generated blog and social posts
- [ ] A visible Cancel button appears during generation; clicking it aborts the request cleanly
- [ ] After 120 seconds with no response, the UI shows an error message rather than spinning forever
- [ ] `StepTracker` shows either a neutral indeterminate state OR advances only on verified server events
