import React, { useState } from 'react'
import { LottiePlayer } from './LottiePlayer.jsx'
import cat404Data from '../../assets/404 error page with cat.json'
import chatbotData from '../../assets/chatbot.json'
import sleepData from '../../assets/sleep.json'

export function ErrorCard({ error, onRetry, retryCountdown, onRunDeterministic }) {
  const [showDiagnostics, setShowDiagnostics] = useState(false)
  const [healthChecking, setHealthChecking] = useState(false)
  const [healthStatus, setHealthStatus] = useState(null)

  if (!error) return null

  const rawMsg = (error.user_message || error.message || '').trim()
  const code = (error.code || '').toUpperCase()

  // Match the user's exact situational message specification
  let situation = 'UNEXPECTED_ERROR'
  let displayMessage = "🛠️ I hit a small snag while working on that. Please try again."
  let animData = cat404Data

  if (code.includes('NO_CACHE') || rawMsg.toLowerCase().includes('no previously cached')) {
    situation = 'NO_CACHED_DATA'
    displayMessage = "📭 I don't have a fresh copy to work from yet. Please try again when the data connection is back."
    animData = cat404Data
  } else if (code.includes('MONDAY_UNAVAILABLE') || (rawMsg.toLowerCase().includes('monday') && rawMsg.toLowerCase().includes('unavailable'))) {
    situation = 'MONDAY_UNAVAILABLE'
    displayMessage = "🤖 I can't reach Monday right now. The data desk seems to be taking a coffee break. I'll use the latest cached data if available."
    animData = sleepData
  } else if (code.includes('MONDAY_TIMEOUT') || (rawMsg.toLowerCase().includes('monday') && rawMsg.toLowerCase().includes('timed out'))) {
    situation = 'MONDAY_TIMEOUT'
    displayMessage = "⏳ Monday is taking a little too long to answer. I'll try again, or use the latest available data."
    animData = cat404Data
  } else if (code.includes('MONDAY_AUTH') || (rawMsg.toLowerCase().includes('monday') && (rawMsg.toLowerCase().includes('access') || rawMsg.toLowerCase().includes('securely')))) {
    situation = 'MONDAY_AUTH'
    displayMessage = "🔐 My Monday access needs a quick check. I couldn't securely access the boards."
    animData = cat404Data
  } else if (code.includes('MONDAY_RATE_LIMIT') || (rawMsg.toLowerCase().includes('monday') && rawMsg.toLowerCase().includes('rate-limit'))) {
    situation = 'MONDAY_RATE_LIMIT'
    displayMessage = "🚦 Too many requests in the data lane! Monday is asking me to slow down. Please try again shortly."
    animData = sleepData
  } else if (code.includes('MONDAY_SERVER') || (rawMsg.toLowerCase().includes('monday') && rawMsg.toLowerCase().includes('service problem'))) {
    situation = 'MONDAY_SERVER_ERROR'
    displayMessage = "🛠️ Monday is having a rough moment. The boards aren't responding right now. I'll use cached data if I have it."
    animData = cat404Data
  } else if (code.includes('GEMINI_QUOTA') || rawMsg.toLowerCase().includes('usage limit') || rawMsg.toLowerCase().includes('recharge')) {
    situation = 'GEMINI_QUOTA'
    displayMessage = "💤 My AI brain needs a short recharge. AI narration is unavailable for now, but I've still calculated the numbers for you."
    animData = sleepData
  } else if (code.includes('RATE_LIMIT') || rawMsg.toLowerCase().includes('too many requests') || rawMsg.toLowerCase().includes('quickly')) {
    situation = 'GEMINI_RATE_LIMIT'
    displayMessage = "🧠 My AI brain is at capacity. I'll skip the narration and show you the computed results instead."
    animData = sleepData
  } else if (code.includes('TIMEOUT') || rawMsg.toLowerCase().includes('timeout') || rawMsg.toLowerCase().includes('didn\'t answer in time')) {
    situation = 'GEMINI_TIMEOUT'
    displayMessage = "🛰️ My AI brain didn't answer in time. No worries, the underlying numbers are still available."
    animData = cat404Data
  } else if (code.includes('GEMINI_UNAVAILABLE') || rawMsg.toLowerCase().includes('temporarily offline')) {
    situation = 'GEMINI_UNAVAILABLE'
    displayMessage = "🔌 My AI reasoning service is temporarily offline. I'm switching to computed results so the work can continue."
    animData = sleepData
  } else if (code.includes('GEMINI_AUTH') || rawMsg.toLowerCase().includes('connection needs a little attention')) {
    situation = 'GEMINI_AUTH'
    displayMessage = "🔑 My AI connection needs a little attention. I'll keep working with the available data while the connection is fixed."
    animData = cat404Data
  } else if (code.includes('INVALID_REQUEST') || rawMsg.toLowerCase().includes('detail to get that right') || rawMsg.toLowerCase().includes('clarify')) {
    situation = 'INVALID_REQUEST'
    displayMessage = "🤔 I need one more detail to get that right. Could you clarify what you'd like me to analyze?"
    animData = chatbotData
  } else if (code.includes('NO_DATA') || rawMsg.toLowerCase().includes('no matching records')) {
    situation = 'NO_DATA_FOR_QUERY'
    displayMessage = "🔎 I couldn't find enough data for that question. There may simply be no matching records for the period you're asking about."
    animData = chatbotData
  } else if (code.includes('MESSY_DATA') || rawMsg.toLowerCase().includes('messy records')) {
    situation = 'MESSY_DATA'
    displayMessage = "🧹 I found a few messy records in the data. I've excluded records that couldn't be reliably calculated and flagged them below."
    animData = chatbotData
  } else if (code.includes('STALE_DATA') || rawMsg.toLowerCase().includes('older snapshot')) {
    situation = 'STALE_DATA'
    displayMessage = "🕐 I'm working from an older snapshot. The latest Monday data isn't available right now, so treat this answer accordingly."
    animData = chatbotData
  } else if (code.includes('NETWORK') || rawMsg.toLowerCase().includes('network') || rawMsg.toLowerCase().includes('gateway') || rawMsg.toLowerCase().includes('unable to communicate')) {
    situation = 'NETWORK_OFFLINE'
    displayMessage = "🛠️ I hit a small snag reaching the server. The data desk seems to be taking a brief moment to connect. Please try again."
    animData = cat404Data
  } else {
    situation = 'UNEXPECTED_ERROR'
    displayMessage = rawMsg || "🛠️ I hit a small snag while working on that. Please try again."
    animData = cat404Data
  }

  const handleHealthCheck = async () => {
    setHealthChecking(true)
    setHealthStatus(null)
    try {
      const res = await fetch('/api/health')
      if (res.ok) {
        setHealthStatus({ ok: true, msg: 'Backend API is responsive.' })
      } else {
        setHealthStatus({ ok: false, msg: `Gateway returned HTTP ${res.status}` })
      }
    } catch (e) {
      setHealthStatus({ ok: false, msg: 'Unable to reach backend gateway.' })
    } finally {
      setHealthChecking(false)
    }
  }

  return (
    <div className="claude-error-card" role="alert">
      <div className="claude-error-layout">
        <div className="claude-error-animation">
          <LottiePlayer animationData={animData} width={100} height={100} />
        </div>

        <div className="claude-error-body">
          <div className="claude-error-msg">
            {displayMessage}
          </div>

          <div className="claude-error-actions">
            {retryCountdown > 0 ? (
              <div className="claude-cooldown-pill">
                <span>⏱️</span>
                <span>Wait {retryCountdown}s</span>
              </div>
            ) : (
              <button className="claude-btn-retry" onClick={onRetry} id="claude-retry-btn">
                <span>⟲</span>
                <span>Retry</span>
              </button>
            )}

            {onRunDeterministic && (
              <button
                className="claude-btn-secondary"
                onClick={onRunDeterministic}
                title="Run calculations directly without AI narration"
              >
                <span>⚡</span>
                <span>Compute Directly</span>
              </button>
            )}

            <button
              className="claude-btn-ghost"
              onClick={handleHealthCheck}
              disabled={healthChecking}
              title="Ping backend health"
            >
              <span>{healthChecking ? '…' : 'Ping'}</span>
            </button>
          </div>

          {healthStatus && (
            <div className={`claude-health-tag ${healthStatus.ok ? 'ok' : 'fail'}`}>
              {healthStatus.ok ? '✓ Online' : '✕ Offline'} • {healthStatus.msg}
            </div>
          )}

          <div className="claude-diag-toggle">
            <button
              className="btn-text-link"
              onClick={() => setShowDiagnostics(!showDiagnostics)}
            >
              {showDiagnostics ? 'Hide details' : 'Show details'}
            </button>
            {showDiagnostics && (
              <div className="claude-diag-content">
                <div>Situation: <code>{situation}</code></div>
                {error.status ? <div>Status: <code>HTTP {error.status}</code></div> : null}
                {error.code ? <div>Code: <code>{error.code}</code></div> : null}
                {error.technicalDetail ? <div>Detail: <code>{error.technicalDetail}</code></div> : null}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
