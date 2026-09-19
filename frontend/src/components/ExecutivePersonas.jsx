import React from 'react'

/**
 * Skylark BI Agent — Executive Personas
 * Hand-Drawn Character System inspired by Icons8 Claude Hand-Drawn style.
 * 100% vector SVG with charming organic ink strokes. Zero bitmap images, zero emojis.
 */

// 1. The Pathfinder — Visionary Founder
export function PathfinderAvatar({ size = 36, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Soft warm background circle */}
      <circle cx="24" cy="24" r="22" fill="#FBF8F2" stroke="#E6E0D5" strokeWidth="1.5" />

      {/* Founder hair swoop */}
      <path
        d="M15 19C15 13 19 9 25 9C31 9 34 13 33 18C33 19 32 20 31 20C29 15 25 13 20 15C17 16 16 18 15 19Z"
        fill="#2B2925"
      />

      {/* Head oval */}
      <circle cx="24" cy="21" r="9" fill="#FFFDF9" stroke="#2B2925" strokeWidth="2" />

      {/* Signature Round Glasses */}
      <circle cx="21" cy="20" r="3.2" stroke="#CC5A2B" strokeWidth="1.8" fill="none" />
      <circle cx="27" cy="20" r="3.2" stroke="#CC5A2B" strokeWidth="1.8" fill="none" />
      <line x1="24.2" y1="20" x2="23.8" y2="20" stroke="#CC5A2B" strokeWidth="1.8" />

      {/* Eyes inside glasses */}
      <circle cx="21" cy="20" r="1" fill="#2B2925" />
      <circle cx="27" cy="20" r="1" fill="#2B2925" />

      {/* Thoughtful warm smile */}
      <path d="M22 25C23 26 25 26 26 25" stroke="#2B2925" strokeWidth="1.6" strokeLinecap="round" />

      {/* Executive Notch Collar & Coat */}
      <path
        d="M13 41C13 33 17 30 24 30C31 30 35 33 35 41"
        stroke="#2B2925"
        strokeWidth="2"
        strokeLinecap="round"
      />
      {/* Terracotta necktie / lapel */}
      <path d="M24 30L22.5 38L24 40L25.5 38L24 30Z" fill="#CC5A2B" stroke="#9A3412" strokeWidth="1.2" />
    </svg>
  )
}

// 2. Eagle Eye — Chief Flight Commander
export function SkyCommanderAvatar({ size = 36, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="24" cy="24" r="22" fill="#F5F8FA" stroke="#DCE5EB" strokeWidth="1.5" />

      {/* Aviator flight helmet */}
      <path
        d="M14 21C14 14 18 10 24 10C30 10 34 14 34 21C34 22 34 25 33 27L15 27C14 25 14 22 14 21Z"
        fill="#3D4A54"
      />

      {/* Aviator goggles on forehead */}
      <rect x="17" y="14" width="6.5" height="4.5" rx="2" stroke="#CC5A2B" strokeWidth="1.8" fill="#FAF9F5" />
      <rect x="24.5" y="14" width="6.5" height="4.5" rx="2" stroke="#CC5A2B" strokeWidth="1.8" fill="#FAF9F5" />
      <line x1="23.5" y1="16" x2="24.5" y2="16" stroke="#CC5A2B" strokeWidth="2" />
      <line x1="14" y1="16" x2="17" y2="16" stroke="#CC5A2B" strokeWidth="1.5" strokeDasharray="1 1" />
      <line x1="31" y1="16" x2="34" y2="16" stroke="#CC5A2B" strokeWidth="1.5" strokeDasharray="1 1" />

      {/* Face */}
      <path d="M16 25C16 30 19 32 24 32C29 32 32 30 32 25" stroke="#2B2925" strokeWidth="2" fill="#FFFDF9" />
      <circle cx="20.5" cy="24" r="1.2" fill="#2B2925" />
      <circle cx="27.5" cy="24" r="1.2" fill="#2B2925" />
      <path d="M22.5 28C23.5 28.8 24.5 28.8 25.5 28" stroke="#2B2925" strokeWidth="1.6" strokeLinecap="round" />

      {/* Flight jacket & wing collar */}
      <path d="M12 41C12 34 17 33 24 33C31 33 36 34 36 41" stroke="#2B2925" strokeWidth="2" strokeLinecap="round" />
      <path d="M19 33L24 37L29 33" stroke="#CC5A2B" strokeWidth="1.8" />
    </svg>
  )
}

// 3. Deal Maestro — Revenue & Growth Lead
export function DealMaestroAvatar({ size = 36, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="24" cy="24" r="22" fill="#FDF7F4" stroke="#F6DCD1" strokeWidth="1.5" />

      {/* Slick hair */}
      <path d="M15 17C16 11 21 9 27 9C32 9 34 12 34 16C30 14 26 14 21 16L15 17Z" fill="#2B2925" />

      {/* Head */}
      <circle cx="24" cy="21" r="8.5" fill="#FFFDF9" stroke="#2B2925" strokeWidth="2" />

      {/* Confident eyes & brows */}
      <path d="M19 18L22 17.5" stroke="#2B2925" strokeWidth="1.4" strokeLinecap="round" />
      <path d="M26 17.5L29 18" stroke="#2B2925" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="20.5" cy="20.5" r="1.2" fill="#2B2925" />
      <circle cx="27.5" cy="20.5" r="1.2" fill="#2B2925" />

      {/* Confident wry smile */}
      <path d="M22 25C23.5 26 25.5 25.5 27 24.5" stroke="#2B2925" strokeWidth="1.6" strokeLinecap="round" />

      {/* Sharp lapel suit */}
      <path d="M13 41C13 33 17 30 24 30C31 30 35 33 35 41" stroke="#2B2925" strokeWidth="2" strokeLinecap="round" />
      {/* V-neck lapel lines */}
      <path d="M19 30L24 37L29 30" stroke="#CC5A2B" strokeWidth="1.8" />

      {/* Hand holding warm takeaway espresso cup */}
      <rect x="31" y="32" width="6" height="8" rx="1.5" fill="#FFFDF9" stroke="#CC5A2B" strokeWidth="1.5" />
      <line x1="31" y1="34" x2="37" y2="34" stroke="#CC5A2B" strokeWidth="1.2" />
      <path d="M33 29C34 28 35 29 35 27" stroke="#CC5A2B" strokeWidth="1" strokeLinecap="round" />
    </svg>
  )
}

// 4. Terrain Whisperer — Lead Geo-Scientist
export function TerrainWhispererAvatar({ size = 36, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="24" cy="24" r="22" fill="#F4F8F4" stroke="#DAEBD9" strokeWidth="1.5" />

      {/* Explorer beanie / field cap */}
      <path d="M15 19C15 13 18 10 24 10C30 10 33 13 33 19L15 19Z" fill="#3D5A43" />
      <line x1="13" y1="19" x2="35" y2="19" stroke="#2B2925" strokeWidth="2" strokeLinecap="round" />

      {/* Head */}
      <path d="M16 20C16 27 19 30 24 30C29 30 32 27 32 20" stroke="#2B2925" strokeWidth="2" fill="#FFFDF9" />

      {/* Surveyor Monocle / Loupe on right eye */}
      <circle cx="27" cy="23" r="3.5" stroke="#CC5A2B" strokeWidth="1.8" fill="none" />
      <line x1="30.5" y1="24.5" x2="33" y2="28" stroke="#CC5A2B" strokeWidth="1.5" />
      <circle cx="27" cy="23" r="1.2" fill="#2B2925" />
      <circle cx="20.5" cy="23" r="1.2" fill="#2B2925" />

      {/* Curious smile */}
      <path d="M22 27C23 28 25 28 26 27" stroke="#2B2925" strokeWidth="1.6" strokeLinecap="round" />

      {/* Field parka & compass badge */}
      <path d="M13 41C13 33 17 31 24 31C31 31 35 33 35 41" stroke="#2B2925" strokeWidth="2" strokeLinecap="round" />
      <circle cx="20" cy="36" r="2.2" stroke="#CC5A2B" strokeWidth="1.2" fill="#FFFDF9" />
    </svg>
  )
}

// 5. Sensor Wizard — Autopilot Architect
export function SensorWizardAvatar({ size = 36, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="24" cy="24" r="22" fill="#F8F6FD" stroke="#E8E2F7" strokeWidth="1.5" />

      {/* Techie messy curls */}
      <path d="M14 18C14 11 18 8 24 8C30 8 34 11 34 18C32 17 29 16 26 17C23 15 19 16 14 18Z" fill="#2B2925" />

      {/* Lightweight tech headset band */}
      <path d="M14 20C14 13 18 11 24 11C30 11 34 13 34 20" stroke="#CC5A2B" strokeWidth="2" fill="none" />
      <rect x="12" y="19" width="3.5" height="6" rx="1.5" fill="#CC5A2B" />
      <rect x="32.5" y="19" width="3.5" height="6" rx="1.5" fill="#CC5A2B" />
      {/* Boom mic pointing to mouth */}
      <path d="M33 24L31 28L27 28" stroke="#CC5A2B" strokeWidth="1.5" strokeLinecap="round" />

      {/* Head */}
      <circle cx="24" cy="21" r="8.5" fill="#FFFDF9" stroke="#2B2925" strokeWidth="2" />
      <circle cx="20" cy="20.5" r="1.2" fill="#2B2925" />
      <circle cx="26.5" cy="20.5" r="1.2" fill="#2B2925" />
      <path d="M22 25C23 26 25 26 26 25" stroke="#2B2925" strokeWidth="1.6" strokeLinecap="round" />

      {/* Tech hoodie & propeller pin */}
      <path d="M13 41C13 33 17 31 24 31C31 31 35 33 35 41" stroke="#2B2925" strokeWidth="2" strokeLinecap="round" />
      <line x1="24" y1="31" x2="24" y2="41" stroke="#CC5A2B" strokeWidth="1.5" />
    </svg>
  )
}

// 6. Pit Surveyor — Mining & Infrastructure Lead
export function PitSurveyorAvatar({ size = 36, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <circle cx="24" cy="24" r="22" fill="#FFFBEB" stroke="#FDE68A" strokeWidth="1.5" />

      {/* Safety Hardhat */}
      <path
        d="M13 21C13 14 17 9 24 9C31 9 35 14 35 21L13 21Z"
        fill="#D97706"
        stroke="#92400E"
        strokeWidth="1.8"
      />
      <line x1="11" y1="21" x2="37" y2="21" stroke="#92400E" strokeWidth="2.5" strokeLinecap="round" />

      {/* Headlamp mount */}
      <rect x="21.5" y="12" width="5" height="4" rx="1" fill="#FEF3C7" stroke="#92400E" strokeWidth="1.5" />
      <circle cx="24" cy="14" r="1.2" fill="#CC5A2B" />

      {/* Head */}
      <path d="M16 22C16 28 19 31 24 31C29 31 32 28 32 22" stroke="#2B2925" strokeWidth="2" fill="#FFFDF9" />
      <circle cx="20" cy="24.5" r="1.2" fill="#2B2925" />
      <circle cx="28" cy="24.5" r="1.2" fill="#2B2925" />
      <path d="M22 28C23 29 25 29 26 28" stroke="#2B2925" strokeWidth="1.6" strokeLinecap="round" />

      {/* High-visibility vest & collar */}
      <path d="M13 41C13 33 17 32 24 32C31 32 35 33 35 41" stroke="#2B2925" strokeWidth="2" strokeLinecap="round" />
      <path d="M18 33L19 41" stroke="#D97706" strokeWidth="2.2" />
      <path d="M30 33L29 41" stroke="#D97706" strokeWidth="2.2" />
    </svg>
  )
}

/**
 * Curated list of Creative Personas
 */
export const EXECUTIVE_PERSONAS = [
  {
    id: 'pathfinder',
    name: 'The Pathfinder',
    role: 'Visionary Founder',
    tag: 'Strategic Fleet Vision',
    bio: 'Steers overall enterprise trajectory, capital allocation, and client partnerships.',
    favPrompt: "Prepare a leadership update",
    icon: PathfinderAvatar,
  },
  {
    id: 'sky_commander',
    name: 'Eagle Eye',
    role: 'Chief Flight Commander',
    tag: 'Airspace & Operations',
    bio: 'Monitors flight coverage, mission uptime, and tactical drone deployment.',
    favPrompt: "How's our open pipeline looking overall?",
    icon: SkyCommanderAvatar,
  },
  {
    id: 'deal_maestro',
    name: 'Deal Maestro',
    role: 'Revenue & Growth Lead',
    tag: 'Commercial Pipeline',
    bio: 'Obsessed with deal velocity, contract win rates, and quarterly bookings.',
    favPrompt: "What's our win rate by sector?",
    icon: DealMaestroAvatar,
  },
  {
    id: 'terrain_whisperer',
    name: 'Terrain Whisperer',
    role: 'Lead Geo-Scientist',
    tag: 'Renewables & Topography',
    bio: 'Directs utility corridor inspections, solar farms, and energy survey data.',
    favPrompt: "How's our pipeline looking for the energy sector this quarter?",
    icon: TerrainWhispererAvatar,
  },
  {
    id: 'sensor_wizard',
    name: 'Sensor Wizard',
    role: 'Autopilot Architect',
    tag: 'AI Navigation & LiDAR',
    bio: 'Designs computer-vision pipelines and automated flight payloads.',
    favPrompt: "Prepare a leadership update",
    icon: SensorWizardAvatar,
  },
  {
    id: 'pit_surveyor',
    name: 'Pit Surveyor',
    role: 'Mining & Heavy Industry',
    tag: 'Volumetric & Collections',
    bio: 'Tracks stockpile volumes, excavation work orders, and billing realization.',
    favPrompt: "How much have we billed versus collected on mining work orders?",
    icon: PitSurveyorAvatar,
  },
]

export function getPersona(id) {
  return EXECUTIVE_PERSONAS.find((p) => p.id === id) || EXECUTIVE_PERSONAS[0]
}

export function PersonaAvatar({ id, size = 32, className = '' }) {
  const persona = getPersona(id)
  const IconComponent = persona.icon
  return <IconComponent size={size} className={className} />
}
