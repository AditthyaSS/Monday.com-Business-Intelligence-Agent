import React, { useState, useEffect, useRef, useCallback } from 'react'
import { StatusStrip } from './components/StatusStrip.jsx'
import { UserMessage, AssistantMessage } from './components/Message.jsx'
import { LoadingMessage } from './components/LoadingMessage.jsx'

const MAX_CHARS = 1000
const MAX_HISTORY = 8
const ABORT_MS = 90000

const SAMPLE_QUESTIONS = [
  {
    icon: '📊',
    label: 'Pipeline Health',
    query: "How's our open pipeline looking overall?",
  },
  {
    icon: '⚡',
    label: 'Energy Sector Q3/Q4',
    query: "How's our pipeline looking for the energy sector this quarter?",
  },
  {
    icon: '🎯',
    label: 'Win Rate Analysis',
    query: "What's our win rate by sector?",
  },
  {
    icon: '💰',
    label: 'Billing vs Collections',
    query: "How much have we billed versus collected on mining work orders?",
  },
  {
    icon: '🌐',
    label: 'Cross-Board Overview',
    query: "Give me a sector overview across deals and work orders",
  },
  {
    icon: '📋',
    label: 'Executive Briefing',
    query: "Prepare a leadership update",
  },
]

export default function App() {
  const [messages, setMessages] = useState([]) // {role, content, trace?, degraded?, model?}
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingStart, setLoadingStart] = useState(0)
  const [error, setError] = useState(null) // {message, retryAfter?}
  const [status, setStatus] = useState(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [statusError, setStatusError] = useState(null)

  const chatBottomRef = useRef(null)
  const textareaRef = useRef(null)
  const abortRef = useRef(null)
  const retryTimerRef = useRef(null)
  const [retryCountdown, setRetryCountdown] = useState(0)

  // Load data status on mount
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/data-status')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setStatus(data)
      setStatusLoading(false)
      setStatusError(null)
    } catch (e) {
      setStatusError(e.message)
      setStatusLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  // Auto-scroll on new messages
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
    }
  }, [input])

  const sendMessage = useCallback(
    async (text) => {
      const cleanText = text.trim()
      if (!cleanText || loading) return
      setError(null)

      const userMsg = { role: 'user', content: cleanText }
      setMessages((prev) => [...prev, userMsg])
      setInput('')
      if (textareaRef.current) {
        textareaRef.current.style.height = '44px'
      }

      setLoading(true)
      setLoadingStart(Date.now())

      // Build history (last MAX_HISTORY messages)
      const allMessages = [...messages, userMsg].slice(-MAX_HISTORY)
      const payload = {
        messages: allMessages.map((m) => ({ role: m.role, content: m.content })),
      }

      const controller = new AbortController()
      abortRef.current = controller

      const abortTimer = setTimeout(() => {
        controller.abort()
        setLoading(false)
        setError({
          message: '⚠️ The request timed out after 90 seconds. Please try again.',
        })
      }, ABORT_MS)

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: controller.signal,
        })

        clearTimeout(abortTimer)
        const data = await res.json()

        if (!res.ok) {
          const errMsg =
            data?.error?.user_message || data?.error?.message || `Server error (${res.status})`
          const retryAfter =
            data?.error?.retry_after_seconds ?? data?.retry_after_seconds ?? null
          setError({ message: errMsg, retryAfter })

          if (retryAfter && retryAfter > 0) {
            setRetryCountdown(retryAfter)
            clearInterval(retryTimerRef.current)
            retryTimerRef.current = setInterval(() => {
              setRetryCountdown((c) => {
                if (c <= 1) {
                  clearInterval(retryTimerRef.current)
                  return 0
                }
                return c - 1
              })
            }, 1000)
          }
        } else {
          const assistantMsg = {
            role: 'assistant',
            content: data.answer,
            trace: data.trace,
            degraded: data.degraded,
            model: data.model_used,
          }
          setMessages((prev) => [...prev, assistantMsg])
          // Refresh status silently in background
          fetchStatus()
        }
      } catch (e) {
        clearTimeout(abortTimer)
        if (e.name !== 'AbortError') {
          setError({
            message: '⚠️ Network connection issue. Unable to communicate with the server.',
          })
        }
      } finally {
        setLoading(false)
      }
    },
    [messages, loading, fetchStatus]
  )

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (input.trim() && input.length <= MAX_CHARS) {
        sendMessage(input)
      }
    }
  }

  const handleRetry = () => {
    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
    if (lastUser) sendMessage(lastUser.content)
  }

  const handleClearSession = () => {
    if (loading) return
    setMessages([])
    setError(null)
    setInput('')
  }

  const isEmpty = messages.length === 0 && !loading

  return (
    <div className="app">
      {/* Executive Header */}
      <header className="header">
        <div className="header-brand">
          <div className="header-icon-wrapper">
            <span className="header-icon">🚁</span>
          </div>
          <div className="header-title-wrap">
            <div className="header-title">
              Skylark Intelligence
              <span className="header-badge">LIVE BOARDS</span>
            </div>
            <div className="header-subtitle">
              Conversational Business Intelligence over Monday.com Deals & Work Orders
            </div>
          </div>
        </div>

        <div className="header-actions">
          {messages.length > 0 && (
            <button
              className="btn-header"
              onClick={handleClearSession}
              disabled={loading}
              title="Start a new conversation"
              aria-label="New Session"
            >
              <span>↺</span>
              <span>New Session</span>
            </button>
          )}
        </div>
      </header>

      {/* Telemetry & Quality Strip */}
      <StatusStrip status={status} loading={statusLoading} error={statusError} />

      {/* Main Conversation Stream */}
      <main
        className="chat-area"
        id="chat-area"
        aria-label="Chat messages"
        aria-live="polite"
      >
        {isEmpty ? (
          <div className="empty-state">
            <div className="hero-glow-card">
              <div className="hero-icon-badge">📈</div>
              <h2 className="hero-title">Executive Decision Intelligence</h2>
              <p className="hero-description">
                Ask questions across live deal pipelines, work order billings, sector margins, and
                cash collections — backed by deterministic calculations and clear data-quality caveats.
              </p>
            </div>

            <div className="chips-container">
              <div className="chips-label">Suggested Founder Questions</div>
              <div className="chips-grid" role="list" aria-label="Sample questions">
                {SAMPLE_QUESTIONS.map((chip, i) => (
                  <button
                    key={i}
                    className="chip"
                    role="listitem"
                    onClick={() => sendMessage(chip.query)}
                    disabled={loading}
                    id={`sample-chip-${i}`}
                  >
                    <span className="chip-icon">{chip.icon}</span>
                    <div>
                      <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '0.82rem' }}>
                        {chip.label}
                      </div>
                      <div style={{ color: 'var(--text-secondary)', fontSize: '0.78rem' }}>
                        {chip.query}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((m, i) =>
              m.role === 'user' ? (
                <UserMessage key={i} msg={m} />
              ) : (
                <AssistantMessage key={i} msg={m} />
              )
            )}
          </>
        )}

        {loading && <LoadingMessage startTime={loadingStart} />}

        {error && (
          <div className="error-card" role="alert">
            <p>
              {error.message.startsWith('⚠️') || error.message.startsWith('⚠')
                ? error.message
                : `⚠️ ${error.message}`}
            </p>

            {error.retryAfter && retryCountdown > 0 && (
              <div className="error-countdown-box">
                <span>⏱️</span>
                <span>Rate limit cooling down: retry in {retryCountdown}s</span>
              </div>
            )}

            {(!error.retryAfter || retryCountdown === 0) && (
              <button className="btn-retry" onClick={handleRetry} id="retry-btn">
                ↩ Retry Request
              </button>
            )}
          </div>
        )}

        <div ref={chatBottomRef} />
      </main>

      {/* Floating Executive Prompt Dock */}
      <div className="input-area">
        <div className="input-dock">
          <div className="input-wrap">
            <textarea
              ref={textareaRef}
              id="chat-input"
              className="input-textarea"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about pipeline value, work orders, win rates, or sector breakdown…"
              disabled={loading}
              maxLength={MAX_CHARS + 50}
              rows={1}
              aria-label="Chat input"
              aria-describedby="char-counter"
            />
            <div className="input-footer">
              <span className="keyboard-hint">
                Press <kbd style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: 4 }}>Enter ↵</kbd> to send • <kbd style={{ background: 'rgba(255,255,255,0.08)', padding: '1px 5px', borderRadius: 4 }}>Shift+Enter</kbd> for newline
              </span>
              <span
                id="char-counter"
                className={`char-count ${input.length > MAX_CHARS ? 'over' : ''}`}
              >
                {input.length}/{MAX_CHARS}
              </span>
            </div>
          </div>

          <button
            id="send-btn"
            className="btn-send"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim() || input.length > MAX_CHARS}
            aria-label="Send message"
            title="Send query"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  )
}
