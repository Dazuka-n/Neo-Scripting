export default function Footer() {
  return (
    <>
      {/* Gradient separator */}
      <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      <footer className="py-6 px-4 sm:px-6">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-sm text-white/30">
            Intelliwrite by Teeny Tech Trek
          </span>

          <div className="flex items-center gap-2 text-sm text-white/20">
            <span>Built with</span>
            {['Agno', 'Gemini', 'Qdrant'].map((tech) => (
              <span
                key={tech}
                className="px-2 py-0.5 rounded text-xs border border-white/10 text-white/30"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      </footer>
    </>
  )
}
