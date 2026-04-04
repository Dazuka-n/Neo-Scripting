import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const components = {
  h1: ({ children }) => (
    <h1 className="text-2xl font-bold text-white mt-8 mb-4 tracking-tight leading-tight">
      {children}
    </h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-xl font-bold text-white mt-7 mb-3 tracking-tight leading-tight pl-3 border-l-2 border-accent">
      {children}
    </h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-semibold text-white mt-5 mb-2 pl-3 border-l border-accent/60">
      {children}
    </h3>
  ),
  p: ({ children }) => (
    <p className="text-[#d4d4d8] text-sm leading-[1.85] mb-4">{children}</p>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-accent-light no-underline hover:underline transition-all duration-200"
    >
      {children}
    </a>
  ),
  ul: ({ children }) => (
    <ul className="mb-4 space-y-1 pl-1">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-4 space-y-1 pl-1 list-decimal list-inside">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="text-[#d4d4d8] text-sm leading-[1.8] flex gap-2">
      <span className="mt-[0.45rem] w-1.5 h-1.5 rounded-full bg-accent flex-shrink-0" />
      <span>{children}</span>
    </li>
  ),
  blockquote: ({ children }) => (
    <blockquote className="pl-4 border-l-2 border-accent/50 italic text-text-secondary text-sm my-4">
      {children}
    </blockquote>
  ),
  code: ({ inline, children, ...props }) => {
    if (inline) {
      return (
        <code
          className="px-1.5 py-0.5 rounded text-[13px] font-mono"
          style={{
            background: 'rgba(124,58,237,0.15)',
            color: '#a78bfa',
          }}
          {...props}
        >
          {children}
        </code>
      )
    }
    return (
      <div className="my-4 rounded-xl overflow-hidden border border-border">
        <div className="px-4 py-1.5 bg-bg-base border-b border-border">
          <span className="label-caps">markdown</span>
        </div>
        <pre className="overflow-x-auto p-4 bg-bg-base/80">
          <code className="text-[13px] font-mono text-text-secondary leading-relaxed" {...props}>
            {children}
          </code>
        </pre>
      </div>
    )
  },
  hr: () => <hr className="border-border my-6" />,
  strong: ({ children }) => (
    <strong className="font-semibold text-white">{children}</strong>
  ),
  em: ({ children }) => (
    <em className="italic text-text-secondary">{children}</em>
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-4">
      <table className="w-full text-sm border-collapse">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="px-3 py-2 text-left text-xs font-semibold text-text-secondary uppercase tracking-wide border border-border bg-bg-surface">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-2 text-[#d4d4d8] border border-border text-sm">
      {children}
    </td>
  ),
}

export default function MarkdownViewer({ content }) {
  return (
    <div className="prose-custom">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  )
}
