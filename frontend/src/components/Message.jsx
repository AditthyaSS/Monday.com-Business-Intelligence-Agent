import React, { useState } from 'react'
import { SafeText } from './SafeText.jsx'
import { AgentAvatar, UserAvatar } from './Icons.jsx'

function TracePanel({ trace }) {
  if (!trace || trace.length === 0) return null

  return (
    <details className="trace-panel">
      <summary>
        <span className="trace-icon">🔍</span>
        <span className="trace-label">
          Reasoning & Data Trace ({trace.length} tool {trace.length > 1 ? 'calls' : 'call'})
        </span>
        <span className="trace-badge">EXPLAINABILITY AUDIT</span>
      </summary>
      <div className="trace-body">
        {trace.map((t, i) => (
          <div key={i} className="trace-item">
            <div className="trace-tool-header">
              <span className="trace-tool-badge">⚙️ {t.tool}</span>
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
                <div className="trace-section-title caveats-title">
                  <span>⚠️</span> Data Caveats & Exclusions
                </div>
                <ul>
                  {t.caveats.map((c, ci) => (
                    <li key={ci} className="caveat-item">{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {t.assumptions && t.assumptions.length > 0 && (
              <div className="trace-section">
                <div className="trace-section-title assumptions-title">
                  <span>📋</span> Business Rules & Policy
                </div>
                <ul>
                  {t.assumptions.map((a, ai) => (
                    <li key={ai} className="assumption-item">{a}</li>
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
      /* ignore clipboard errors */
    }
  }

  return (
    <button
      className="btn-action"
      onClick={handleCopy}
      aria-label="Copy answer to clipboard"
      title="Copy message to clipboard"
    >
      <span className="btn-action-icon">{copied ? '✓' : '📋'}</span>
      <span>{copied ? 'Copied' : 'Copy'}</span>
    </button>
  )
}

export function AssistantMessage({ msg, onRetry }) {
  const formattedTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div className="message assistant">
      <div className="message-avatar-col">
        <AgentAvatar size={36} />
      </div>

      <div className="message-content-col">
        <div className="message-header-line">
          <span className="sender-name">Skylark Intelligence</span>
          <span className="sender-tag">BI AGENT</span>
          <span className="message-time">{formattedTime}</span>
        </div>

        <div className="bubble">
          {msg.degraded && (
            <div className="degraded-badge">
              <span>⚡</span>
              <span>Deterministic Mode • Pure Pandas Engine • Zero Hallucination</span>
            </div>
          )}

          <SafeText text={msg.content} />
        </div>

        <div className="msg-actions">
          <CopyButton text={msg.content} />
          {msg.model && (
            <span className="model-pill">
              <span className="model-indicator" />
              {msg.model}
            </span>
          )}
          {onRetry && (
            <button className="btn-action" onClick={onRetry} title="Re-run this query">
              <span>⟲</span>
              <span>Re-run</span>
            </button>
          )}
        </div>

        <TracePanel trace={msg.trace} />
      </div>
    </div>
  )
}

export function UserMessage({ msg }) {
  const formattedTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div className="message user">
      <div className="message-content-col">
        <div className="message-header-line user-header">
          <span className="sender-name">Founder / Executive</span>
          <span className="message-time">{formattedTime}</span>
        </div>
        <div className="bubble">{msg.content}</div>
      </div>

      <div className="message-avatar-col">
        <UserAvatar size={36} />
      </div>
    </div>
  )
}
