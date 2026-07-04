/**
 * @file web/src/hooks/useUpdateChecker.js
 * @description React hook for the update chip + popover — M2 parity with TUI `Shift+U`.
 * 📖 Polls `/api/version` every 5 minutes (matches the TUI cadence) and exposes
 * 📖 `updateAvailable` (boolean) + `latestVersion` (string) for the header chip.
 * 📖 The chip's "Update now" button calls `/api/update/run` which spawns the
 * 📖 detected package manager in the background; the Web UI just surfaces a
 * 📖 toast and tells the user to restart the dashboard to apply the update.
 *
 * @functions
 *   → useUpdateChecker({ onToast }) — { latestVersion, updateAvailable, runUpdate, checkNow, loading }
 */
import { useCallback, useEffect, useState, useRef } from 'react'

const POLL_INTERVAL_MS = 5 * 60_000

// 📖 Lightweight semver compare: returns 1 if a > b, -1 if a < b, 0 if equal.
function semverCompare(a, b) {
  if (!a || !b) return 0
  const ap = a.replace(/^v/, '').split('.').map(Number)
  const bp = b.replace(/^v/, '').split('.').map(Number)
  for (let i = 0; i < Math.max(ap.length, bp.length); i++) {
    const av = ap[i] || 0
    const bv = bp[i] || 0
    if (bv !== av) return bv - av
  }
  return 0
}

export function useUpdateChecker({ onToast } = {}) {
  const [localVersion, setLocalVersion] = useState(null)
  const [latestVersion, setLatestVersion] = useState(null)
  const [lastReleaseDate, setLastReleaseDate] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const intervalRef = useRef(null)

  const checkNow = useCallback(async () => {
    setLoading(true)
    try {
      const resp = await fetch('/api/version')
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setLocalVersion(data.local ?? null)
      setLatestVersion(data.latest ?? null)
      setLastReleaseDate(data.lastReleaseDate ?? null)
      setError(data.error ?? null)
    } catch (err) {
      setError(err.message || 'update check failed')
    } finally {
      setLoading(false)
    }
  }, [])

  // 📖 Initial check + 5-minute polling. We stop polling on unmount.
  useEffect(() => {
    checkNow()
    intervalRef.current = setInterval(checkNow, POLL_INTERVAL_MS)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [checkNow])

  // 📖 updateAvailable is true when latest > local. A null latest means the
  // 📖 npm registry is unreachable, so we don't surface a chip.
  const updateAvailable = Boolean(latestVersion && localVersion && semverCompare(latestVersion, localVersion) > 0)

  const runUpdate = useCallback(async () => {
    if (!updateAvailable) {
      onToast?.('No update available.', 'info')
      return
    }
    try {
      const resp = await fetch('/api/update/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version: latestVersion }),
      })
      const data = await resp.json().catch(() => ({}))
      if (resp.ok && data?.started) {
        onToast?.(`Update to v${latestVersion} started — restart the dashboard to apply.`, 'success')
      } else {
        onToast?.(data?.error || data?.message || 'Update failed', 'error')
      }
    } catch (err) {
      onToast?.(err.message || 'Update request failed', 'error')
    }
  }, [updateAvailable, latestVersion, onToast])

  return { localVersion, latestVersion, lastReleaseDate, updateAvailable, checkNow, runUpdate, loading, error }
}
