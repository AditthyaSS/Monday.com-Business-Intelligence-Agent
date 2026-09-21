import React, { useEffect } from 'react'
import { GuideIcon } from './Icons.jsx'

export const INSIGHT_CATEGORIES = [
  {
    id: 'cross-board',
    title: 'Cross-Board Intelligence',
    icon: '🔗',
    description: 'Deals ∩ Work Orders dual-board correlations',
    items: [
      {
        label: 'Pipeline + operational delivery risk',
        question: 'Which sectors have both a large sales pipeline and operational delivery risk?',
      },
      {
        label: 'Sales exposure + execution risk',
        question: 'Where are sales exposure and execution risk overlapping?',
      },
      {
        label: 'Sector comparisons across boards',
        question: 'Compare Mining and Renewables across deals and work orders.',
      },
      {
        label: 'Cross-board risk',
        question: 'Where are our biggest combined commercial and operational risks?',
      },
      {
        label: 'Sales and operations overlap',
        question: 'Where do pipeline concentration and operational problems overlap?',
      },
    ],
  },
  {
    id: 'commercial',
    title: 'Commercial / Sales',
    icon: '💰',
    description: 'Deals board pipeline, owners, and conversion',
    items: [
      {
        label: 'Open pipeline',
        question: "How's our open pipeline looking overall?",
      },
      {
        label: 'Pipeline by sector',
        question: 'Show me active pipeline by sector.',
      },
      {
        label: 'Largest open deals',
        question: 'Where is most of our potential revenue right now?',
      },
      {
        label: 'Owner pipeline',
        question: 'Who owns the most valuable open deals?',
      },
      {
        label: 'Win rate',
        question: 'Which sector has the highest win rate?',
      },
      {
        label: 'Pipeline concentration',
        question: 'How concentrated is our open sales pipeline?',
      },
    ],
  },
  {
    id: 'operations',
    title: 'Operations',
    icon: '⚙️',
    description: 'Work Orders board financials, billing, and fulfillment',
    items: [
      {
        label: 'Work-order performance',
        question: 'How are our work orders doing?',
      },
      {
        label: 'Delayed work orders',
        question: 'Which work orders are delayed past their end date?',
      },
      {
        label: 'Billed vs collected',
        question: 'How much have we billed versus collected?',
      },
      {
        label: 'Receivables',
        question: 'How much is currently tied up in receivables?',
      },
      {
        label: 'Still-to-bill',
        question: 'How much is still to be billed on active orders?',
      },
      {
        label: 'Operational anomalies',
        question: 'Are there any billing anomalies or over-billed orders?',
      },
    ],
  },
  {
    id: 'leadership',
    title: 'Leadership',
    icon: '🎯',
    description: 'Executive snapshot, exposures, and data trust',
    items: [
      {
        label: 'Executive snapshot',
        question: 'Give me an executive leadership snapshot.',
      },
      {
        label: 'Biggest risks',
        question: 'Which deals should leadership worry about right now?',
      },
      {
        label: 'Biggest opportunities',
        question: 'What are our biggest commercial opportunities right now?',
      },
      {
        label: 'Leadership briefing',
        question: 'Prepare a comprehensive leadership briefing.',
      },
      {
        label: 'Data trust / quality',
        question: 'Can I trust the current data from Monday.com?',
      },
    ],
  },
  {
    id: 'trends',
    title: 'Time / Trends',
    icon: '📈',
    description: 'Recent changes and quarter-over-quarter analysis',
    items: [
      {
        label: 'Recent changes',
        question: 'What changed recently in our business?',
      },
      {
        label: 'Quarter comparisons',
        question: 'How does this quarter compare to last quarter?',
      },
      {
        label: 'Period-based analysis',
        question: 'How is our pipeline pacing across recent periods?',
      },
      {
        label: 'Recent pipeline movement',
        question: 'How has our pipeline grown recently?',
      },
    ],
  },
]

export function ExploreInsightsModal({ isOpen, onClose, onSelectInsight }) {
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div className="modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="modal-panel explore-insights-modal-panel"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="explore-insights-title"
      >
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon"><GuideIcon size={18} /></span>
            <div>
              <h2 className="modal-title" id="explore-insights-title">Explore Insights</h2>
              <p className="explore-insights-subtitle">
                Select a topic to load the question into chat. These are discovery starters across all five capability areas.
              </p>
            </div>
          </div>
          <button
            className="btn-modal-close"
            onClick={onClose}
            aria-label="Close explore insights"
          >
            ✕
          </button>
        </div>

        <div className="modal-body explore-insights-body">
          <div className="explore-grid">
            {INSIGHT_CATEGORIES.map((cat) => (
              <div key={cat.id} className="explore-category-card">
                <div className="explore-category-header">
                  <span className="explore-category-icon" aria-hidden="true">{cat.icon}</span>
                  <div>
                    <h3 className="explore-category-title">{cat.title}</h3>
                    <span className="explore-category-desc">{cat.description}</span>
                  </div>
                </div>

                <div className="explore-items-list" role="list">
                  {cat.items.map((item, idx) => (
                    <button
                      key={idx}
                      className="explore-item-btn"
                      onClick={() => onSelectInsight(item.question)}
                      title={`Load: "${item.question}"`}
                      type="button"
                    >
                      <span className="explore-item-bullet">•</span>
                      <span className="explore-item-label">{item.label}</span>
                      <span className="explore-item-arrow" aria-hidden="true">→</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="modal-footer explore-insights-footer">
          <div className="explore-footer-note">
            <span>💡 You can ask any arbitrary natural-language business question. These are starting points.</span>
          </div>
          <button className="btn-modal-secondary" onClick={onClose} type="button">
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
