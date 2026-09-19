import React from 'react'

/**
 * Skylark BI Agent — Hand-Drawn Design System Vector Icons
 * Styled in the Icons8 Claude Hand-Drawn aesthetic.
 * 100% pure vector SVG with organic strokes. Zero bitmap images, zero emojis.
 */

// 1. Primary Skylark BI Drone Vector Logo
export function SkylarkDroneLogo({ size = 28, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 36 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Skylark Drones BI Logo"
    >
      {/* Central Drone Fuselage */}
      <rect x="12" y="12" width="12" height="12" rx="4" fill="#FAF6F0" stroke="#CC5A2B" strokeWidth="2.2" />
      <circle cx="18" cy="18" r="3" fill="#CC5A2B" />

      {/* Diagonal Rotor Arms */}
      <line x1="7" y1="7" x2="12" y2="12" stroke="#CC5A2B" strokeWidth="2" strokeLinecap="round" />
      <line x1="29" y1="7" x2="24" y2="12" stroke="#CC5A2B" strokeWidth="2" strokeLinecap="round" />
      <line x1="7" y1="29" x2="12" y2="24" stroke="#CC5A2B" strokeWidth="2" strokeLinecap="round" />
      <line x1="29" y1="29" x2="24" y2="24" stroke="#CC5A2B" strokeWidth="2" strokeLinecap="round" />

      {/* Hand-Drawn Rotors */}
      <circle cx="6" cy="6" r="3.5" stroke="#9A3412" strokeWidth="1.8" strokeDasharray="3 2" />
      <circle cx="30" cy="6" r="3.5" stroke="#9A3412" strokeWidth="1.8" strokeDasharray="3 2" />
      <circle cx="6" cy="30" r="3.5" stroke="#9A3412" strokeWidth="1.8" strokeDasharray="3 2" />
      <circle cx="30" cy="30" r="3.5" stroke="#9A3412" strokeWidth="1.8" strokeDasharray="3 2" />
    </svg>
  )
}

// 2. Chatbot Assistant Avatar Icon
export function SkylarkChatbotIcon({ size = 26, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <rect x="5" y="8" width="22" height="18" rx="6" fill="#FDF8F3" stroke="#CC5A2B" strokeWidth="2" />
      {/* Friendly Eyes */}
      <circle cx="11.5" cy="16" r="2.2" fill="#CC5A2B" />
      <circle cx="20.5" cy="16" r="2.2" fill="#CC5A2B" />
      {/* Happy Smile Arc */}
      <path d="M12 21C13.5 22.5 18.5 22.5 20 21" stroke="#CC5A2B" strokeWidth="1.8" strokeLinecap="round" />
      {/* Antenna with Signal Spark */}
      <line x1="16" y1="8" x2="16" y2="3" stroke="#CC5A2B" strokeWidth="2" strokeLinecap="round" />
      <circle cx="16" cy="2.5" r="1.8" fill="#E65100" />
      {/* Ear nodes */}
      <rect x="2" y="14" width="3" height="6" rx="1.5" fill="#CC5A2B" />
      <rect x="27" y="14" width="3" height="6" rx="1.5" fill="#CC5A2B" />
    </svg>
  )
}

// 3. Founder Executive Profile Icon
export function FounderIcon({ size = 24, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="14" cy="9" r="5" stroke="#3D3A34" strokeWidth="2" fill="#ECE9DF" />
      <path
        d="M5 24C5 18.5 9 16 14 16C19 16 23 18.5 23 24"
        stroke="#3D3A34"
        strokeWidth="2"
        strokeLinecap="round"
      />
      {/* Executive tie / lapel accent */}
      <path d="M14 17L13 22H15L14 17Z" fill="#CC5A2B" />
    </svg>
  )
}

// 4. Domain Specific Hand-Drawn Category Icons
export function PipelineIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3V21H21" />
      <path d="M7 17L11 11L15 14L21 6" />
      <circle cx="21" cy="6" r="1.5" fill="currentColor" />
    </svg>
  )
}

export function EnergyIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  )
}

export function WinRateIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="5" />
      <circle cx="12" cy="12" r="1.5" fill="currentColor" />
    </svg>
  )
}

export function RevenueIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M9 7H15" />
      <path d="M9 11H14" />
      <path d="M9 7C12 7 13 9 13 11C13 13 11 14 9 14L15 18" />
    </svg>
  )
}

export function BriefingIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 4H19C19.5523 4 20 4.44772 20 5V20C20 20.5523 19.5523 21 19 21H5C4.44772 21 4 20.5523 4 20V5C4 4.44772 4.44772 4 5 4H8" />
      <rect x="8" y="2" width="8" height="4" rx="1.5" />
      <line x1="8" y1="10" x2="16" y2="10" />
      <line x1="8" y1="14" x2="14" y2="14" />
    </svg>
  )
}

// 5. System UI Icons
export function GearIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

export function KeyIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 2L15 8" />
      <circle cx="8" cy="15" r="5" />
      <line x1="16" y1="7" x2="19" y2="10" />
      <line x1="18.5" y1="4.5" x2="21.5" y2="7.5" />
    </svg>
  )
}

export function GuideIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" />
      <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

export function DatabaseIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="5" rx="9" ry="3" />
      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
    </svg>
  )
}

export function ClockIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <polyline points="12 7 12 12 15 14" />
    </svg>
  )
}

export function ShieldIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  )
}

export function WarningIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

export function CopyIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  )
}

export function CheckIcon({ size = 15 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12" />
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
      <line x1="4" y1="12" x2="4" y2="12.01" strokeWidth="2.5" />
      <line x1="8" y1="9" x2="8" y2="15" />
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="16" y1="8" x2="16" y2="16" />
      <line x1="20" y1="10" x2="20" y2="14" />
    </svg>
  )
}

export function HandDrawnSend({ size = 16 }) {
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
