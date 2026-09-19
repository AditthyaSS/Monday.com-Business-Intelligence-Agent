import React, { useState, useEffect, useRef, useCallback } from 'react'
import { StatusStrip } from './components/StatusStrip.jsx'
import { UserMessage, AssistantMessage } from './components/Message.jsx'
import { LoadingMessage } from './components/LoadingMessage.jsx'
import { ErrorCard } from './components/ErrorCard.jsx'
import {
  ClaudeLogo,
  HandDrawnWrite,
  HandDrawnLearn,
  HandDrawnCode,
  HandDrawnCoffee,
  HandDrawnBulb,
  HandDrawnPlus,
  HandDrawnMic,
  HandDrawnWaveform,
  HandDrawnSend,
  HandDrawnSidebar,
} from './components/Icons.jsx'

const MAX_CHARS = 1000
const MAX_HISTORY = 8
const ABORT_MS = 90000

// Claude prompt chips matching screenshot style
const CLAUDE_PROMPTS = [
  {
    icon: <HandDrawnWrite size={15} />,
    label: 'Pipeline Health',
    tag: 'Write',
    query: "How's our open pipeline looking overall?",
  },
  {
    icon: <HandDrawnLearn size={15} />,
    label: 'Energy Sector',
    tag: 'Learn',
    query: "How's our pipeline looking for the energy sector this quarter?",
  },
  {
    icon: <HandDrawnCode size={15} />,
    label: 'Win Rate Analysis',
    tag: 'Code',
    query: "What's our win rate by sector?",
  },
  {
    icon: <HandDrawnCoffee size={15} />,
    label: 'Mining Billed vs Collected',
    tag: 'Life stuff',
    query: "How much have we billed versus collected on mining work orders?",
  },
  {
    icon: <HandDrawnBulb size={15} />,
    label: 'Leadership Update',
    tag: "Claude's choice",
    query: "Prepare a leadership update",
  },
]

export default function App() {
  const [messages, setMessages] = useState([]) // {role, content, trace?, degraded?, model?}
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingStart, setLoadingStart] = useState(0)
  const [error, setError] = useState(null)
  const [status, setStatus] = useState(null)
  const [statusLoading, setStatusLoading] = useState(true)
  const [statusError, setStatusError] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [showStatusStrip, setShowStatusStrip] = useState(false)

  const chatBottomRef = useRef(null)
  const textareaRef = useRef(null)
  const abortRef = useRef(null)
  const retryTimerRef = useRef(null)
  const [retryCountdown, setRetryCountdown] = useState(0)

  // Dynamic greeting based on time of day (matching Claude: "Evening, how are things?")
  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Morning, how are things?'
    if (hour < 17) return 'Afternoon, how are things?'
    return 'Evening, how are things?'
  }

  // Load live telemetry
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
  }, [messages, loading, error])

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`
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
        textareaRef.current.style.height = '48px'
      }

      setLoading(true)
      setLoadingStart(Date.now())

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
          code: 'TIMEOUT',
          message: "🛰️ My AI brain didn't answer in time. No worries, the underlying numbers are still available.",
          user_message: "🛰️ My AI brain didn't answer in time. No worries, the underlying numbers are still available.",
          status: 504,
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

        let data = null
        const contentType = res.headers.get('content-type') || ''
        if (contentType.includes('application/json')) {
          try {
            data = await res.json()
          } catch (jsonErr) {
            data = null
          }
        } else {
          // HTML edge response (404/502)
          data = {
            error: {
              code: res.status === 404 ? 'GATEWAY_404' : 'SERVER_ERROR',
              message: `HTTP ${res.status}`,
              user_message: "🛠️ I hit a small snag while working on that. Please try again.",
            },
          }
        }

        if (!res.ok || !data || data.error) {
          const errObj = data?.error || {}
          const errMsg = errObj.user_message || errObj.message || "🛠️ I hit a small snag while working on that. Please try again."
          const retryAfter = errObj.retry_after_seconds ?? data?.retry_after_seconds ?? null

          setError({
            code: errObj.code || `HTTP_${res.status}`,
            message: errObj.message || errMsg,
            user_message: errMsg,
            retryAfter,
            status: res.status,
          })

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
          fetchStatus()
        }
      } catch (e) {
        clearTimeout(abortTimer)
        if (e.name !== 'AbortError') {
          setError({
            code: 'NETWORK_ERROR',
            message: e.message || 'Failed to fetch',
            user_message: "🤖 I can't reach Monday right now. The data desk seems to be taking a coffee break. I'll use the latest cached data if available.",
            status: 0,
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
    if (lastUser) {
      sendMessage(lastUser.content)
    } else if (input.trim()) {
      sendMessage(input)
    }
  }

  const handleClearSession = () => {
    if (loading) return
    setMessages([])
    setError(null)
    setInput('')
  }

  const isEmpty = messages.length === 0 && !loading

  return (
    <div className="claude-app-container">
      {/* Left Claude-Inspired Sidebar */}
      <aside className={`claude-sidebar ${sidebarOpen ? 'open' : 'collapsed'}`}>
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <ClaudeLogo size={24} />
            <span className="sidebar-title">Claude</span>
          </div>
          <button
            className="sidebar-toggle-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title="Toggle sidebar"
            aria-label="Toggle sidebar"
          >
            <HandDrawnSidebar size={18} />
          </button>
        </div>

        <button className="btn-new-chat" onClick={handleClearSession} disabled={loading}>
          <HandDrawnPlus size={16} />
          <span>New chat</span>
        </button>

        <div className="sidebar-nav-section">
          <div className="sidebar-nav-item">
            <span className="nav-icon">📁</span>
            <span>Projects</span>
          </div>
          <div className="sidebar-nav-item">
            <span className="nav-icon">📄</span>
            <span>Artifacts</span>
          </div>
          <div className="sidebar-nav-item">
            <span className="nav-icon">&lt;/&gt;</span>
            <span>Code</span>
            <span className="upgrade-pill">Upgrade</span>
          </div>
          <div className="sidebar-nav-item">
            <span className="nav-icon">⚙️</span>
            <span>Customize</span>
          </div>
        </div>

        <div className="sidebar-section-title">Pinned</div>
        <div className="sidebar-history-list">
          <div className="history-item" onClick={() => sendMessage("How's our pipeline looking for the energy sector this quarter?")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Energy Sector Q3/Q4</span>
          </div>
          <div className="history-item" onClick={() => sendMessage("How's our open pipeline looking overall?")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Pipeline Health Q3</span>
          </div>
        </div>

        <div className="sidebar-section-title">Chats and tasks</div>
        <div className="sidebar-history-list">
          <div className="history-item" onClick={() => sendMessage("What's our win rate by sector?")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Win rate by sector</span>
          </div>
          <div className="history-item" onClick={() => sendMessage("How much have we billed versus collected on mining work orders?")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Mining Billed vs Collected</span>
          </div>
          <div className="history-item" onClick={() => sendMessage("Prepare a leadership update")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Leadership briefing</span>
          </div>
        </div>

        <div className="sidebar-footer">
          <div className="sidebar-user-pill">
            <span className="user-avatar-initial">A</span>
            <div className="user-info-text">
              <span className="user-name">Aditthya</span>
              <span className="user-plan">Founder • Skylark Drones</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Chat Workspace */}
      <div className="claude-main-workspace">
        {/* Top Minimalist Header */}
        <header className="claude-top-bar">
          {!sidebarOpen && (
            <button
              className="sidebar-open-btn"
              onClick={() => setSidebarOpen(true)}
              title="Open sidebar"
              aria-label="Open sidebar"
            >
              <HandDrawnSidebar size={18} />
            </button>
          )}

          <div className="claude-top-brand">
            <ClaudeLogo size={20} />
            <span className="top-brand-text">Skylark BI Agent</span>
            <span className="live-pill">LIVE BOARDS</span>
          </div>

          <div className="claude-top-right">
            <button
              className="telemetry-pill-btn"
              onClick={() => setShowStatusStrip(!showStatusStrip)}
              title="Toggle Telemetry Audit Drawer"
            >
              <span className="beacon-dot" />
              <span>Telemetry</span>
            </button>
            <span className="free-plan-tag">Read-Only • Monday.com</span>
          </div>
        </header>

        {showStatusStrip && (
          <StatusStrip status={status} loading={statusLoading} error={statusError} />
        )}

        {/* Scrollable Conversation Stream */}
        <main className="claude-chat-scroll" id="claude-chat-container">
          {isEmpty ? (
            /* Claude Hero State matching user screenshot */
            <div className="claude-hero-container">
              <div className="claude-greeting-heading">
                <ClaudeLogo size={36} className="hero-starburst" />
                <h1 className="greeting-text">{getGreeting()}</h1>
              </div>

              {/* Centered Claude Input Box Capsule */}
              <div className="claude-input-capsule">
                <textarea
                  ref={textareaRef}
                  id="chat-input"
                  className="claude-textarea"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="How can I help you today?"
                  disabled={loading}
                  maxLength={MAX_CHARS + 50}
                  rows={1}
                  aria-label="Chat input"
                />

                <div className="claude-capsule-toolbar">
                  <div className="toolbar-left">
                    <button className="capsule-icon-btn" title="Add context">
                      <HandDrawnPlus size={16} />
                    </button>
                    <div className="mode-toggle-group">
                      <span className="mode-tab active">Chat</span>
                      <span className="mode-tab">Cowork</span>
                    </div>
                  </div>

                  <div className="toolbar-right">
                    <span className="model-selector-pill">
                      Sonnet 3.5
                      <span className="pill-arrow">▾</span>
                    </span>
                    <button className="capsule-icon-btn" title="Voice dictation">
                      <HandDrawnMic size={16} />
                    </button>
                    <button className="capsule-icon-btn" title="Voice response">
                      <HandDrawnWaveform size={16} />
                    </button>
                    <button
                      id="send-btn"
                      className={`claude-send-btn ${input.trim() && !loading ? 'ready' : ''}`}
                      onClick={() => sendMessage(input)}
                      disabled={loading || !input.trim() || input.length > MAX_CHARS}
                      title="Send message"
                      aria-label="Send message"
                    >
                      <HandDrawnSend size={16} />
                    </button>
                  </div>
                </div>
              </div>

              {/* Claude Prompt Suggestion Pills */}
              <div className="claude-chips-row">
                {CLAUDE_PROMPTS.map((p, idx) => (
                  <button
                    key={idx}
                    className="claude-prompt-pill"
                    onClick={() => sendMessage(p.query)}
                    disabled={loading}
                  >
                    <span className="pill-icon">{p.icon}</span>
                    <span className="pill-text">{p.tag}</span>
                    <span className="pill-query">({p.label})</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Active Message List */
            <div className="claude-messages-wrapper">
              {messages.map((m, idx) =>
                m.role === 'user' ? (
                  <UserMessage key={idx} msg={m} />
                ) : (
                  <AssistantMessage
                    key={idx}
                    msg={m}
                    onRetry={() => {
                      const prevUser = messages[idx - 1]?.content
                      if (prevUser) sendMessage(prevUser)
                    }}
                  />
                )
              )}

              {loading && <LoadingMessage startTime={loadingStart} />}

              {/* Error card with situation message and Lottie animation */}
              {error && (
                <ErrorCard
                  error={error}
                  onRetry={handleRetry}
                  retryCountdown={retryCountdown}
                  onRunDeterministic={() => {
                    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
                    if (lastUser) sendMessage(lastUser.content)
                  }}
                />
              )}

              <div ref={chatBottomRef} />
            </div>
          )}
        </main>

        {/* Floating Bottom Input when chat has active messages */}
        {!isEmpty && (
          <div className="claude-bottom-dock">
            <div className="claude-input-capsule in-chat">
              <textarea
                ref={textareaRef}
                className="claude-textarea"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Reply to Skylark BI Agent…"
                disabled={loading}
                maxLength={MAX_CHARS + 50}
                rows={1}
                aria-label="Chat input"
              />

              <div className="claude-capsule-toolbar">
                <div className="toolbar-left">
                  <button className="capsule-icon-btn" title="Add context">
                    <HandDrawnPlus size={16} />
                  </button>
                  <span className="model-selector-pill in-chat">
                    Sonnet 3.5 Medium
                  </span>
                </div>

                <div className="toolbar-right">
                  <span className="char-count-minimal">
                    {input.length}/{MAX_CHARS}
                  </span>
                  <button
                    className={`claude-send-btn ${input.trim() && !loading ? 'ready' : ''}`}
                    onClick={() => sendMessage(input)}
                    disabled={loading || !input.trim() || input.length > MAX_CHARS}
                    title="Send message"
                  >
                    <HandDrawnSend size={16} />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
