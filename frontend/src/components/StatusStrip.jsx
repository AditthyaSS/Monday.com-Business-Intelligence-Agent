import React, { useState } from 'react'
import {
  PipelineIcon,
  BriefingIcon,
  ClockIcon,
  KeyIcon,
  ShieldIcon,
  WarningIcon,
  DatabaseIcon,
} from './Icons.jsx'

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
            <span style={{ fontSize: '0.78rem', color: 'var(--claude-text-tertiary)' }}>Syncing live boards…</span>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="status-strip-wrapper">
        <div className="status-strip" style={{ borderColor: 'rgba(239, 68, 68, 0.4)', background: '#FEF2F2' }}>
          <div className="status-row">
            <span style={{ color: '#DC2626', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <WarningIcon size={14} /> Connection notice:
            </span>
            <span style={{ color: '#991B1B', fontSize: '0.8rem' }}>{error}</span>
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
          <WarningIcon size={16} />
          <div>
            <strong>Historical / Snapshot Data Notice:</strong> Most recent board record is dated{' '}
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{dao || 'unknown'}</span>.
            {status.stale_cache && ' Showing cached snapshot (Monday.com currently unreachable).'}
          </div>
        </div>
      )}

      <div
        className="status-strip"
        onClick={() => setExpanded((e) => !e)}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-label="System telemetry and data quality audit — click to toggle details"
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && setExpanded((e) => !e)}
      >
        <div className="status-row">
          <div className="telemetry-beacon">
            <span className="beacon-dot" />
            LIVE • READ ONLY
          </div>

          <div className="telemetry-metric">
            <PipelineIcon size={14} />
            <span>Deals:</span>
            <strong>{status.deals_rows}</strong>
          </div>

          <div className="telemetry-metric">
            <BriefingIcon size={14} />
            <span>Work Orders:</span>
            <strong>{status.work_orders_rows}</strong>
          </div>

          {dao && (
            <div className="telemetry-metric">
              <ClockIcon size={14} />
              <span>As of:</span>
              <strong>{dao}</strong>
            </div>
          )}

          <span className={`status-pill ${aiLeft > 5 ? 'pill-ok' : aiLeft > 0 ? 'pill-warn' : 'pill-error'}`}>
            <KeyIcon size={12} /> AI Quota: {aiLeft} left
          </span>

          {status.degraded && (
            <span className="status-pill pill-warn">
              <ShieldIcon size={12} /> Degraded Engine
            </span>
          )}

          <span className="telemetry-toggle-hint">
            {expanded ? '▲ Hide Data Audit' : '▼ Audit Details'}
          </span>
        </div>

        {expanded && (
          <div className="audit-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="audit-header">
              <span><ShieldIcon size={14} /> Python Data Quality & Normalization Audit</span>
              <span style={{ fontSize: '0.74rem', color: 'var(--claude-text-tertiary)' }}>
                Cleaned deterministically before reaching LLM
              </span>
            </div>

            <div className="audit-columns">
              <div className="audit-col">
                <div className="audit-col-title">Deals Board Quality Rules</div>
                <ul>
                  {status.quality_lines
                    ?.filter((l) => l.toLowerCase().includes('deal') || l.toLowerCase().includes('board: deals') || l.toLowerCase().includes('junk') || l.toLowerCase().includes('duplicate'))
                    .map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                </ul>
              </div>

              <div className="audit-col">
                <div className="audit-col-title">Work Orders Board Rules</div>
                <ul>
                  {status.quality_lines
                    ?.filter((l) => l.toLowerCase().includes('order') || l.toLowerCase().includes('work_order') || l.toLowerCase().includes('billed') || l.toLowerCase().includes('column'))
                    .map((line, i) => (
                      <li key={i}>{line}</li>
                    ))}
                </ul>
              </div>
            </div>

            {status.warnings && status.warnings.length > 0 && (
              <div className="audit-warnings">
                <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                  <WarningIcon size={13} /> Ingestion Caveats
                </div>
                <ul>
                  {status.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
