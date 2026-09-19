import React, { useState } from 'react'
import { SafeText } from './SafeText.jsx'

function TracePanel({ trace }) {
  if (!trace || trace.length === 0) return null
  return (
    <details className="trace-panel">
      <summary>🔍 How I got this ({trace.length} tool{trace.length > 1 ? 's' : ''})</summary>
      <div className="trace-body">
        {trace.map((t, i) => (
          <div key={i} className="trace-item">
            <div className="trace-tool">🛠 {t.tool}</div>
            {t.params && Object.keys(t.params).length > 0 && (
              <div className="trace-params">
                Params: {Object.entries(t.params).map(([k, v]) => (
                  <span key={k}>{k}: {String(v)}</span>
                ))}
              </div>
            )}
            {t.coverage && t.coverage.length > 0 && (
              <div className="trace-section">
                <span className="trace-section-label">Coverage: </span>
                <ul>
                  {t.coverage.map((c, ci) => (
                    <li key={ci}>{c.metric}: {c.used}/{c.total} — {c.note}</li>
                  ))}
                </ul>
              </div>
            )}
            {t.caveats && t.caveats.length > 0 && (
              <div className="trace-section">
                <span className="trace-section-label">Caveats: </span>
                <ul>{t.caveats.map((c, ci) => <li key={ci}>{c}</li>)}</ul>
              </div>
            )}
            {t.assumptions && t.assumptions.length > 0 && (
              <div className="trace-section">
                <span className="trace-section-label">Assumptions: </span>
                <ul>{t.assumptions.map((a, ai) => <li key={ai}>{a}</li>)}</ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </details>
  )
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(text)
      } else {
        // Fallback
        const ta = document.createElement('textarea')
        ta.value = text
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      }
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch (e) { /* silently fail */ }
  }
  return (
    <button className="btn-copy" onClick={handleCopy} aria-label="Copy answer">
      {copied ? '✓ Copied' : '📋 Copy'}
    </button>
  )
}

export function AssistantMessage({ msg }) {
  return (
    <div className="message assistant">
      <div className="bubble">
        {msg.degraded && <span className="degraded-badge">Computed results (no AI narration)</span>}
        <SafeText text={msg.content} />
      </div>
      <div className="msg-actions">
        <CopyButton text={msg.content} />
        {msg.model && <span style={{fontSize:'0.72rem',color:'var(--color-text-muted)'}}>Model: {msg.model}</span>}
      </div>
      <TracePanel trace={msg.trace} />
    </div>
  )
}

export function UserMessage({ msg }) {
  return (
    <div className="message user">
      <div className="bubble">{msg.content}</div>
    </div>
  )
}
