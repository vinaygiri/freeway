/**
 * @file web/src/hooks/useRouterDashboard.js
 * @description Hook for Router Dashboard — polls daemon status, proxies actions.
 * 📖 M4: Provides status, stats, tokens, sets, start/stop, probe-mode control.
 * 📖 Polls /api/router/status every 5s; fetches full stats on demand.
 *
 * @functions useRouterDashboard → { status, stats, tokens, start, stop, setProbeMode, refresh }
 */
import { useState, useEffect, useCallback, useRef } from 'react'

const POLL_INTERVAL_MS = 5000

export function useRouterDashboard() {
  const [status, setStatus] = useState(null)
  const [stats, setStats] = useState(null)
  const [tokens, setTokens] = useState(null)
  const [sets, setSets] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const pollRef = useRef(null)

  const fetchStatus = useCallback(async () => {
    try {
      const resp = await fetch('/api/router/status')
      const data = await resp.json()
      setStatus(data)
      return data
    } catch {
      setStatus({ ok: false, running: false })
      return null
    }
  }, [])

  const fetchStats = useCallback(async () => {
    try {
      const resp = await fetch('/api/router/stats')
      const data = await resp.json()
      if (data.ok) setStats(data)
      return data
    } catch { return null }
  }, [])

  const fetchTokens = useCallback(async () => {
    try {
      const resp = await fetch('/api/router/tokens')
      const data = await resp.json()
      setTokens(data)
      return data
    } catch { return null }
  }, [])

  const fetchSets = useCallback(async () => {
    try {
      const resp = await fetch('/api/router/sets')
      const data = await resp.json()
      setSets(data)
      return data
    } catch { return null }
  }, [])

  // 📖 Poll daemon status + refresh stats when running
  useEffect(() => {
    let mounted = true

    const poll = async () => {
      const s = await fetchStatus()
      if (s?.ok && mounted) {
        await fetchStats()
      }
    }

    poll().then(() => { if (mounted) setLoading(false) })
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS)

    return () => {
      mounted = false
      clearInterval(pollRef.current)
    }
  }, [fetchStatus, fetchStats])

  const start = useCallback(async () => {
    setActionLoading(true)
    try {
      const resp = await fetch('/api/router/start', { method: 'POST' })
      const data = await resp.json()
      await fetchStatus()
      if (data.ok) await fetchStats()
      return data
    } finally { setActionLoading(false) }
  }, [fetchStatus, fetchStats])

  const stop = useCallback(async () => {
    setActionLoading(true)
    try {
      const resp = await fetch('/api/router/stop', { method: 'POST' })
      const data = await resp.json()
      setStatus({ ok: false, running: false })
      setStats(null)
      return data
    } finally { setActionLoading(false) }
  }, [])

  const setProbeMode = useCallback(async (mode) => {
    try {
      await fetch('/api/router/probe-mode', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ probeMode: mode }),
      })
      await fetchStats()
    } catch {}
  }, [fetchStats])

  const refresh = useCallback(async () => {
    setLoading(true)
    await Promise.all([fetchStatus(), fetchTokens(), fetchSets()])
    setLoading(false)
  }, [fetchStatus, fetchTokens, fetchSets])

  const getQuickSetup = useCallback(async () => {
    try {
      const resp = await fetch('/api/router/quick-setup')
      return await resp.json()
    } catch { return null }
  }, [])

  return {
    status, stats, tokens, sets,
    loading, actionLoading,
    start, stop, setProbeMode, refresh,
    fetchTokens, fetchSets, getQuickSetup,
  }
}
