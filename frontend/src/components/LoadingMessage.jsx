import React, { useState, useEffect } from 'react'

const LOADING_TEXTS = [
  'Reading monday.com...',
  'Cleaning the data...',
  'Analysing...',
  'Thinking...',
]

export function LoadingMessage({ startTime }) {
  const [textIdx, setTextIdx] = useState(0)
  const [showSlow, setShowSlow] = useState(false)

  useEffect(() => {
    const interval = setInterval(() => {
      setTextIdx(i => (i + 1) % LOADING_TEXTS.length)
    }, 2000)
    const slowTimer = setTimeout(() => setShowSlow(true), 8000)
    return () => { clearInterval(interval); clearTimeout(slowTimer) }
  }, [])

  return (
    <div className="loading-msg">
      <div className="loading-bubble">
        <div className="dots">
          <div className="dot" />
          <div className="dot" />
          <div className="dot" />
        </div>
        <div>
          <div className="loading-text">{LOADING_TEXTS[textIdx]}</div>
          {showSlow && (
            <div className="loading-text" style={{marginTop:4,fontSize:'0.78rem'}}>
              The server may be waking up — this can take up to a minute.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
