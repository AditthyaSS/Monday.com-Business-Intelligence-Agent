import React from 'react'

/**
 * Safe text formatter: converts markdown-lite to React nodes.
 * NO dangerouslySetInnerHTML. Handles paragraphs, lists, bold, inline code, and italics.
 */
export function SafeText({ text }) {
  if (!text) return null

  // Split into paragraphs/blocks
  const blocks = text.split(/\n\n+/)

  return (
    <div className="msg-text">
      {blocks.map((block, bi) => {
        const lines = block.split('\n')
        const isList = lines.every(l => l.match(/^([-*•]|\d+\.)\s/) || l.trim() === '')

        if (isList) {
          return (
            <ul key={bi} className="msg-ul">
              {lines.filter(l => l.trim()).map((l, li) => (
                <li key={li}>
                  <InlineFormat text={l.replace(/^([-*•]|\d+\.)\s+/, '')} />
                </li>
              ))}
            </ul>
          )
        }

        // Check if block has mixed list lines
        const hasList = lines.some(l => l.match(/^([-*•]|\d+\.)\s/))
        if (hasList) {
          return (
            <div key={bi} className="msg-para">
              {lines.map((l, li) => {
                if (l.match(/^[-*•]\s/)) {
                  return (
                    <div key={li} style={{ paddingLeft: 12, margin: '3px 0' }}>
                      <span style={{ color: 'var(--accent-cyan)', marginRight: 6 }}>•</span>
                      <InlineFormat text={l.replace(/^[-*•]\s+/, '')} />
                    </div>
                  )
                }
                if (l.match(/^\d+\.\s/)) {
                  const num = l.match(/^(\d+\.)\s/)[1]
                  return (
                    <div key={li} style={{ paddingLeft: 12, margin: '3px 0' }}>
                      <span style={{ color: 'var(--accent-primary)', fontWeight: 600, marginRight: 6 }}>{num}</span>
                      <InlineFormat text={l.replace(/^\d+\.\s+/, '')} />
                    </div>
                  )
                }
                return l.trim() ? (
                  <div key={li} style={{ margin: '4px 0' }}>
                    <InlineFormat text={l} />
                  </div>
                ) : null
              })}
            </div>
          )
        }

        // Check if line is an alert/note
        if (block.trim().startsWith('⚠️') || block.trim().startsWith('_⚠️')) {
          return (
            <div
              key={bi}
              style={{
                background: 'rgba(245, 158, 11, 0.12)',
                borderLeft: '3px solid #f59e0b',
                borderRadius: '0 8px 8px 0',
                padding: '8px 12px',
                margin: '8px 0',
                color: '#fef3c7',
                fontSize: '0.88rem',
              }}
            >
              <InlineFormat text={block} />
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

/** Handle bold, code, and italic inline tokens safely */
function InlineFormat({ text }) {
  // Tokenize by `code`, **bold**, and _italic_
  const tokens = text.split(/(`[^`]+`|\*\*[^*]+\*\*|_[^_]+_)/)

  return (
    <>
      {tokens.map((token, i) => {
        if (token.startsWith('`') && token.endsWith('`')) {
          return <code key={i}>{token.slice(1, -1)}</code>
        }
        if (token.startsWith('**') && token.endsWith('**')) {
          return <strong key={i}>{token.slice(2, -2)}</strong>
        }
        if (token.startsWith('_') && token.endsWith('_')) {
          return <em key={i} style={{ color: 'var(--text-secondary)' }}>{token.slice(1, -1)}</em>
        }
        return <span key={i}>{token}</span>
      })}
    </>
  )
}
