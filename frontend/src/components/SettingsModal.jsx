import React, { useState, useEffect } from 'react'
import { KeyIcon, CheckIcon, ShieldIcon, DatabaseIcon } from './Icons.jsx'

export function SettingsModal({ isOpen, onClose, telemetry, onKeyUpdated }) {
  const [geminiKey, setGeminiKey] = useState('')
  const [useAlways, setUseAlways] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (isOpen) {
      const storedKey = localStorage.getItem('skylark_custom_gemini_key') || ''
      const storedAlways = localStorage.getItem('skylark_byok_always') === 'true'
      setGeminiKey(storedKey)
      setUseAlways(storedAlways)
      setSaved(false)
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleSave = () => {
    const cleanKey = geminiKey.trim()
    if (cleanKey) {
      localStorage.setItem('skylark_custom_gemini_key', cleanKey)
      localStorage.setItem('skylark_byok_always', String(useAlways))
    } else {
      localStorage.removeItem('skylark_custom_gemini_key')
      localStorage.removeItem('skylark_byok_always')
    }
    setSaved(true)
    if (onKeyUpdated) onKeyUpdated(cleanKey)
    setTimeout(() => {
      setSaved(false)
      onClose()
    }, 1000)
  }

  const handleClear = () => {
    localStorage.removeItem('skylark_custom_gemini_key')
    localStorage.removeItem('skylark_byok_always')
    setGeminiKey('')
    setUseAlways(false)
    if (onKeyUpdated) onKeyUpdated('')
  }

  const callsToday = telemetry?.llm_calls_today ?? 0
  const dailyBudget = telemetry?.llm_daily_budget ?? 16
  const callsRemaining = Math.max(0, dailyBudget - callsToday)

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon"><KeyIcon size={18} /></span>
            <h2 className="modal-title">Settings & BYOK</h2>
          </div>
          <button className="btn-modal-close" onClick={onClose} aria-label="Close settings">✕</button>
        </div>

        <div className="modal-body">
          {/* Shared Quota Telemetry */}
          <div className="settings-section">
            <h3 className="section-label">Shared AI Quota Telemetry</h3>
            <div className="quota-telemetry-box">
              <div className="quota-stat">
                <span className="stat-label">Daily Budget</span>
                <span className="stat-value">{dailyBudget} calls</span>
              </div>
              <div className="quota-stat">
                <span className="stat-label">Calls Used Today</span>
                <span className="stat-value">{callsToday}</span>
              </div>
              <div className="quota-stat highlight">
                <span className="stat-label">Calls Remaining</span>
                <span className="stat-value">{callsRemaining} left</span>
              </div>
            </div>
            <p className="section-hint">
              Free-tier Gemini AI quota is capped per day. If shared quota is exhausted, you can plug in your personal key below to keep querying with AI narration, or use deterministic calculation.
            </p>
          </div>

          {/* BYOK Input Form */}
          <div className="settings-section">
            <h3 className="section-label">Bring Your Own Key (BYOK)</h3>
            <label className="input-label" htmlFor="byok-input">
              Google Gemini API Key
            </label>
            <input
              id="byok-input"
              type="password"
              className="settings-text-input"
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              placeholder="AIzaSy..."
              autoComplete="off"
            />

            <div className="checkbox-row">
              <input
                id="byok-always"
                type="checkbox"
                checked={useAlways}
                onChange={(e) => setUseAlways(e.target.checked)}
              />
              <label htmlFor="byok-always">
                Always use my key (bypasses shared daily quota completely)
              </label>
            </div>

            <div className="security-notice">
              <ShieldIcon size={15} />
              <span>
                <strong>Zero Storage:</strong> Your key is stored solely in your browser's local storage and only transmitted as an authorization header to process your requests.
              </span>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          {geminiKey && (
            <button className="btn-modal-secondary" onClick={handleClear}>
              Clear Key
            </button>
          )}
          <div className="footer-right">
            <button className="btn-modal-ghost" onClick={onClose}>
              Cancel
            </button>
            <button className="btn-modal-primary" onClick={handleSave}>
              {saved ? <><CheckIcon size={14} /> Saved!</> : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
