import { useState } from 'react'
import { Check, Copy } from 'lucide-react'
import ClientTabs from './ClientTabs'

const MCP_URL = 'https://mcp.intelliwrite.ai/sse'

const EXAMPLE_PROMPTS = [
  'Generate a blog about AI in logistics for my brand Teeny Tech Trek',
  'Write LinkedIn and Twitter posts for the blog you just created',
  'Ingest this document into the Intelliwrite knowledge base',
]

export default function MCPSection() {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(MCP_URL)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  return (
    <section
      id="mcp-section"
      className="relative py-16 px-4 sm:px-6 border-t border-white/[0.08] border-b border-b-white/[0.08] overflow-hidden"
      style={{ background: 'rgba(255,255,255,0.02)' }}
    >
      {/* Subtle top-right radial glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-0 right-0 w-[500px] h-[300px]"
        style={{
          background:
            'radial-gradient(ellipse at top right, rgba(124,58,237,0.05) 0%, transparent 65%)',
        }}
      />

      <div className="relative max-w-3xl mx-auto">
        <p className="label-caps mb-4">MCP Integration</p>

        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-3">
          Connect Intelliwrite to Your Agent
        </h2>

        <p className="text-white/45 text-sm sm:text-base leading-relaxed mb-10 max-w-xl">
          Intelliwrite runs as a live MCP server. Point any compatible AI client at the URL below
          and start generating content from inside your agent workflow.
        </p>

        {/* MCP URL block */}
        <div className="mb-8">
          <p className="label-caps mb-3">Server URL</p>
          <div
            className="flex items-center gap-3 rounded-lg px-4 py-3 border border-violet-500/30"
            style={{ background: 'rgba(0,0,0,0.4)' }}
          >
            <code className="flex-1 font-mono text-sm text-violet-300 tracking-wide">
              {MCP_URL}
            </code>
            <button
              onClick={handleCopy}
              className={[
                'flex-shrink-0 flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg',
                'transition-colors duration-200',
                copied
                  ? 'text-emerald-400'
                  : 'text-violet-400 hover:text-violet-200',
              ].join(' ')}
              aria-label="Copy MCP URL"
            >
              {copied ? (
                <>
                  <Check size={14} />
                  Copied
                </>
              ) : (
                <>
                  <Copy size={14} />
                  Copy
                </>
              )}
            </button>
          </div>
        </div>

        {/* Client tabs */}
        <div className="mb-10">
          <p className="label-caps mb-4">Choose your client</p>
          <ClientTabs />
        </div>

        {/* Example prompts */}
        <div>
          <p className="label-caps mb-4">What you can say after connecting</p>
          <div className="space-y-2.5">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <div
                key={prompt}
                className="flex items-start gap-3 px-4 py-3 rounded-xl border border-white/[0.07] hover:border-violet-500/25 hover:bg-violet-500/[0.04] transition-all duration-200"
                style={{ background: 'rgba(255,255,255,0.02)' }}
              >
                <span className="mt-0.5 text-violet-500 flex-shrink-0 font-medium text-sm">→</span>
                <p className="text-sm text-white/45 italic">&ldquo;{prompt}&rdquo;</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
