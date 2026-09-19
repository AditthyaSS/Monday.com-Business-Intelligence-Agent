import React from 'react'

/**
 * Claude Hand-Drawn Design System Vector Icons
 * Styled after Claude's signature aesthetic and Icons8 Claude Hand-Drawn pack.
 * Pure vector SVG with organic strokes, zero bitmap images.
 */

// 1. Signature Claude Terracotta Sunburst Logo
export function ClaudeLogo({ size = 28, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Claude Starburst"
    >
      {/* Hand-drawn organic 12-ray terracotta sunburst */}
      <g stroke="#CC5A2B" strokeWidth="2.6" strokeLinecap="round">
        <line x1="20" y1="4" x2="20" y2="12" />
        <line x1="20" y1="28" x2="20" y2="36" />
        <line x1="4" y1="20" x2="12" y2="20" />
        <line x1="28" y1="20" x2="36" y2="20" />
        <line x1="8.7" y1="8.7" x2="14.3" y2="14.3" />
        <line x1="25.7" y1="25.7" x2="31.3" y2="31.3" />
        <line x1="8.7" y1="31.3" x2="14.3" y2="25.7" />
        <line x1="25.7" y1="14.3" x2="31.3" y2="8.7" />
        <line x1="12.5" y1="5.5" x2="15.8" y2="13.2" />
        <line x1="24.2" y1="26.8" x2="27.5" y2="34.5" />
        <line x1="5.5" y1="27.5" x2="13.2" y2="24.2" />
        <line x1="26.8" y1="15.8" x2="34.5" y2="12.5" />
      </g>
      <circle cx="20" cy="20" r="3.2" fill="#CC5A2B" />
    </svg>
  )
}

// 2. Assistant Message Avatar (Claude Hand-Drawn Sunburst on Warm Canvas)
export function AgentAvatar({ size = 30 }) {
  return (
    <div
      className="claude-agent-avatar"
      style={{
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 8,
        background: '#FAF6F0',
        border: '1px solid rgba(204, 90, 43, 0.2)',
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
      }}
    >
      <ClaudeLogo size={size * 0.75} />
    </div>
  )
}

// 3. User Avatar (Minimalist Hand-Drawn Silhouette)
export function UserAvatar({ size = 30 }) {
  return (
    <div
      className="claude-user-avatar"
      style={{
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: 8,
        background: '#ECEAE4',
        border: '1px solid rgba(0,0,0,0.06)',
      }}
    >
      <svg width={size * 0.65} height={size * 0.65} viewBox="0 0 24 24" fill="none" stroke="#5C5850" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="7" r="4" />
        <path d="M5.5 21C5.5 17.41 8.41 14.5 12 14.5C15.59 14.5 18.5 17.41 18.5 21" />
      </svg>
    </div>
  )
}

// 4. Hand-Drawn Quick Action Icons (matching Claude's bottom chip pills)
export function HandDrawnWrite({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20H21" />
      <path d="M16.5 3.5C17.3284 2.67157 18.6716 2.67157 19.5 3.5C20.3284 4.32843 20.3284 5.67157 19.5 6.5L7 19L3 20L4 16L16.5 3.5Z" />
    </svg>
  )
}

export function HandDrawnLearn({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 10L12 5L2 10L12 15L22 10Z" />
      <path d="M6 12.5V17.5C6 17.5 8 20 12 20C16 20 18 17.5 18 17.5V12.5" />
      <path d="M22 10V16" />
    </svg>
  )
}

export function HandDrawnCode({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="16 18 22 12 16 6" />
      <polyline points="8 6 2 12 8 18" />
    </svg>
  )
}

export function HandDrawnCoffee({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8H19C20.6569 8 22 9.34315 22 11C22 12.6569 20.6569 14 19 14H18" />
      <path d="M2 8H18V17C18 19.2091 16.2091 21 14 21H6C3.79086 21 2 19.2091 2 17V8Z" />
      <line x1="6" y1="2" x2="6" y2="5" />
      <line x1="10" y1="2" x2="10" y2="5" />
      <line x1="14" y1="2" x2="14" y2="5" />
    </svg>
  )
}

export function HandDrawnBulb({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18H15" />
      <path d="M10 22H14" />
      <path d="M12 2C8.13401 2 5 5.13401 5 9C5 11.38 6.19 13.47 8 14.74V17H16V14.74C17.81 13.47 19 11.38 19 9C19 5.13401 15.866 2 12 2Z" />
    </svg>
  )
}

export function HandDrawnPlus({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  )
}

export function HandDrawnMic({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2C10.3431 2 9 3.34315 9 5V12C9 13.6569 10.3431 15 12 15C13.6569 15 15 13.6569 15 12V5C15 3.34315 13.6569 2 12 2Z" />
      <path d="M19 10V12C19 15.866 15.866 19 12 19C8.13401 19 5 15.866 5 12V10" />
      <line x1="12" y1="19" x2="12" y2="22" />
    </svg>
  )
}

export function HandDrawnWaveform({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <line x1="3" y1="12" x2="3" y2="12.01" strokeWidth="2.5" />
      <line x1="7" y1="9" x2="7" y2="15" />
      <line x1="11" y1="5" x2="11" y2="19" />
      <line x1="15" y1="8" x2="15" y2="16" />
      <line x1="19" y1="10" x2="19" y2="14" />
    </svg>
  )
}

export function HandDrawnSend({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="19" x2="12" y2="5" />
      <polyline points="5 12 12 5 19 12" />
    </svg>
  )
}

export function HandDrawnSidebar({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  )
}
