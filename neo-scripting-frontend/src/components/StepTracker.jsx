import { useEffect, useState } from 'react'

// TODO: Phase 2 — uncomment and wire to real SSE events from POST /generate/stream
// const STEPS = [
//   { key: 'topic_generator', label: 'Structuring topic' },
//   { key: 'researcher', label: 'Researching knowledge base' },
//   { key: 'planner', label: 'Building outline' },
//   { key: 'writer', label: 'Writing article' },
//   { key: 'optimizer', label: 'Optimizing for AEO' },
//   { key: 'final_editor', label: 'Final QA pass' },
//   { key: 'social_researcher', label: 'Researching social content' },
//   { key: 'social_writer', label: 'Writing social posts' },
//   { key: 'social_qa', label: 'Social QA check' },
// ]

export default function StepTracker({ active }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!active) {
      setElapsed(0)
      return
    }

    setElapsed(0)
    const id = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [active])

  if (!active) return null

  return (
    <div className="mt-5 flex flex-col items-center gap-3">
      {/* Spinner */}
      <div
        className="w-5 h-5 rounded-full border-2 border-violet-400 border-t-transparent"
        style={{ animation: 'spin 0.8s linear infinite' }}
      />

      {/* Status text */}
      <p className="text-sm text-violet-300 font-medium">
        Generating your content
        <span
          style={{ animation: 'ellipsis 1.5s steps(4, end) infinite' }}
          className="inline-block w-4 overflow-hidden align-bottom"
        >
          ...
        </span>
        <span className="text-white/40 ml-1">({elapsed}s)</span>
      </p>

      {/* Helpful subtext */}
      <p className="text-xs text-white/30">
        This takes 1–3 minutes. Please keep this tab open.
      </p>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes ellipsis {
          0%  { width: 0; }
          25% { width: 0.4em; }
          50% { width: 0.8em; }
          75% { width: 1.2em; }
          100% { width: 0; }
        }
      `}</style>
    </div>
  )
}
