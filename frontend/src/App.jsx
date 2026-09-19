import React, { useState, useEffect, useRef, useCallback } from 'react'
import { StatusStrip } from './components/StatusStrip.jsx'
import { UserMessage, AssistantMessage } from './components/Message.jsx'
import { LoadingMessage } from './components/LoadingMessage.jsx'

const MAX_CHARS = 1000
const MAX_HISTORY = 8
const ABORT_MS = 90000

const SAMPLE_CHIPS = [
  "How's our open pipeline looking overall?",
  "How's our pipeline looking for the energy sector this quarter?",
  "What's our win rate by sector?",
  "How much have we billed versus collected on mining work orders?",
  "Give me a sector overview across deals and work orders",
  "Prepare a leadership update",
]

export default function App() {
  const [messages, setMessages] = useState([])  // {role, content, trace?, degraded?, model?}
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null) // {message, retryAfter?}
  const [status, setStatus] = useState(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [statusError, setStatusError] = useState(null)

  const chatBottomRef = useRef(null)
  const abortRef = useRef(null)
  const retryTimerRef = useRef(null)
  const [retryCountdown, setRetryCountdown] = useState(0)

  // Load data status on mount (retry a few times for cold starts)
  useEffect(() => {
    let attempts = 0
    const tryLoad = async () => {
      try {
        const res = await fetch('/api/data-status')
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        setStatus(data)
        setStatusLoading(false)
      } catch (e) {
        attempts++
        if (attempts < 5) {
          setTimeout(tryLoad, 3000 * attempts)
        } else {
          setStatusError(e.message)
          setStatusLoading(false)
        }
      }
    }
    tryLoad()
  }, [])

  // Auto-scroll on new messages
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || loading) return
    setError(null)

    const userMsg = { role: 'user', content: text.trim() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Build history (last MAX_HISTORY messages)
    const allMessages = [...messages, userMsg].slice(-MAX_HISTORY)
    const payload = { messages: allMessages.map(m => ({ role: m.role, content: m.content })) }

    const controller = new AbortController()
    abortRef.current = controller

    const abortTimer = setTimeout(() => {
      controller.abort()
      setLoading(false)
      setError({ message: "The request timed out after 90 seconds. Please try again." })
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
        const errMsg = data?.error?.user_message || data?.error?.message || `Server error (${res.status})`
        const retryAfter = data?.error?.retry_after_seconds ?? data?.retry_after_seconds ?? null
        setError({ message: errMsg, retryAfter })
        if (retryAfter && retryAfter > 0) {
          setRetryCountdown(retryAfter)
          clearInterval(retryTimerRef.current)
          retryTimerRef.current = setInterval(() => {
            setRetryCountdown(c => {
              if (c <= 1) { clearInterval(retryTimerRef.current); return 0 }
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
        setMessages(prev => [...prev, assistantMsg])
        // Refresh status
        fetch('/api/data-status').then(r => r.json()).then(setStatus).catch(() => {})
      }
    } catch (e) {
      clearTimeout(abortTimer)
      if (e.name !== 'AbortError') {
        setError({ message: "Connection error. Is the server running?" })
      }
    } finally {
      setLoading(false)
    }
  }, [messages, loading])

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (input.trim() && input.length <= MAX_CHARS) {
        sendMessage(input)
      }
    }
  }

  const handleRetry = () => {
    const lastUser = [...messages].reverse().find(m => m.role === 'user')
    if (lastUser) sendMessage(lastUser.content)
  }

  const isEmpty = messages.length === 0 && !loading

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1><span className="header-logo">🚁</span> Skylark BI Agent</h1>
        <div className="header-subtitle">
          Read-only business intelligence over monday.com Deals and Work Orders
        </div>
      </header>

      {/* Status */}
      <StatusStrip status={status} loading={statusLoading} error={statusError} />

      {/* Chat area */}
      <main className="chat-area" id="chat-area" aria-label="Chat messages" aria-live="polite">
        {isEmpty ? (
          <div className="empty-state">
            <div className="empty-state-icon">📈</div>
            <h2>Ask me about your pipeline & work orders</h2>
            <p>I can answer questions about deals, work orders, win rates, sector breakdown, and more — live from monday.com.</p>
            <div className="chips" role="list" aria-label="Sample questions">
              {SAMPLE_CHIPS.map((chip, i) => (
                <button
                  key={i}
                  className="chip"
                  role="listitem"
                  onClick={() => sendMessage(chip)}
                  disabled={loading}
                  id={`sample-chip-${i}`}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((m, i) => (
              m.role === 'user'
                ? <UserMessage key={i} msg={m} />
                : <AssistantMessage key={i} msg={m} />
            ))}
          </>
        )}

        {loading && <LoadingMessage startTime={Date.now()} />}

        {error && (
          <div className="error-card" role="alert">
            <p>{error.message.startsWith('⚠️') || error.message.startsWith('⚠') ? error.message : `⚠️ ${error.message}`}</p>
            {error.retryAfter && retryCountdown > 0 && (
              <div className="countdown">Retry available in {retryCountdown}s</div>
            )}
            {(!error.retryAfter || retryCountdown === 0) && (
              <button className="btn-retry" onClick={handleRetry} id="retry-btn">
                ↩ Retry
              </button>
            )}
          </div>
        )}

        <div ref={chatBottomRef} />
      </main>

      {/* Input area */}
      <div className="input-area">
        <div className="input-row">
          <div className="input-wrap">
            <textarea
              id="chat-input"
              className="input-textarea"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about pipeline, work orders, win rate… (Enter to send, Shift+Enter for newline)"
              disabled={loading}
              maxLength={MAX_CHARS + 50}
              rows={1}
              aria-label="Chat input"
              aria-describedby="char-counter"
            />
            <div
              id="char-counter"
              className={`char-count ${input.length > MAX_CHARS ? 'over' : ''}`}
            >
              {input.length}/{MAX_CHARS}
            </div>
          </div>
          <button
            id="send-btn"
            className="btn-send"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim() || input.length > MAX_CHARS}
            aria-label="Send message"
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  )
}
