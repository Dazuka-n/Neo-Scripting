import { useState } from 'react'
import { Copy, Check } from 'lucide-react'

const PLATFORM_META = {
  linkedin: {
    label: 'LinkedIn',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" />
        <circle cx="4" cy="4" r="2" />
      </svg>
    ),
    color: 'text-[#0A66C2]',
  },
  twitter: {
    label: 'Twitter / X',
    icon: (
      <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
    color: 'text-white',
  },
  reddit: {
    label: 'Reddit',
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <circle cx="12" cy="12" r="10" fill="#FF4500" />
        <path
          d="M17.9 9.3c-.3 0-.6.1-.8.3-.9-.6-2.1-.9-3.4-.9l.6-2.7 1.9.4c0 .5.4.8.9.8.5 0 .9-.4.9-.9s-.4-.9-.9-.9c-.4 0-.7.2-.8.6l-2.1-.4c-.1 0-.2.1-.2.2l-.6 3c-1.4 0-2.6.4-3.4.9-.2-.2-.5-.3-.8-.3-.9 0-1.3.9-.8 1.6-.1.2-.1.4-.1.6 0 1.9 2.2 3.4 4.9 3.4s4.9-1.5 4.9-3.4c0-.2 0-.4-.1-.6.4-.6.1-1.5-.9-1.5z"
          fill="white"
        />
        <circle cx="10" cy="12" r=".8" fill="#FF4500" />
        <circle cx="14" cy="12" r=".8" fill="#FF4500" />
        <path
          d="M14.5 14c-.5.5-1.2.8-2.5.8s-2-.3-2.5-.8"
          stroke="#FF4500"
          strokeWidth=".6"
          fill="none"
          strokeLinecap="round"
        />
      </svg>
    ),
    color: 'text-[#FF4500]',
  },
}

export default function SocialPostCard({ platform, content }) {
  const [copied, setCopied] = useState(false)
  const meta = PLATFORM_META[platform] || { label: platform, icon: null, color: 'text-white' }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  return (
    <div className="glass rounded-xl p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className={`flex items-center gap-2 ${meta.color}`}>
          {meta.icon}
          <span className="text-sm font-semibold text-white">{meta.label}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-white transition-colors duration-200 px-2 py-1 rounded-lg hover:bg-white/5"
          aria-label={`Copy ${meta.label} post`}
        >
          {copied ? (
            <>
              <Check size={13} className="text-emerald-400" />
              <span className="text-emerald-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy size={13} />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Content */}
      <p className="text-[#d4d4d8] text-sm leading-relaxed whitespace-pre-wrap">{content}</p>

      {/* Char count */}
      <div className="flex justify-end">
        <span className="text-xs text-text-muted">{content.length} chars</span>
      </div>
    </div>
  )
}
