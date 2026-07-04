/**
 * @file web/src/utils/ranks.js
 * @description Tier, verdict, and SWE ranking maps and helpers.
 * → tierRank, verdictRank, parseSwe, sweClass
 */

const TIER_RANKS = { 'S+': 0, S: 1, 'A+': 2, A: 3, 'A-': 4, 'B+': 5, B: 6, C: 7 }
const VERDICT_RANKS = {
  Perfect: 0, Normal: 1, Slow: 2, Spiky: 3,
  'Very Slow': 4, Overloaded: 5, Unstable: 6,
  'Not Active': 7, Pending: 8,
}

export function tierRank(tier) { return TIER_RANKS[tier] ?? 99 }
export function verdictRank(verdict) { return VERDICT_RANKS[verdict] ?? 99 }

export function parseSwe(s) {
  if (!s || s === '—') return 0
  return parseFloat(s.replace('%', '')) || 0
}

export function sweClass(swe) {
  const val = parseSwe(swe)
  if (val >= 65) return 'sweHigh'
  if (val >= 40) return 'sweMid'
  return 'sweLow'
}

export function verdictCls(verdict) {
  if (!verdict) return 'pending'
  const map = {
    perfect: 'perfect', normal: 'normal', slow: 'slow',
    spiky: 'spiky', veryslow: 'veryslow', overloaded: 'overloaded',
    unstable: 'unstable', notactive: 'notactive', pending: 'pending',
  }
  return map[verdict.toLowerCase().replace(/\s+/g, '')] || 'pending'
}
