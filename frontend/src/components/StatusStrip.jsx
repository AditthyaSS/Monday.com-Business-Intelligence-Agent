import React, { useState, useEffect } from 'react'

export function StatusStrip({ status, loading, error }) {
  const [expanded, setExpanded] = useState(false)

  if (loading) {
    return <div className="status-strip">Loading data status…</div>
  }
  if (error) {
    return <div className="status-strip" style={{color:'var(--color-error)'}}>⚠ {error}</div>
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
    <>
      {isStale && (
        <div className="stale-banner">
          ⚠ Data may be stale — last seen around {dao || 'unknown'}.
          Fetch is limited by Monday.com API quota.
        </div>
      )}
      <div
        className="status-strip"
        onClick={() => setExpanded(e => !e)}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-label="Data status — click to expand"
        onKeyDown={e => e.key === 'Enter' && setExpanded(e => !e)}
      >
        <div className="status-row">
          <span>📊 <strong>{status.deals_rows}</strong> deals &nbsp;|&nbsp; <strong>{status.work_orders_rows}</strong> work orders</span>
          {dao && <span>Data as of: <strong>{dao}</strong></span>}
          <span>
            <span className={`status-pill ${aiLeft > 0 ? 'pill-ok' : 'pill-error'}`}>
              AI answers left today: {aiLeft}
            </span>
          </span>
          {status.degraded && <span className="status-pill pill-warn">⚡ Degraded mode</span>}
          {status.stale_cache && <span className="status-pill pill-warn">📦 Cached data</span>}
          <span style={{marginLeft:'auto',fontSize:'0.75rem',color:'var(--color-text-muted)'}}>
            {expanded ? '▲' : '▼'}
          </span>
        </div>
        {expanded && (status.quality_lines?.length > 0 || status.warnings?.length > 0) && (
          <div className="status-details" onClick={e => e.stopPropagation()}>
            {status.quality_lines?.length > 0 && (
              <>
                <strong>Data quality:</strong>
                <ul>{status.quality_lines.map((l, i) => <li key={i}>{l}</li>)}</ul>
              </>
            )}
            {status.warnings?.length > 0 && (
              <>
                <strong>Warnings:</strong>
                <ul>{status.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
              </>
            )}
          </div>
        )}
      </div>
    </>
  )
}
