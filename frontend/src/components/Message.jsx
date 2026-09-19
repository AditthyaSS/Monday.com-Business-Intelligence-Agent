import React, { useState } from 'react'
import { SafeText } from './SafeText.jsx'

function TracePanel({ trace }) {
  if (!trace || trace.length === 0) return null

  return (
    <details className="trace-panel">
      <summary>
        <span>🔍</span>
        <span>Reasoning & Data Trace ({trace.length} tool {trace.length > 1 ? 'calls' : 'call'})</span>
        <span style={{ marginLeft: 'auto', fontSize: '0.72rem', opacity: 0.7 }}>Explainability Audit</span>
      </summary>
      <div className="trace-body">
        {trace.map((t, i) => (
          <div key={i} className="trace-item">
            <div className="trace-tool-header">
              <span className="trace-tool-badge">🛠️ {t.tool}</span>
            </div>

            {t.params && Object.keys(t.params).length > 0 && (
              <div className="trace-params">
                {Object.entries(t.params).map(([k, v]) => (
                  <span key={k} className="trace-param-pill">
                    {k}: <strong>{String(v)}</strong>
                  </span>
                ))}
              </div>
            )}

            {t.coverage && t.coverage.length > 0 && (
              <div className="trace-section">
                <div className="trace-section-title">
                  <span>🛡️</span> Data Coverage
                </div>
                <ul>
                  {t.coverage.map((c, ci) => (
                    <li key={ci}>
                      <strong>{c.metric}:</strong> {c.used}/{c.total} records accounted for
                      {c.note ? ` (${c.note})` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {t.caveats && t.caveats.length > 0 && (
              <div className="trace-section">
                <div className="trace-section-title" style={{ color: '#fde68a' }}>
                  <span>⚠️</span> Data Caveats & Exclusions
                </div>
                <ul>
                  {t.caveats.map((c, ci) => (
                    <li key={ci} style={{ color: '#fef3c7' }}>{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {t.assumptions && t.assumptions.length > 0 && (
              <div className="trace-section">
                <div className="trace-section-title" style={{ color: '#c7d2fe' }}>
                  <span>📋</span> Business Rules & Assumptions
                </div>
                <ul>
                  {t.assumptions.map((a, ai) => (
                    <li key={ai} style={{ color: '#e0e7ff' }}>{a}</li>
                  ))}
                </ul>
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
        const ta = document.createElement('textarea')
        ta.value = text
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      }
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch (e) {
      /* silently ignore clipboard errors */
    }
  }

  return (
    <button
      className="btn-action"
      onClick={handleCopy}
      aria-label="Copy answer to clipboard"
      title="Copy message to clipboard"
    >
      <span>{copied ? '✓' : '📋'}</span>
      <span>{copied ? 'Copied' : 'Copy'}</span>
    </button>
  )
}

export function AssistantMessage({ msg }) {
  return (
    <div className="message assistant">
      <div className="bubble">
        <div className="assistant-header-tag">
          <span>🚁</span>
          <span>Skylark Intelligence</span>
        </div>

        {msg.degraded && (
          <div className="degraded-badge">
            <span>⚡</span>
            <span>Deterministic Engine • AI Narration Bypassed</span>
          </div>
        )}

        <SafeText text={msg.content} />
      </div>

      <div className="msg-actions">
        <CopyButton text={msg.content} />
        {msg.model && (
          <span className="model-pill">
            model: {msg.model}
          </span>
        )}
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
