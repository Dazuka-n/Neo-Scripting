import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Copy, Check } from 'lucide-react'
import MarkdownViewer from '../components/MarkdownViewer'
import SocialPostCard from '../components/SocialPostCard'

export default function Result() {
  const navigate = useNavigate()
  const [result, setResult] = useState(null)
  const [mdCopied, setMdCopied] = useState(false)

  useEffect(() => {
    const raw = localStorage.getItem('intelliwrite_result')
    if (!raw) {
      navigate('/')
      return
    }
    try {
      setResult(JSON.parse(raw))
    } catch {
      navigate('/')
    }
  }, [navigate])

  const handleCopyMarkdown = async () => {
    if (!result?.blog_markdown) return
    try {
      await navigator.clipboard.writeText(result.blog_markdown)
      setMdCopied(true)
      setTimeout(() => setMdCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  const handleGenerateAnother = () => {
    localStorage.removeItem('intelliwrite_result')
    navigate('/')
  }

  if (!result) return null

  const socialPosts = result.social_posts || {}
  const platformOrder = ['linkedin', 'twitter', 'reddit']
  const availablePlatforms = platformOrder.filter(
    (p) => socialPosts[p] && socialPosts[p].trim()
  )

  return (
    <div className="min-h-screen bg-bg-base">
      {/* Minimal top bar */}
      <header className="sticky top-0 z-40 bg-bg-base/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-13 flex items-center justify-between py-3">
          <div className="flex items-center gap-2">
            <span className="text-base font-bold tracking-tight">
              <span className="text-white">Intelli</span>
              <span className="text-gradient-accent">write</span>
            </span>
            <span className="hidden sm:block text-text-muted text-sm mx-2">·</span>
            <span className="hidden sm:block text-sm text-text-secondary">Result</span>
          </div>
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-white transition-colors duration-200 px-2 py-1 rounded-lg hover:bg-white/5"
          >
            <ArrowLeft size={15} />
            Back
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* LEFT — Blog Article */}
          <div className="lg:w-[60%] min-w-0">
            {/* Article header */}
            <div className="flex items-center justify-between mb-4">
              <p className="label-caps">Generated Article</p>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyMarkdown}
                  className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-white transition-colors duration-200 px-2.5 py-1.5 rounded-lg border border-border hover:border-white/20 hover:bg-white/5"
                >
                  {mdCopied ? (
                    <>
                      <Check size={13} className="text-emerald-400" />
                      <span className="text-emerald-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={13} />
                      Copy Markdown
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Article content */}
            <div className="glass rounded-2xl p-5 sm:p-7 overflow-y-auto max-h-[calc(100vh-180px)]">
              <MarkdownViewer content={result.blog_markdown || ''} />
            </div>
          </div>

          {/* RIGHT — Social Posts */}
          <div className="lg:w-[40%] min-w-0">
            <p className="label-caps mb-4">Social Posts</p>

            <div className="space-y-3">
              {availablePlatforms.length > 0 ? (
                availablePlatforms.map((platform) => (
                  <SocialPostCard
                    key={platform}
                    platform={platform}
                    content={socialPosts[platform]}
                  />
                ))
              ) : (
                <p className="text-text-muted text-sm">No social posts returned.</p>
              )}
            </div>

            {/* Generate another */}
            <button
              onClick={handleGenerateAnother}
              className="mt-6 w-full py-3 rounded-xl text-sm font-medium border border-border text-text-secondary hover:text-white hover:border-white/20 hover:bg-white/5 transition-all duration-200"
            >
              Generate Another →
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
