import React, { useState, useEffect, useRef, useCallback } from 'react'
import { StatusStrip } from './components/StatusStrip.jsx'
import { UserMessage, AssistantMessage } from './components/Message.jsx'
import { LoadingMessage } from './components/LoadingMessage.jsx'
import { ErrorCard } from './components/ErrorCard.jsx'
import { SettingsModal } from './components/SettingsModal.jsx'
import { OnboardingGuideModal } from './components/OnboardingGuideModal.jsx'
import { PersonaSelectionModal } from './components/PersonaSelectionModal.jsx'
import { getPersona, PersonaAvatar } from './components/ExecutivePersonas.jsx'
import { ExploreInsightsModal } from './components/ExploreInsightsModal.jsx'
import {
  SkylarkDroneLogo,
  SkylarkChatbotIcon,
  FounderIcon,
  PipelineIcon,
  EnergyIcon,
  WinRateIcon,
  RevenueIcon,
  BriefingIcon,
  GearIcon,
  GuideIcon,
  KeyIcon,
  DatabaseIcon,
  HandDrawnPlus,
  HandDrawnMic,
  HandDrawnWaveform,
  HandDrawnSend,
  HandDrawnSidebar,
} from './components/Icons.jsx'

const MAX_CHARS = 1000
const MAX_HISTORY = 8
const ABORT_MS = 90000

// Internal rotation pools for the 3 visible sample questions (compact discovery)
const DISCOVERY_ROTATION_POOLS = [
  [
    'Which deals should leadership worry about right now?',
    'How much is currently tied up in receivables?',
    'Which sectors have both a large sales pipeline and operational delivery risk?',
  ],
  [
    "How's our open pipeline looking overall?",
    'Which work orders are delayed past their end date?',
    'Where are sales exposure and execution risk overlapping?',
  ],
  [
    'Where are our biggest sales and execution risks?',
    'How much have we billed versus collected?',
    'Can I trust the current data from Monday.com?',
  ],
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
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isGuideOpen, setIsGuideOpen] = useState(false)
  const [isExploreOpen, setIsExploreOpen] = useState(false)
  const [byokKey, setByokKey] = useState('')

  // 3 carefully selected sample questions rotated per page load
  const [visibleExamples] = useState(() => {
    const idx = Math.floor(Math.random() * DISCOVERY_ROTATION_POOLS.length)
    return DISCOVERY_ROTATION_POOLS[idx]
  })

  // Executive Character Persona state
  const [personaId, setPersonaId] = useState(() => {
    return localStorage.getItem('skylark_user_persona') || 'pathfinder'
  })
  const [isPersonaModalOpen, setIsPersonaModalOpen] = useState(false)
  const [isOnboardingPersona, setIsOnboardingPersona] = useState(true)
  const activePersona = getPersona(personaId)

  const chatBottomRef = useRef(null)
  const textareaRef = useRef(null)
  const abortRef = useRef(null)
  const retryTimerRef = useRef(null)
  const [retryCountdown, setRetryCountdown] = useState(0)

  // Initialize BYOK from localStorage
  useEffect(() => {
    const stored = localStorage.getItem('skylark_custom_gemini_key') || ''
    setByokKey(stored)
  }, [])

  // Dynamic greeting based on time of day and executive persona
  const getGreeting = () => {
    const hour = new Date().getHours()
    let timeStr = 'Good morning'
    if (hour >= 12 && hour < 17) timeStr = 'Good afternoon'
    else if (hour >= 17) timeStr = 'Good evening'
    return `${timeStr}, ${activePersona.name}`
  }


  // Load telemetry from server
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

  // Auto-scroll
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, error])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`
    }
  }, [input])

  // Discovery insight selection handler (populates input and focuses textarea)
  const handleSelectInsight = useCallback((query) => {
    setInput(query)
    setIsExploreOpen(false)
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus()
        textareaRef.current.style.height = 'auto'
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 240)}px`
      }
    }, 60)
  }, [])

  const sendMessage = useCallback(
    async (text, options = {}) => {
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
        compute_directly: Boolean(options?.computeDirectly),
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
        const headers = { 'Content-Type': 'application/json' }
        if (options?.computeDirectly) {
          headers['X-Compute-Directly'] = 'true'
        }
        const activeKey = localStorage.getItem('skylark_custom_gemini_key') || ''
        if (activeKey.trim()) {
          headers['X-Custom-Gemini-Key'] = activeKey.trim()
        }

        const res = await fetch('/api/chat', {
          method: 'POST',
          headers,
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
  const callsRemaining = status ? Math.max(0, status.llm_daily_budget - status.llm_calls_today) : 16

  return (
    <div className="claude-app-container">
      {/* Left Sidebar — Skylark BI Style */}
      <aside className={`claude-sidebar ${sidebarOpen ? 'open' : 'collapsed'}`}>
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <SkylarkDroneLogo size={26} />
            <span className="sidebar-title">Skylark BI</span>
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
          <span>New Briefing</span>
        </button>

        {/* Practical Navigation Actions */}
        <div className="sidebar-nav-section">
          <div className="sidebar-nav-item" onClick={() => setIsPersonaModalOpen(true)}>
            <span className="nav-icon"><PersonaAvatar id={personaId} size={16} /></span>
            <span>Character: {activePersona.name}</span>
          </div>

          <div className="sidebar-nav-item" onClick={() => setIsGuideOpen(true)}>
            <span className="nav-icon"><GuideIcon size={16} /></span>
            <span>Architecture & Guide</span>
          </div>

          <div className="sidebar-nav-item" onClick={() => setIsExploreOpen(true)}>
            <span className="nav-icon"><GuideIcon size={16} /></span>
            <span>Explore Insights</span>
          </div>

          <div className="sidebar-nav-item" onClick={() => setIsSettingsOpen(true)}>
            <span className="nav-icon"><GearIcon size={16} /></span>
            <span>Settings & BYOK</span>
            {byokKey && <span className="byok-active-tag">BYOK</span>}
          </div>

          <div className="sidebar-nav-item" onClick={() => setShowStatusStrip(!showStatusStrip)}>
            <span className="nav-icon"><DatabaseIcon size={16} /></span>
            <span>Data & Telemetry</span>
          </div>
        </div>

        {/* Real-time Token & API Budget Telemetry Meter */}
        <div className="sidebar-quota-box">
          <div className="quota-meter-header">
            <span className="quota-meter-title">Daily AI Quota</span>
            <span className="quota-meter-count">{callsRemaining}/16 left</span>
          </div>
          <div className="quota-meter-bar">
            <div
              className="quota-meter-fill"
              style={{ width: `${Math.min(100, (callsRemaining / 16) * 100)}%` }}
            />
          </div>
          <span className="quota-meter-hint">
            {byokKey ? 'BYOK Key Active (Bypasses Quota)' : 'Resets at midnight UTC'}
          </span>
        </div>

        <div className="sidebar-section-title">Saved Briefings</div>
        <div className="sidebar-history-list">
          <div className="history-item" onClick={() => sendMessage("How's our open pipeline looking overall?")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Overall Pipeline Health</span>
          </div>
          <div className="history-item" onClick={() => sendMessage("How's our pipeline looking for the energy sector this quarter?")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Energy Sector Q3/Q4</span>
          </div>
          <div className="history-item" onClick={() => sendMessage("What's our win rate by sector?")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Win Rate Analysis</span>
          </div>
          <div className="history-item" onClick={() => sendMessage("How much have we billed versus collected on mining work orders?")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Mining Billed vs Collected</span>
          </div>
          <div className="history-item" onClick={() => sendMessage("Prepare a leadership update")}>
            <span className="history-bullet">•</span>
            <span className="history-text">Executive Leadership Update</span>
          </div>
        </div>

        <div className="sidebar-footer">
          <div
            className="sidebar-user-pill"
            onClick={() => setIsPersonaModalOpen(true)}
            title="Click to switch your executive character"
          >
            <div className="founder-icon-wrapper">
              <PersonaAvatar id={personaId} size={28} />
            </div>
            <div className="user-info-text">
              <span className="user-name">{activePersona.name}</span>
              <span className="user-plan">{activePersona.role}</span>
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
            <SkylarkDroneLogo size={22} />
            <span className="top-brand-text">Skylark BI</span>
            <span className="live-pill">LIVE BOARDS</span>
          </div>

          <div className="claude-top-right">
            <button
              className="telemetry-pill-btn"
              onClick={() => setIsExploreOpen(true)}
              title="Explore all BI insight capabilities"
            >
              <GuideIcon size={14} />
              <span>Explore Insights</span>
            </button>

            <button
              className="telemetry-pill-btn persona-pill"
              onClick={() => setIsPersonaModalOpen(true)}
              title="Switch Executive Character"
            >
              <PersonaAvatar id={personaId} size={16} />
              <span>{activePersona.name}</span>
            </button>

            <button
              className="telemetry-pill-btn"
              onClick={() => setIsSettingsOpen(true)}
              title="Configure BYOK API Key"
            >
              <KeyIcon size={14} />
              <span>{byokKey ? 'BYOK Active' : 'BYOK Key'}</span>
            </button>

            <button
              className="telemetry-pill-btn"
              onClick={() => setIsGuideOpen(true)}
              title="Architecture & Onboarding Guide"
            >
              <GuideIcon size={14} />
              <span>Guide</span>
            </button>

            <span className="free-plan-tag">{callsRemaining}/16 Requests Left</span>
          </div>
        </header>

        {showStatusStrip && (
          <StatusStrip status={status} loading={statusLoading} error={statusError} />
        )}

        {/* Scrollable Conversation Stream */}
        <main className="claude-chat-scroll" id="claude-chat-container">
          {isEmpty ? (
            /* Claude-Inspired Skylark Hero View */
            <div className="claude-hero-container">
              <div className="claude-greeting-heading">
                <div className="greeting-title-row">
                  <SkylarkDroneLogo size={38} className="hero-starburst" />
                  <h1 className="greeting-text">Ask Skylark Intelligence</h1>
                </div>
                <p className="hero-subtitle">
                  Ask a question about sales, operations, pipeline, or business performance.
                </p>
                <div
                  className="persona-hero-badge"
                  onClick={() => setIsPersonaModalOpen(true)}
                  title="Click to switch executive character"
                >
                  <PersonaAvatar id={personaId} size={18} />
                  <span className="persona-badge-role">{activePersona.role}</span>
                  <span className="persona-badge-dot">•</span>
                  <span className="persona-badge-switch">{activePersona.name} ↻</span>
                </div>
              </div>

              {/* Centered Floating Capsule */}
              <div className="claude-input-capsule">
                <textarea
                  ref={textareaRef}
                  id="chat-input"
                  className="claude-textarea"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about sales, operations, pipeline, or business performance..."
                  disabled={loading}
                  maxLength={MAX_CHARS + 50}
                  rows={2}
                  aria-label="Ask Skylark BI agent"
                />

                <div className="claude-capsule-toolbar">
                  <div className="toolbar-left">
                    <button
                      className="capsule-icon-btn"
                      onClick={() => setIsSettingsOpen(true)}
                      title="Settings & BYOK"
                    >
                      <GearIcon size={16} />
                    </button>
                    <span className="model-selector-pill">
                      {byokKey ? 'Gemini (BYOK)' : 'Gemini 3.5 Flash'}
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

              {/* Compact Discovery Section */}
              <div className="discovery-section">
                <div className="discovery-header">
                  <span className="discovery-label">Try asking</span>
                </div>

                <div className="discovery-pills-row" role="group" aria-label="Sample questions">
                  {visibleExamples.map((ex, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="discovery-pill"
                      onClick={() => handleSelectInsight(ex)}
                      title={`Load: "${ex}"`}
                    >
                      <span className="discovery-pill-text">{ex}</span>
                    </button>
                  ))}
                </div>

                <div className="discovery-footer">
                  <button
                    type="button"
                    className="btn-explore-insights"
                    onClick={() => setIsExploreOpen(true)}
                    aria-label="Open Explore Insights discovery menu"
                  >
                    <span>Explore insights</span>
                    <span className="arrow" aria-hidden="true">→</span>
                  </button>
                </div>
              </div>
            </div>
          ) : (
            /* Active Message Thread */
            <div className="claude-messages-wrapper">
              {messages.map((m, idx) =>
                m.role === 'user' ? (
                  <UserMessage key={idx} msg={m} personaId={personaId} />
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

              {error && (
                <ErrorCard
                  error={error}
                  onRetry={handleRetry}
                  retryCountdown={retryCountdown}
                  onRunDeterministic={() => {
                    const lastUser = [...messages].reverse().find((m) => m.role === 'user')
                    if (lastUser) sendMessage(lastUser.content, { computeDirectly: true })
                  }}
                />
              )}

              <div ref={chatBottomRef} />
            </div>
          )}
        </main>

        {/* Floating Bottom Dock (In Active Chat) */}
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
                  <button
                    className="capsule-icon-btn"
                    onClick={() => setIsSettingsOpen(true)}
                    title="Settings & BYOK"
                  >
                    <GearIcon size={16} />
                  </button>
                  <span className="model-selector-pill in-chat">
                    {byokKey ? 'Gemini (BYOK)' : 'Gemini 3.5 Flash'}
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

      {/* Settings & BYOK Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        telemetry={status}
        onKeyUpdated={(k) => setByokKey(k)}
      />

      {/* Onboarding Architecture Guide Modal */}
      <OnboardingGuideModal
        isOpen={isGuideOpen}
        onClose={() => setIsGuideOpen(false)}
        onSelectPrompt={(q) => sendMessage(q)}
        dataStatus={status}
        statusLoading={statusLoading}
      />

      {/* Executive Character Persona Selection Modal */}
      <PersonaSelectionModal
        isOpen={isPersonaModalOpen || isOnboardingPersona}
        onClose={() => {
          setIsPersonaModalOpen(false)
          setIsOnboardingPersona(false)
          sessionStorage.setItem('skylark_session_onboarded', 'true')
        }}
        currentPersonaId={personaId}
        onSelectPersona={(newId) => {
          setPersonaId(newId)
          localStorage.setItem('skylark_user_persona', newId)
          sessionStorage.setItem('skylark_session_onboarded', 'true')
          setIsOnboardingPersona(false)
        }}
        isOnboarding={isOnboardingPersona}
        dataStatus={status}
        statusLoading={statusLoading}
        onLaunchPrompt={(prompt) => {
          setIsPersonaModalOpen(false)
          setIsOnboardingPersona(false)
          sessionStorage.setItem('skylark_session_onboarded', 'true')
          sendMessage(prompt)
        }}
      />

      {/* Explore Insights Discovery Modal */}
      <ExploreInsightsModal
        isOpen={isExploreOpen}
        onClose={() => setIsExploreOpen(false)}
        onSelectInsight={handleSelectInsight}
      />
    </div>
  )
}
