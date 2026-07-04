/**
 * @file web/src/hooks/useTokenUsage.js
 * @description Hook for Token Usage panel — fetches token data from daemon or file.
 * 📖 M4: Returns today's usage, 7-day breakdown, top models, top providers.
 *
 * @functions useTokenUsage → { data, loading, refresh }
 */
import { useState, useEffect, useCallback } from 'react'

export function useTokenUsage() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const resp = await fetch('/api/router/tokens')
      const raw = await resp.json()
      setData(processTokenData(raw))
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  return { data, loading, refresh }
}

function processTokenData(raw) {
  if (!raw) return null

  const daily = raw.daily || {}
  const allTime = raw.all_time || {}

  // 📖 Build 7-day chart data
  const days = []
  const today = new Date()
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i)
    const key = d.toISOString().slice(0, 10)
    const entry = daily[key] || { total_tokens: 0, requests: 0 }
    days.push({
      date: key,
      label: d.toLocaleDateString('en', { weekday: 'short' }),
      totalTokens: entry.total_tokens || 0,
      requests: entry.requests || 0,
    })
  }

  // 📖 Top models across all tracked days
  const modelTotals = {}
  for (const entry of Object.values(daily)) {
    const byModel = entry.by_model || {}
    for (const [key, val] of Object.entries(byModel)) {
      if (!modelTotals[key]) modelTotals[key] = { total: 0, requests: 0 }
      modelTotals[key].total += val.total || 0
      modelTotals[key].requests += val.requests || 0
    }
  }
  const topModels = Object.entries(modelTotals)
    .sort((a, b) => b[1].total - a[1].total)
    .slice(0, 10)
    .map(([key, val]) => ({ key, ...val }))

  // 📖 Top providers (aggregated from model keys)
  const providerTotals = {}
  for (const [key, val] of Object.entries(modelTotals)) {
    const provider = key.split('/')[0]
    if (!providerTotals[provider]) providerTotals[provider] = { total: 0, requests: 0 }
    providerTotals[provider].total += val.total
    providerTotals[provider].requests += val.requests
  }
  const topProviders = Object.entries(providerTotals)
    .sort((a, b) => b[1].total - a[1].total)
    .slice(0, 10)
    .map(([key, val]) => ({ key, ...val }))

  const todayKey = today.toISOString().slice(0, 10)
  const todayData = daily[todayKey] || {}

  return {
    today: {
      totalTokens: todayData.total_tokens || 0,
      promptTokens: todayData.prompt_tokens || 0,
      completionTokens: todayData.completion_tokens || 0,
      requests: todayData.requests || 0,
    },
    allTime: {
      totalTokens: allTime.total_tokens || 0,
      promptTokens: allTime.prompt_tokens || 0,
      completionTokens: allTime.completion_tokens || 0,
      requests: allTime.requests || 0,
    },
    sevenDays: days,
    topModels,
    topProviders,
    hasData: allTime.total_tokens > 0 || Object.keys(daily).length > 0,
  }
}
