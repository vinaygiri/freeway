/**
 * @file web/src/hooks/useChangelog.js
 * @description React hook for the changelog data — M2 parity with the TUI's `N` key overlay.
 * 📖 Loads `/api/changelog` once on mount, exposes the parsed { versions } map,
 * 📖 and provides helpers for the index/details two-phase modal.
 *
 * @functions
 *   → useChangelog() — { versions, sortedVersions, getVersion, loading, error, refresh }
 */
import { useEffect, useMemo, useState, useCallback } from 'react'

export function useChangelog() {
  const [versions, setVersions] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const resp = await fetch('/api/changelog')
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const data = await resp.json()
      setVersions(data?.versions ?? {})
      setError(null)
    } catch (err) {
      setError(err.message || 'Failed to load changelog')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  // 📖 Sort versions in descending semver order. We do a string-based compare
  // 📖 on the dotted tuples so '0.10.0' > '0.9.0' works correctly.
  const sortedVersions = useMemo(() => {
    return Object.keys(versions).sort((a, b) => {
      const ap = a.split('.').map(Number)
      const bp = b.split('.').map(Number)
      for (let i = 0; i < Math.max(ap.length, bp.length); i++) {
        const av = ap[i] || 0
        const bv = bp[i] || 0
        if (bv !== av) return bv - av
      }
      return 0
    })
  }, [versions])

  const getVersion = useCallback((v) => versions[v] ?? null, [versions])

  return { versions, sortedVersions, getVersion, loading, error, refresh }
}
