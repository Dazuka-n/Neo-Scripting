import { useEffect, useState } from 'react'

const STEPS = [
  'Structuring topic',
  'Researching knowledge base',
  'Building outline',
  'Writing article',
  'Optimizing for AEO',
  'Final QA pass',
]

const STEP_INTERVAL_MS = 4000

export default function StepTracker({ active }) {
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    if (!active) {
      setCurrentStep(0)
      return
    }

    setCurrentStep(0)
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < STEPS.length - 1) return prev + 1
        clearInterval(interval)
        return prev
      })
    }, STEP_INTERVAL_MS)

    return () => clearInterval(interval)
  }, [active])

  if (!active) return null

  return (
    <div className="mt-5 space-y-1.5">
      {STEPS.map((step, i) => {
        const done = i < currentStep
        const inProgress = i === currentStep

        return (
          <div
            key={step}
            className={[
              'flex items-center gap-3 text-sm px-3 py-2 rounded-lg transition-all duration-300',
              done
                ? 'text-emerald-400'
                : inProgress
                ? 'text-violet-300 border-l-2 border-violet-500 bg-violet-500/5 pl-2.5'
                : 'text-white/30',
            ].join(' ')}
          >
            {/* Icon */}
            <span className="w-4 h-4 flex-shrink-0 flex items-center justify-center">
              {done ? (
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path
                    d="M2.5 7L5.5 10L11.5 4"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : inProgress ? (
                <span
                  className="block w-2 h-2 rounded-full bg-violet-400"
                  style={{
                    boxShadow: '0 0 6px rgba(167,139,250,0.8)',
                    animation: 'stepPulse 1.2s ease-in-out infinite',
                  }}
                />
              ) : (
                <span className="block w-1.5 h-1.5 rounded-full bg-white/15" />
              )}
            </span>

            {/* Label */}
            <span className={inProgress ? 'font-medium' : ''}>
              {inProgress ? (
                <>
                  {step}
                  <span
                    style={{ animation: 'ellipsis 1.5s steps(4, end) infinite' }}
                    className="inline-block w-4 overflow-hidden align-bottom"
                  >
                    ...
                  </span>
                </>
              ) : (
                step
              )}
            </span>
          </div>
        )
      })}

      <style>{`
        @keyframes stepPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.35; transform: scale(0.75); }
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
