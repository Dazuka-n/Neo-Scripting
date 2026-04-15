import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

function highlight(code) {
  if (code.trim().startsWith('{')) {
    return code
      .replace(/("(?:[^"\\]|\\.)*")(\s*:)/g, '<span class="json-key">$1</span>$2')
      .replace(/:\s*("(?:[^"\\]|\\.)*")/g, ': <span class="json-str">$1</span>')
      .replace(/:\s*(true|false|null)/g, ': <span class="json-kw">$1</span>')
      .replace(/:\s*(\d+)/g, ': <span class="json-num">$1</span>')
  }
  return code
    .replace(/^(claude)\s/gm, '<span class="sh-cmd">$1</span> ')
    .replace(/(--\w[\w-]*)/g, '<span class="sh-flag">$1</span>')
    .replace(/(https?:\/\/[^\s]+)/g, '<span class="sh-url">$1</span>')
}

export default function CodeBlock({ code, language = 'json' }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  const html = highlight(code)

  return (
    <div className="relative rounded-xl overflow-hidden border border-white/[0.08] group">
      {/* Top bar */}
      <div className="flex items-center px-4 py-2 bg-black/40 border-b border-white/[0.06]">
        <span className="label-caps flex-1">{language}</span>
      </div>

      {/* Code */}
      <pre className="overflow-x-auto p-4 text-[13px] leading-relaxed font-mono bg-black/30">
        <code
          className="text-white/55"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      </pre>

      {/* Absolute copy button — top right, overlays the code */}
      <button
        onClick={handleCopy}
        className={[
          'absolute top-2 right-3 flex items-center gap-1.5 text-xs px-2 py-1 rounded-md',
          'border transition-all duration-200',
          copied
            ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
            : 'border-white/10 bg-black/30 text-white/40 hover:text-white/80 hover:border-white/25',
        ].join(' ')}
        aria-label="Copy code"
      >
        {copied ? (
          <>
            <Check size={12} />
            Copied
          </>
        ) : (
          <>
            <Copy size={12} />
            Copy
          </>
        )}
      </button>

      <style>{`
        .json-key  { color: #a78bfa; }
        .json-str  { color: #6ee7b7; }
        .json-kw   { color: #f87171; }
        .json-num  { color: #fb923c; }
        .sh-cmd    { color: #a78bfa; }
        .sh-flag   { color: #67e8f9; }
        .sh-url    { color: #6ee7b7; }
      `}</style>
    </div>
  )
}
