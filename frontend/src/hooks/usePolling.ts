import { useEffect } from 'react'

export function usePolling(enabled: boolean, intervalMs: number, tick: () => void) {
  useEffect(() => {
    if (!enabled) return
    const id = window.setInterval(tick, intervalMs)
    return () => window.clearInterval(id)
  }, [enabled, intervalMs, tick])
}
