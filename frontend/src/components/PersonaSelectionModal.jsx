import React, { useState } from 'react'
import { EXECUTIVE_PERSONAS, getPersona } from './ExecutivePersonas.jsx'
import { CheckIcon, FounderIcon, SkylarkDroneLogo } from './Icons.jsx'

export function PersonaSelectionModal({
  isOpen,
  onClose,
  currentPersonaId,
  onSelectPersona,
  isOnboarding = false,
  onLaunchPrompt,
}) {
  const [selectedId, setSelectedId] = useState(currentPersonaId || 'pathfinder')

  if (!isOpen) return null

  const activePersona = getPersona(selectedId)

  const handleConfirm = () => {
    localStorage.setItem('skylark_user_persona', selectedId)
    if (onSelectPersona) onSelectPersona(selectedId)
    onClose()
  }

  const handleConfirmAndRun = () => {
    handleConfirm()
    if (onLaunchPrompt && activePersona.favPrompt) {
      onLaunchPrompt(activePersona.favPrompt)
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel persona-modal-panel" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-wrap">
            <span className="modal-icon">
              <SkylarkDroneLogo size={22} />
            </span>
            <div>
              <h2 className="modal-title">
                {isOnboarding ? 'Welcome to Skylark Intelligence' : 'Executive Command Personas'}
              </h2>
              <p className="modal-subtitle">
                Select your character avatar inspired by Claude hand-drawn ink art
              </p>
            </div>
          </div>
          {!isOnboarding && (
            <button className="btn-modal-close" onClick={onClose} aria-label="Close modal">
              ✕
            </button>
          )}
        </div>

        <div className="modal-body">
          <div className="persona-grid">
            {EXECUTIVE_PERSONAS.map((p) => {
              const isSelected = p.id === selectedId
              const AvatarComp = p.icon
              return (
                <div
                  key={p.id}
                  className={`persona-card ${isSelected ? 'active' : ''}`}
                  onClick={() => setSelectedId(p.id)}
                >
                  <div className="persona-card-top">
                    <div className="persona-avatar-frame">
                      <AvatarComp size={54} />
                    </div>
                    {isSelected && (
                      <span className="persona-selected-badge">
                        <CheckIcon size={12} /> Active
                      </span>
                    )}
                  </div>

                  <div className="persona-card-content">
                    <h3 className="persona-name">{p.name}</h3>
                    <span className="persona-role">{p.role}</span>
                    <p className="persona-bio">{p.bio}</p>
                  </div>

                  <div className="persona-card-footer">
                    <span className="persona-tag">{p.tag}</span>
                  </div>
                </div>
              )
            })}
          </div>

          {activePersona && (
            <div className="persona-preview-callout">
              <div className="preview-left">
                <div className="preview-avatar">
                  <activePersona.icon size={38} />
                </div>
                <div>
                  <div className="preview-title">
                    Configuring session as <strong>{activePersona.name}</strong> ({activePersona.role})
                  </div>
                  <div className="preview-hint">
                    Recommended starter query: <em>"{activePersona.favPrompt}"</em>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <span className="footer-note">
            Character saved locally to your device. Switch anytime from the sidebar.
          </span>
          <div className="footer-right">
            {!isOnboarding && (
              <button className="btn-modal-ghost" onClick={onClose}>
                Cancel
              </button>
            )}
            {isOnboarding && activePersona.favPrompt ? (
              <button className="btn-modal-primary" onClick={handleConfirmAndRun}>
                Select & Launch Analysis →
              </button>
            ) : (
              <button className="btn-modal-primary" onClick={handleConfirm}>
                Confirm Persona
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
