import React from 'react'

/**
 * Safe text formatter: converts markdown-lite to React nodes.
 * NO dangerouslySetInnerHTML. Handles paragraphs, bullet lists, **bold**.
 */
export function SafeText({ text }) {
  if (!text) return null

  // Split into paragraphs/blocks
  const blocks = text.split(/\n\n+/)

  return (
    <div className="msg-text">
      {blocks.map((block, bi) => {
        const lines = block.split('\n')
        const isList = lines.every(l => l.match(/^[-*•]\s/) || l.trim() === '')
        if (isList) {
          return (
            <ul key={bi} className="msg-ul">
              {lines.filter(l => l.trim()).map((l, li) => (
                <li key={li}><InlineFormat text={l.replace(/^[-*•]\s+/, '')} /></li>
              ))}
            </ul>
          )
        }
        // Check if block has any list lines mixed in
        const hasList = lines.some(l => l.match(/^[-*•]\s/))
        if (hasList) {
          return (
            <div key={bi} className="msg-para">
              {lines.map((l, li) => {
                if (l.match(/^[-*•]\s/)) {
                  return <div key={li}>• <InlineFormat text={l.replace(/^[-*•]\s+/, '')} /></div>
                }
                return l.trim() ? <div key={li}><InlineFormat text={l} /></div> : null
              })}
            </div>
          )
        }
        return (
          <p key={bi} className="msg-para">
            <InlineFormat text={block} />
          </p>
        )
      })}
    </div>
  )
}

/** Handle **bold** inline */
function InlineFormat({ text }) {
  const parts = text.split(/(\*\*[^*]+\*\*)/)
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith('**') && p.endsWith('**')) {
          return <strong key={i}>{p.slice(2, -2)}</strong>
        }
        return <span key={i}>{p}</span>
      })}
    </>
  )
}
