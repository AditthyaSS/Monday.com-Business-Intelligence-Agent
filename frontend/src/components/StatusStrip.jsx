import React, { useState } from 'react'

export function StatusStrip({ status, loading, error }) {
  const [expanded, setExpanded] = useState(false)

  if (loading) {
    return (
      <div className="status-strip-wrapper">
        <div className="status-strip">
          <div className="status-row">
            <span className="telemetry-beacon">
              <span className="beacon-dot" style={{ backgroundColor: '#a5b4fc', boxShadow: 'none' }} />
              CONNECTING TO MONDAY.COM
            </span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-tertiary)' }}>Syncing live boards…</span>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="status-strip-wrapper">
        <div className="status-strip" style={{ borderColor: 'rgba(239, 68, 68, 0.4)', background: 'rgba(220, 38, 38, 0.1)' }}>
          <div className="status-row">
            <span style={{ color: '#fca5a5', fontWeight: 600 }}>⚠️ Connection notice:</span>
            <span style={{ color: '#fecaca', fontSize: '0.8rem' }}>{error}</span>
          </div>
        </div>
      </div>
    )
  }

  if (!status) return null

  const aiLeft = status.llm_daily_budget - status.llm_calls_today
  const dao = status.data_as_of

  // Check if data is >45 days stale
  let isStale = status.stale_cache
  if (dao) {
    const daysOld = (Date.now() - new Date(dao).getTime()) / 86400000
    if (daysOld > 45) isStale = true
  }

  return (
    <div className="status-strip-wrapper">
      {isStale && (
        <div className="stale-banner" role="alert">
          <span>⚠️</span>
          <div>
            <strong>Historical / Snapshot Data Notice:</strong> Most recent board record is dated{' '}
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{dao || 'unknown'}</span>.
            {status.stale_cache && ' Showing cached snapshot (Monday.com currently unreachable).'}
          </div>
        </div>
      )}

      <div
        className="status-strip"
        onClick={() => setExpanded(e => !e)}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-label="System telemetry and data quality audit — click to toggle details"
        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && setExpanded(e => !e)}
      >
        <div className="status-row">
          <div className="telemetry-beacon">
            <span className="beacon-dot" />
            LIVE • READ ONLY
          </div>

          <div className="telemetry-metric">
            <span>📊 Deals:</span>
            <strong>{status.deals_rows}</strong>
          </div>

          <div className="telemetry-metric">
            <span>📑 Work Orders:</span>
            <strong>{status.work_orders_rows}</strong>
          </div>

          {dao && (
            <div className="telemetry-metric">
              <span>🕒 As of:</span>
              <strong>{dao}</strong>
            </div>
          )}

          <span className={`status-pill ${aiLeft > 5 ? 'pill-ok' : aiLeft > 0 ? 'pill-warn' : 'pill-error'}`}>
            ⚡ AI Quota: {aiLeft} left
          </span>

          {status.degraded && (
            <span className="status-pill pill-warn">
              ⚡ Degraded Engine
            </span>
          )}

          {status.stale_cache && (
            <span className="status-pill pill-warn">
              📦 Cached
            </span>
          )}

          <div className="status-expand-icon">
            <span style={{ fontSize: '0.74rem', marginRight: 4 }}>
              {expanded ? 'Hide Audit' : 'Quality Audit'}
            </span>
            <span>{expanded ? '▲' : '▼'}</span>
          </div>
        </div>

        {expanded && (
          <div className="status-details" onClick={e => e.stopPropagation()}>
            <div className="audit-card">
              <div className="audit-card-title">
                <span>🛡️</span> Data Quality Invariants
              </div>
              {status.quality_lines?.length > 0 ? (
                <ul>
                  {status.quality_lines.map((l, i) => (
                    <li key={i}>{l}</li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: 'var(--text-tertiary)' }}>No data anomalies reported.</div>
              )}
            </div>

            <div className="audit-card">
              <div className="audit-card-title">
                <span>⚠️</span> Normalisation & Warnings
              </div>
              {status.warnings?.length > 0 ? (
                <ul>
                  {status.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              ) : (
                <div style={{ color: 'var(--text-tertiary)' }}>All board constraints satisfied.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
