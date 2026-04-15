import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import StepTracker from './StepTracker'

const PLATFORMS = ['LinkedIn', 'Twitter', 'Reddit']
const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function GeneratorForm() {
  const navigate = useNavigate()

  const [topic, setTopic] = useState('')
  const [brandName, setBrandName] = useState('')
  const [companyUrl, setCompanyUrl] = useState('')
  const [selectedPlatforms, setSelectedPlatforms] = useState(['LinkedIn'])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [controller, setController] = useState(null)

  const togglePlatform = (platform) => {
    setSelectedPlatforms((prev) =>
      prev.includes(platform)
        ? prev.length > 1
          ? prev.filter((p) => p !== platform)
          : prev
        : [...prev, platform]
    )
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    sessionStorage.removeItem('neo_scripting_last_result')

    const ac = new AbortController()
    setController(ac)
    const timeoutId = setTimeout(() => ac.abort(), 120_000)

    try {
      const response = await fetch(`${API_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: topic,
          brand_name: brandName,
          company_url: companyUrl,
          platforms: selectedPlatforms.map((p) => p.toLowerCase()),
        }),
        signal: ac.signal,
      })

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`)
      }

      const data = await response.json()
      localStorage.setItem('neo_scripting_result', JSON.stringify(data))
      sessionStorage.setItem('neo_scripting_last_result', JSON.stringify(data))
      navigate('/result', { state: data })
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request was cancelled or timed out. Please try again.')
      } else {
        setError('Generation failed. Check your inputs or try again.')
      }
    } finally {
      clearTimeout(timeoutId)
      setController(null)
      setLoading(false)
    }
  }

  const inputClass = [
    'w-full bg-white/5 border border-white/15 rounded-lg px-3.5 py-2.5',
    'text-white text-sm placeholder-white/25',
    'focus:outline-none focus:border-violet-500/60 focus:ring-2 focus:ring-violet-500/20',
    'transition-all duration-200',
    'disabled:opacity-50',
  ].join(' ')

  return (
    <section className="max-w-2xl mx-auto px-4 sm:px-6 py-12">
      <p className="label-caps mb-4 text-center">Generate an Article</p>

      {/* Accent gradient top line */}
      <div className="h-px bg-gradient-to-r from-transparent via-violet-500/60 to-transparent mb-0 rounded-full" />

      <div className="glass rounded-2xl rounded-tl-none rounded-tr-none border-t-0 p-6 sm:p-8"
        style={{
          borderTop: 'none',
          background: 'rgba(15, 15, 22, 0.75)',
        }}
      >
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Topic */}
          <div>
            <label className="block text-sm font-medium text-white/60 mb-1.5">
              Topic / Content Brief
            </label>
            <textarea
              rows={3}
              required
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. How AI is transforming logistics operations in 2025"
              className={`${inputClass} resize-none`}
              disabled={loading}
            />
          </div>

          {/* Brand Name */}
          <div>
            <label className="block text-sm font-medium text-white/60 mb-1.5">
              Brand Name
            </label>
            <input
              type="text"
              required
              value={brandName}
              onChange={(e) => setBrandName(e.target.value)}
              placeholder="e.g. Acme Corp"
              className={inputClass}
              disabled={loading}
            />
          </div>

          {/* Company URL */}
          <div>
            <label className="block text-sm font-medium text-white/60 mb-1.5">
              Company URL
            </label>
            <input
              type="url"
              required
              value={companyUrl}
              onChange={(e) => setCompanyUrl(e.target.value)}
              placeholder="e.g. https://example.com"
              className={inputClass}
              disabled={loading}
            />
          </div>

          {/* Platforms */}
          <div>
            <label className="block text-sm font-medium text-white/60 mb-2.5">
              Generate social posts for
            </label>
            <div className="flex gap-2.5 flex-wrap">
              {PLATFORMS.map((platform) => {
                const active = selectedPlatforms.includes(platform)
                return (
                  <button
                    key={platform}
                    type="button"
                    onClick={() => togglePlatform(platform)}
                    disabled={loading}
                    className={[
                      'px-5 py-2.5 min-w-[100px] rounded-full text-sm font-medium border',
                      'text-center transition-all duration-200 disabled:opacity-40',
                      active
                        ? 'bg-violet-600 border-violet-500 text-white shadow-[0_0_16px_rgba(124,58,237,0.4)]'
                        : 'bg-transparent border-white/20 text-white/50 hover:border-white/40 hover:text-white/80',
                    ].join(' ')}
                  >
                    {platform}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Submit */}
          <div className="pt-2">
            <p className="text-xs text-white/30 text-center mt-2 mb-3">
              ⏱ First generation may take 30–60s while the server wakes up.
            </p>
            <button
              type="submit"
              disabled={loading || !topic || !brandName || !companyUrl}
              className={[
                'w-full py-4 rounded-xl text-base font-semibold tracking-wide',
                'flex items-center justify-center gap-2.5 transition-all duration-200',
                loading
                  ? 'bg-violet-700/60 text-white/60 cursor-not-allowed'
                  : [
                      'bg-violet-600 text-white',
                      'hover:bg-violet-500',
                      'hover:shadow-[0_0_24px_rgba(124,58,237,0.5)]',
                      'active:scale-[0.99]',
                    ].join(' '),
                'disabled:opacity-40 disabled:cursor-not-allowed',
              ].join(' ')}
            >
              {loading ? (
                <>
                  <Loader2 size={17} className="animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate Article →'
              )}
            </button>

            <StepTracker active={loading} />

            {loading && controller && (
              <button
                onClick={() => controller.abort()}
                type="button"
                className="mt-3 w-full py-3 rounded-xl text-sm font-medium border border-white/20 text-white/50 hover:text-white hover:border-red-500/50 hover:bg-red-500/10 transition-all duration-200"
              >
                Cancel
              </button>
            )}
          </div>

          {/* Error */}
          {error && (
            <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/25 text-red-400 text-sm">
              {error}
            </div>
          )}
        </form>
      </div>
    </section>
  )
}
