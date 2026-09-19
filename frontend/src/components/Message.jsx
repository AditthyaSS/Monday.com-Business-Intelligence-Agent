import React, { useState } from 'react'
import { SafeText } from './SafeText.jsx'
import {
  SkylarkChatbotIcon,
  GearIcon,
  ShieldIcon,
  WarningIcon,
  BriefingIcon,
  CopyIcon,
  CheckIcon,
} from './Icons.jsx'
import { PersonaAvatar, getPersona } from './ExecutivePersonas.jsx'

function TracePanel({ trace }) {
  if (!trace || trace.length === 0) return null

  return (
    <details className="trace-panel">
      <summary>
        <span className="trace-icon"><BriefingIcon size={14} /></span>
        <span className="trace-label">
          Reasoning & Data Trace ({trace.length} tool {trace.length > 1 ? 'calls' : 'call'})
        </span>
        <span className="trace-badge">EXPLAINABILITY AUDIT</span>
      </summary>
      <div className="trace-body">
        {trace.map((t, i) => (
          <div key={i} className="trace-item">
            <div className="trace-tool-header">
              <span className="trace-tool-badge">
                <GearIcon size={12} /> {t.tool}
              </span>
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
                  <ShieldIcon size={13} /> Data Coverage
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
              <div className="trace-section caveats">
                <div className="trace-section-title">
                  <WarningIcon size={13} /> Data Caveats & Anomalies
                </div>
                <ul>
                  {t.caveats.map((c, ci) => (
                    <li key={ci}>{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {t.assumptions && t.assumptions.length > 0 && (
              <div className="trace-section">
                <div className="trace-section-title">Assumptions Applied</div>
                <ul>
                  {t.assumptions.map((a, ai) => (
                    <li key={ai}>{a}</li>
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
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      /* ignore clipboard fail */
    }
  }

  return (
    <button
      className={`btn-action ${copied ? 'copied' : ''}`}
      onClick={handleCopy}
      title="Copy message to clipboard"
    >
      <span className="btn-action-icon">{copied ? <CheckIcon size={13} /> : <CopyIcon size={13} />}</span>
      <span>{copied ? 'Copied' : 'Copy'}</span>
    </button>
  )
}

export function AssistantMessage({ msg, onRetry }) {
  const formattedTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div className="message assistant">
      <div className="message-avatar-col">
        <div className="skylark-avatar-badge">
          <SkylarkChatbotIcon size={26} />
        </div>
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
              <span className="engine-bolt-icon">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
              </span>
              <span>Deterministic Mode • Pure Pandas Engine • Zero Hallucination</span>
            </div>
          )}

          <SafeText text={msg.content} />
        </div>

        <div className="msg-actions">
          <CopyButton text={msg.content} />
          {msg.model && (
            <span className="model-pill">
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

export function UserMessage({ msg, personaId }) {
  const formattedTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const persona = getPersona(personaId)

  return (
    <div className="message user">
      <div className="message-content-col">
        <div className="message-header-line user-header">
          <span className="sender-name">{persona.name}</span>
          <span className="sender-role-tag">{persona.role}</span>
          <span className="message-time">{formattedTime}</span>
        </div>
        <div className="bubble">{msg.content}</div>
      </div>

      <div className="message-avatar-col">
        <div className="founder-avatar-badge" title={`${persona.name} (${persona.role})`}>
          <PersonaAvatar id={persona.id} size={28} />
        </div>
      </div>
    </div>
  )
}
