/**
 * @file web/src/hooks/useRequestInspector.js
 * @description Hook for the Request Inspector — polls the Freeway proxy's recent
 * routing decisions via the web server's /api/proxy/requests pass-through.
 * 📖 M6b: glass-box view of what was asked, where it routed and why.
 *
 * @functions useRequestInspector → { enabled, requests, loading, error, refresh }
 */
import { useCallback, useEffect, useRef, useState } from 'react'

const POLL_INTERVAL_MS = 5000

export function useRequestInspector() {
  const [enabled, setEnabled] = useState(false)
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  const fetchRequests = useCallback(async () => {
    try {
      const resp = await fetch('/api/proxy/requests')
      const data = await resp.json()
      setEnabled(Boolean(data?.enabled))
      setRequests(Array.isArray(data?.requests) ? data.requests : [])
      setError(data?.error || null)
    } catch (err) {
      setRequests([])
      setError(err?.message || 'Freeway proxy unreachable')
    }
  }, [])

  useEffect(() => {
    let mounted = true
    fetchRequests().then(() => {
      if (mounted) setLoading(false)
    })
    pollRef.current = setInterval(fetchRequests, POLL_INTERVAL_MS)
    return () => {
      mounted = false
      clearInterval(pollRef.current)
    }
  }, [fetchRequests])

  return { enabled, requests, loading, error, refresh: fetchRequests }
}
