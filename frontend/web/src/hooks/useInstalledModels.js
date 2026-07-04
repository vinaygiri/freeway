/**
 * @file web/src/hooks/useInstalledModels.js
 * @description Hook for Installed Models — scans tool configs and soft-deletes models.
 * 📖 M4: Fetches /api/installed-models, provides disable(action) for soft-delete.
 *
 * @functions useInstalledModels → { results, loading, refresh, disableModel }
 */
import { useState, useEffect, useCallback } from 'react'

export function useInstalledModels() {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const resp = await fetch('/api/installed-models')
      const data = await resp.json()
      setResults(data.results || [])
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  const disableModel = useCallback(async (toolMode, modelId) => {
    const resp = await fetch(`/api/installed-models/${encodeURIComponent(toolMode)}/${encodeURIComponent(modelId)}/disable`, {
      method: 'POST',
    })
    const result = await resp.json()
    if (result.success) {
      // 📖 Refresh after successful delete
      await refresh()
    }
    return result
  }, [refresh])

  return { results, loading, refresh, disableModel }
}
