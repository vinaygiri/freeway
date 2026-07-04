/**
 * @file web/src/hooks/useRecommend.js
 * @description Smart Recommend hook for M3 Web parity. Owns the 10 second
 * analysis phase and calls `/api/recommend`, which uses the shared TUI scoring
 * engine in `src/core/utils.js`.
 *
 * @functions useRecommend → run/cancel recommendation analysis
 * @exports useRecommend
 */
import { useCallback, useEffect, useRef, useState } from 'react'

export function useRecommend({ onToast } = {}) {
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [results, setResults] = useState([])
  const [error, setError] = useState(null)
  const timerRef = useRef(null)

  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current) }, [])

  const recommend = useCallback(async (answers) => {
    if (timerRef.current) clearInterval(timerRef.current)
    setLoading(true)
    setProgress(0)
    setResults([])
    setError(null)

    const started = Date.now()
    timerRef.current = setInterval(() => {
      const pct = Math.min(98, Math.round(((Date.now() - started) / 10_000) * 100))
      setProgress(pct)
    }, 250)

    try {
      await new Promise((resolve) => setTimeout(resolve, 10_000))
      const resp = await fetch('/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers }),
      })
      const payload = await resp.json().catch(() => ({}))
      if (!resp.ok) throw new Error(payload.error || `HTTP ${resp.status}`)
      setResults(Array.isArray(payload.top3) ? payload.top3 : [])
      setProgress(100)
      return { ok: true, top3: payload.top3 || [] }
    } catch (err) {
      setError(err.message)
      onToast?.(`Recommend failed: ${err.message}`, 'error')
      return { ok: false, error: err.message }
    } finally {
      if (timerRef.current) clearInterval(timerRef.current)
      timerRef.current = null
      setLoading(false)
    }
  }, [onToast])

  const reset = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = null
    setLoading(false)
    setProgress(0)
    setResults([])
    setError(null)
  }, [])

  return { recommend, loading, progress, results, error, reset }
}
