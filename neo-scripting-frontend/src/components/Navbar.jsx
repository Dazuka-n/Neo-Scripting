import { useEffect, useState } from 'react'

function SparkleIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M12 2L13.5 8.5L20 10L13.5 11.5L12 18L10.5 11.5L4 10L10.5 8.5L12 2Z"
        fill="#7c3aed"
        stroke="#a78bfa"
        strokeWidth="0.5"
        strokeLinejoin="round"
      />
      <path
        d="M19 3L19.75 5.25L22 6L19.75 6.75L19 9L18.25 6.75L16 6L18.25 5.25L19 3Z"
        fill="#a78bfa"
        opacity="0.7"
      />
      <path
        d="M5 17L5.5 18.5L7 19L5.5 19.5L5 21L4.5 19.5L3 19L4.5 18.5L5 17Z"
        fill="#a78bfa"
        opacity="0.5"
      />
    </svg>
  )
}

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const handleDocsClick = (e) => {
    e.preventDefault()
    const el = document.getElementById('mcp-section')
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'backdrop-blur-xl border-b border-white/[0.08]'
          : 'bg-transparent'
      }`}
      style={scrolled ? { backgroundColor: 'rgba(10,10,15,0.82)' } : {}}
    >
      <nav className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <a href="/" className="flex items-center gap-2 group" aria-label="Neo Scripting home">
          <SparkleIcon />
          <span className="text-base font-bold tracking-tight leading-none">
            <span className="text-white">Intelli</span>
            <span className="text-gradient-accent">write</span>
          </span>
        </a>

        {/* Nav links */}
        <div className="hidden sm:flex items-center gap-1">
          <a
            href="#mcp-section"
            onClick={handleDocsClick}
            className="px-3 py-1.5 text-sm text-white/50 hover:text-white transition-colors duration-200 rounded-md hover:bg-white/5"
          >
            Docs
          </a>
          <a
            href="#"
            className="px-3 py-1.5 text-sm text-white/50 hover:text-white transition-colors duration-200 rounded-md hover:bg-white/5"
          >
            GitHub
          </a>
        </div>
      </nav>
    </header>
  )
}
