import { useEffect, useRef } from 'react'

export function usePolling(enabled: boolean, intervalMs: number, tick: () => void) {
  const tickRef = useRef(tick)
  tickRef.current = tick

  useEffect(() => {
    if (!enabled) return
    const id = window.setInterval(() => tickRef.current(), intervalMs)
    return () => window.clearInterval(id)
  }, [enabled, intervalMs])
}
