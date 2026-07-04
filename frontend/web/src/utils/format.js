/**
 * @file web/src/utils/format.js
 * @description Shared formatting utilities for the web dashboard.
 * → formatPing, formatAvg, formatCtx, maskKey, escapeHtml
 */

export function formatPing(ms, code) {
  if (ms == null) return { text: '—', cls: 'pingNone' }
  if (code === '429') return { text: '429', cls: 'pingSlow' }
  if (code === '000') return { text: 'TIMEOUT', cls: 'pingSlow' }
  return { text: `${ms}ms`, cls: pingClass(ms) }
}

export function formatAvg(avg) {
  if (avg == null || avg === Infinity || avg > 99000) return { text: '—', cls: 'pingNone' }
  return { text: `${avg}ms`, cls: pingClass(avg) }
}

export function pingClass(ms) {
  if (ms == null || ms === Infinity) return 'pingNone'
  if (ms < 500) return 'pingFast'
  if (ms < 1500) return 'pingMedium'
  return 'pingSlow'
}

export function formatCtx(c) {
  if (!c || c === '—') return 0
  const s = c.toLowerCase()
  if (s.includes('m')) return parseFloat(s) * 1000
  if (s.includes('k')) return parseFloat(s)
  return 0
}

export function maskKey(key) {
  if (!key || key.length < 8) return '••••••••'
  return '••••••••' + key.slice(-4)
}

export function escapeHtml(str) {
  if (!str) return ''
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}
