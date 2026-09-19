import React, { useEffect, useRef } from 'react'
import lottie from 'lottie-web'

export function LottiePlayer({
  animationData,
  width = 120,
  height = 120,
  loop = true,
  autoplay = true,
  className = '',
}) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current || !animationData) return

    const anim = lottie.loadAnimation({
      container: containerRef.current,
      renderer: 'svg',
      loop,
      autoplay,
      animationData,
    })

    return () => {
      anim.destroy()
    }
  }, [animationData, loop, autoplay])

  return (
    <div
      ref={containerRef}
      style={{ width, height, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      className={className}
    />
  )
}
