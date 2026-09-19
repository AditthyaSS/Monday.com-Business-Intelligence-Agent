import React, { useState, useEffect } from 'react'

const LOADING_STEPS = [
  { icon: '📡', text: 'Reading live Monday.com boards…' },
  { icon: '🧼', text: 'Normalising records & auditing data invariants…' },
  { icon: '⚙️', text: 'Executing deterministic analytics tools…' },
  { icon: '💡', text: 'Synthesizing executive insights…' },
]

export function LoadingMessage({ startTime }) {
  const [stepIdx, setStepIdx] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [showSlow, setShowSlow] = useState(false)

  useEffect(() => {
    const stepInterval = setInterval(() => {
      setStepIdx(i => (i + 1) % LOADING_STEPS.length)
    }, 2200)

    const timer = setInterval(() => {
      setElapsed(((Date.now() - startTime) / 1000).toFixed(1))
    }, 200)

    const slowTimer = setTimeout(() => setShowSlow(true), 9000)

    return () => {
      clearInterval(stepInterval)
      clearInterval(timer)
      clearTimeout(slowTimer)
    }
  }, [startTime])

  const step = LOADING_STEPS[stepIdx]

  return (
    <div className="loading-msg" role="status" aria-live="polite">
      <div className="loading-bubble">
        <div className="dots">
          <div className="dot" />
          <div className="dot" />
          <div className="dot" />
        </div>

        <div className="loading-content">
          <div className="loading-text">
            <span style={{ marginRight: 6 }}>{step.icon}</span>
            <span>{step.text}</span>
            <span
              style={{
                marginLeft: 8,
                fontFamily: 'var(--font-mono)',
                fontSize: '0.74rem',
                color: 'var(--accent-cyan)',
                opacity: 0.85,
              }}
            >
              [{elapsed}s]
            </span>
          </div>

          {showSlow && (
            <div className="loading-subtext">
              Cold start in progress on serverless runtime — this typically completes within 30–45s.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
