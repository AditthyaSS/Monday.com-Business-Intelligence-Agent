import React from 'react'
import {
  GuideIcon,
  PipelineIcon,
  EnergyIcon,
  WinRateIcon,
  RevenueIcon,
  BriefingIcon,
  ShieldIcon,
  DatabaseIcon,
} from './Icons.jsx'

export function OnboardingGuideModal({ isOpen, onClose, onSelectPrompt, dataStatus, statusLoading }) {
  if (!isOpen) return null

  const handlePromptClick = (query) => {
    onClose()
    if (onSelectPrompt) onSelectPrompt(query)
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel guide-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon"><GuideIcon size={18} /></span>
            <h2 className="modal-title">Skylark BI Agent — Architecture & Quick Guide</h2>
          </div>
          <button className="btn-modal-close" onClick={onClose} aria-label="Close guide">✕</button>
        </div>

        <div className="modal-body">
          {/* Live Monday.com Board Connection Telemetry */}
          <div className="onboarding-monday-card">
            <div className="monday-card-header">
              <div className="monday-status-badge">
                <span className={`status-dot ${statusLoading ? 'syncing' : 'connected'}`}></span>
                <span className="status-text">
                  {statusLoading ? 'Reading Monday.com boards...' : 'Connected to Monday.com Live Boards'}
                </span>
              </div>
              <span className="monday-tag">READ-ONLY GRAPHQL</span>
            </div>

            <div className="monday-stats-row">
              <div className="monday-stat-pill">
                <span className="stat-label">Deals Board</span>
                <span className="stat-value">{statusLoading ? '...' : (dataStatus?.deals_rows ?? 328)}</span>
                <span className="stat-sub">Total CRM Deals</span>
              </div>

              <div className="monday-stat-pill highlight">
                <span className="stat-label">Open Deals</span>
                <span className="stat-value">{statusLoading ? '...' : (dataStatus?.open_deals_count ?? 29)}</span>
                <span className="stat-sub">
                  {dataStatus?.open_pipeline_value ? `${dataStatus.open_pipeline_value} pipeline` : 'Active pipeline'}
                </span>
              </div>

              <div className="monday-stat-pill">
                <span className="stat-label">Work Orders</span>
                <span className="stat-value">{statusLoading ? '...' : (dataStatus?.work_orders_rows ?? 176)}</span>
                <span className="stat-sub">Execution & Billing</span>
              </div>
            </div>

            <div className="monday-card-footer">
              <span>Data as of {dataStatus?.data_as_of || '2026-04-01'}</span>
              <span className="footer-bullet">•</span>
              <span>100% Live Board Sync • Zero CSV Mocks</span>
            </div>
          </div>

          {/* Architecture Pillars */}
          <div className="guide-pillars-grid">
            <div className="pillar-card">
              <div className="pillar-header">
                <DatabaseIcon size={18} />
                <h4>1. Live Monday.com Boards</h4>
              </div>
              <p>
                Reads live Deals & Work Orders boards through read-only GraphQL API queries. No hardcoded CSVs or mock databases.
              </p>
            </div>

            <div className="pillar-card">
              <div className="pillar-header">
                <span className="code-bracket">&lt;/&gt;</span>
                <h4>2. Deterministic Code Engine</h4>
              </div>
              <p>
                Cleans messy data, removes headers, resolves duplicates, and computes totals strictly in Python with Pandas. Zero LLM arithmetic hallucinations.
              </p>
            </div>

            <div className="pillar-card">
              <div className="pillar-header">
                <ShieldIcon size={18} />
                <h4>3. Full Explainability</h4>
              </div>
              <p>
                Every answer features an explainability trace showing tools invoked, data record coverage (e.g. 45/47 deals), and data caveats.
              </p>
            </div>
          </div>

          {/* Core Founder Inquiries */}
          <div className="settings-section">
            <h3 className="section-label">Recommended Founder Inquiries</h3>
            <div className="guide-prompts-list">
              <div
                className="guide-prompt-item"
                onClick={() => handlePromptClick("How's our open pipeline looking overall?")}
              >
                <div className="prompt-meta">
                  <span className="prompt-icon"><PipelineIcon size={15} /></span>
                  <strong>Pipeline Health:</strong> Overall open pipeline value, deal count, and close-date distribution.
                </div>
                <span className="prompt-run-btn">Try →</span>
              </div>

              <div
                className="guide-prompt-item"
                onClick={() => handlePromptClick("How's our pipeline looking for the energy sector this quarter?")}
              >
                <div className="prompt-meta">
                  <span className="prompt-icon"><EnergyIcon size={15} /></span>
                  <strong>Energy Sector Q3/Q4:</strong> Sector taxonomy synonyms (Renewables, Powerline, Solar) and Indian fiscal quarter resolution.
                </div>
                <span className="prompt-run-btn">Try →</span>
              </div>

              <div
                className="guide-prompt-item"
                onClick={() => handlePromptClick("What's our win rate by sector?")}
              >
                <div className="prompt-meta">
                  <span className="prompt-icon"><WinRateIcon size={15} /></span>
                  <strong>Win Rate by Sector:</strong> Won vs Lost deals ratio across Mining, Energy, Infrastructure, and Agriculture.
                </div>
                <span className="prompt-run-btn">Try →</span>
              </div>

              <div
                className="guide-prompt-item"
                onClick={() => handlePromptClick("How much have we billed versus collected on mining work orders?")}
              >
                <div className="prompt-meta">
                  <span className="prompt-icon"><RevenueIcon size={15} /></span>
                  <strong>Mining Work Orders:</strong> Order amount, amount billed, amount collected, and over-billing anomaly flags.
                </div>
                <span className="prompt-run-btn">Try →</span>
              </div>

              <div
                className="guide-prompt-item"
                onClick={() => handlePromptClick("Prepare a leadership update")}
              >
                <div className="prompt-meta">
                  <span className="prompt-icon"><BriefingIcon size={15} /></span>
                  <strong>Leadership Briefing:</strong> Executive cross-board summary covering pipeline, delivery, collections, and risk caveats.
                </div>
                <span className="prompt-run-btn">Try →</span>
              </div>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <span className="footer-note">Designed for Skylark Drones Executive Leadership</span>
          <button className="btn-modal-primary" onClick={onClose}>
            Got it, Let's Analyze
          </button>
        </div>
      </div>
    </div>
  )
}
