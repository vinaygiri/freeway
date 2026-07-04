/**
 * @file web/app.js
 * @description Client-side JavaScript for the free-coding-models Web Dashboard V2.
 *
 * Features:
 *   - Real-time SSE model updates
 *   - Sidebar navigation (Dashboard / Settings / Analytics)
 *   - Full API key management (add, edit, delete, reveal, copy)
 *   - Toast notification system
 *   - Export (JSON, CSV, clipboard)
 *   - Analytics view with provider health, leaderboard, tier distribution
 */

// ─── State ───────────────────────────────────────────────────────────────────

let models = []
let sortColumn = 'avg'
let sortDirection = 'asc'
let filterTier = 'all'
let filterStatus = 'all'
let filterProvider = 'all'
let searchQuery = ''
let selectedModelId = null
let eventSource = null
let updateCount = 0
let configData = null
let revealedKeys = new Set()
let currentView = 'dashboard'

// ─── DOM References ───────────────────────────────────────────────────────────

const $ = (sel) => document.querySelector(sel)
const $$ = (sel) => document.querySelectorAll(sel)

const tableBody = $('#table-body')
const searchInput = $('#search-input')
const themeToggle = $('#theme-toggle')
const settingsBtn = $('#settings-btn')
const detailPanel = $('#detail-panel')
const detailClose = $('#detail-close')
const detailTitle = $('#detail-title')
const detailBody = $('#detail-body')
const providerFilter = $('#provider-filter')
const toastContainer = $('#toast-container')

// ─── Toast Notification System ───────────────────────────────────────────────

function showToast(message, type = 'info', duration = 3500) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' }
  const toast = document.createElement('div')
  toast.className = `toast toast--${type}`
  toast.innerHTML = `
    <span class="toast__icon">${icons[type] || '📌'}</span>
    <span class="toast__message">${escapeHtml(message)}</span>
    <button class="toast__close">&times;</button>
  `
  toastContainer.appendChild(toast)

  const closeBtn = toast.querySelector('.toast__close')
  const dismiss = () => {
    toast.classList.add('toast--exiting')
    setTimeout(() => toast.remove(), 300)
  }
  closeBtn.addEventListener('click', dismiss)
  setTimeout(dismiss, duration)
}

// ─── SSE Connection ──────────────────────────────────────────────────────────

function connectSSE() {
  if (eventSource) eventSource.close()
  eventSource = new EventSource('/api/events')

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      models = data
      updateCount++
      if (currentView === 'dashboard') {
        renderTable()
        updateStats()
      }
      if (currentView === 'analytics') renderAnalytics()
      if (updateCount === 1) populateProviderFilter()
      if (selectedModelId) updateDetailPanel()
    } catch (e) {
      console.error('SSE parse error:', e)
    }
  }

  eventSource.onerror = () => {
    console.warn('SSE connection lost, reconnecting in 3s...')
    setTimeout(connectSSE, 3000)
  }
}

// ─── View Navigation ─────────────────────────────────────────────────────────

function switchView(viewId) {
  currentView = viewId
  $$('.view').forEach(v => v.classList.add('view--hidden'))
  $(`#view-${viewId}`).classList.remove('view--hidden')
  $$('.sidebar__nav-item').forEach(n => n.classList.remove('sidebar__nav-item--active'))
  $(`#nav-${viewId}`)?.classList.add('sidebar__nav-item--active')

  if (viewId === 'settings') loadSettingsPage()
  if (viewId === 'analytics') renderAnalytics()
}

$$('.sidebar__nav-item[data-view]').forEach(btn => {
  btn.addEventListener('click', () => switchView(btn.dataset.view))
})

settingsBtn.addEventListener('click', () => switchView('settings'))

// ─── Rendering ───────────────────────────────────────────────────────────────

function getFilteredModels() {
  let filtered = [...models]

  if (filterTier !== 'all') filtered = filtered.filter(m => m.tier === filterTier)
  if (filterStatus !== 'all') {
    filtered = filtered.filter(m => {
      if (filterStatus === 'up') return m.status === 'up'
      if (filterStatus === 'down') return m.status === 'down' || m.status === 'timeout'
      if (filterStatus === 'pending') return m.status === 'pending'
      return true
    })
  }
  if (filterProvider !== 'all') filtered = filtered.filter(m => m.providerKey === filterProvider)
  if (searchQuery) {
    const q = searchQuery.toLowerCase()
    filtered = filtered.filter(m =>
      m.label.toLowerCase().includes(q) ||
      m.modelId.toLowerCase().includes(q) ||
      m.origin.toLowerCase().includes(q) ||
      m.tier.toLowerCase().includes(q) ||
      (m.verdict || '').toLowerCase().includes(q)
    )
  }

  filtered.sort((a, b) => {
    let cmp = 0
    const col = sortColumn
    if (col === 'idx') cmp = a.idx - b.idx
    else if (col === 'tier') cmp = tierRank(a.tier) - tierRank(b.tier)
    else if (col === 'label') cmp = a.label.localeCompare(b.label)
    else if (col === 'origin') cmp = a.origin.localeCompare(b.origin)
    else if (col === 'sweScore') cmp = parseSwe(a.sweScore) - parseSwe(b.sweScore)
    else if (col === 'ctx') cmp = parseCtx(a.ctx) - parseCtx(b.ctx)
    else if (col === 'latestPing') cmp = (a.latestPing ?? Infinity) - (b.latestPing ?? Infinity)
    else if (col === 'avg') cmp = (a.avg === Infinity ? 99999 : a.avg) - (b.avg === Infinity ? 99999 : b.avg)
    else if (col === 'stability') cmp = (a.stability ?? -1) - (b.stability ?? -1)
    else if (col === 'verdict') cmp = verdictRank(a.verdict) - verdictRank(b.verdict)
    else if (col === 'uptime') cmp = (a.uptime ?? 0) - (b.uptime ?? 0)
    return sortDirection === 'asc' ? cmp : -cmp
  })

  return filtered
}

function renderTable() {
  const filtered = getFilteredModels()

  if (filtered.length === 0) {
    tableBody.innerHTML = `
      <tr class="loading-row">
        <td colspan="12">
          <div class="loading-spinner">
            <span style="font-size: 24px">🔍</span>
            <span>No models match your filters</span>
          </div>
        </td>
      </tr>`
    return
  }

  const onlineModels = filtered.filter(m => m.status === 'up' && m.avg !== Infinity)
  const sorted = [...onlineModels].sort((a, b) => a.avg - b.avg)
  const top3 = sorted.slice(0, 3).map(m => m.modelId)

  const html = filtered.map((m, i) => {
    const rankClass = top3.indexOf(m.modelId) === 0 ? 'rank-1' :
                      top3.indexOf(m.modelId) === 1 ? 'rank-2' :
                      top3.indexOf(m.modelId) === 2 ? 'rank-3' : ''
    const medal = top3.indexOf(m.modelId) === 0 ? '🥇' :
                  top3.indexOf(m.modelId) === 1 ? '🥈' :
                  top3.indexOf(m.modelId) === 2 ? '🥉' : ''

    return `<tr class="${rankClass}" data-model-id="${m.modelId}" data-provider="${m.providerKey}">
      <td class="td--rank">${medal || (i + 1)}</td>
      <td>${tierBadge(m.tier)}</td>
      <td>
        <div class="model-name">
          <span class="status-dot status-dot--${m.status}"></span>${escapeHtml(m.label)}
          ${!m.hasApiKey && !m.cliOnly ? '<span class="no-key-badge">🔑 NO KEY</span>' : ''}
        </div>
        <div class="model-id">${escapeHtml(m.modelId)}</div>
      </td>
      <td><span class="provider-pill">${escapeHtml(m.origin)}</span></td>
      <td class="swe-score ${sweClass(m.sweScore)}">${m.sweScore || '—'}</td>
      <td class="ctx-value">${m.ctx || '—'}</td>
      <td class="ping-value ${pingClass(m.latestPing)}">${formatPing(m.latestPing, m.latestCode)}</td>
      <td class="ping-value ${pingClass(m.avg)}">${formatAvg(m.avg)}</td>
      <td class="td--stability">${stabilityCell(m.stability)}</td>
      <td>${verdictBadge(m.verdict, m.httpCode)}</td>
      <td class="td--uptime"><span class="uptime-value">${m.uptime > 0 ? m.uptime + '%' : '—'}</span></td>
      <td class="td--sparkline">${sparkline(m.pingHistory)}</td>
    </tr>`
  }).join('')

  tableBody.innerHTML = html

  tableBody.querySelectorAll('tr[data-model-id]').forEach(row => {
    row.addEventListener('click', () => {
      selectedModelId = row.dataset.modelId
      showDetailPanel(selectedModelId)
    })
  })
}

// ─── Cell Renderers ──────────────────────────────────────────────────────────

function tierBadge(tier) {
  const cls = tier.replace('+', 'plus').replace('-', 'minus').toLowerCase()
  return `<span class="tier-badge tier-badge--${cls}">${tier}</span>`
}

function sweClass(swe) {
  const val = parseSwe(swe)
  if (val >= 65) return 'swe-high'
  if (val >= 40) return 'swe-mid'
  return 'swe-low'
}

function pingClass(ms) {
  if (ms == null || ms === Infinity) return 'ping-none'
  if (ms < 500) return 'ping-fast'
  if (ms < 1500) return 'ping-medium'
  return 'ping-slow'
}

function formatPing(ms, code) {
  if (ms == null) return '<span class="ping-none">—</span>'
  if (code === '429') return '<span class="ping-slow">429</span>'
  if (code === '000') return '<span class="ping-slow">TIMEOUT</span>'
  return `${ms}ms`
}

function formatAvg(avg) {
  if (avg == null || avg === Infinity || avg > 99000) return '<span class="ping-none">—</span>'
  return `${avg}ms`
}

function stabilityCell(score) {
  if (score == null || score < 0) return '<span class="ping-none">—</span>'
  const cls = score >= 70 ? 'high' : score >= 40 ? 'mid' : 'low'
  return `<div class="stability-cell">
    <div class="stability-bar"><div class="stability-bar__fill stability-bar__fill--${cls}" style="width:${score}%"></div></div>
    <span class="stability-value">${score}</span>
  </div>`
}

function verdictBadge(verdict, httpCode) {
  if (!verdict) return '<span class="verdict-badge verdict--pending">Pending</span>'
  if (httpCode === '429') return '<span class="verdict-badge verdict--ratelimited">⚠️ Rate Limited</span>'
  const cls = verdict.toLowerCase().replace(/\s+/g, '').replace('very', 'very')
  const classMap = {
    'perfect': 'perfect', 'normal': 'normal', 'slow': 'slow',
    'spiky': 'spiky', 'veryslow': 'veryslow', 'overloaded': 'overloaded',
    'unstable': 'unstable', 'notactive': 'notactive', 'pending': 'pending'
  }
  return `<span class="verdict-badge verdict--${classMap[cls] || 'pending'}">${verdict}</span>`
}

function sparkline(history) {
  if (!history || history.length < 2) return ''
  const valid = history.filter(p => p.code === '200' || p.code === '401')
  if (valid.length < 2) return ''

  const values = valid.map(p => p.ms)
  const max = Math.max(...values, 1)
  const min = Math.min(...values, 0)
  const range = max - min || 1
  const w = 80, h = 22
  const step = w / (values.length - 1)

  const points = values.map((v, i) => {
    const x = i * step
    const y = h - ((v - min) / range) * (h - 4) - 2
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')

  const lastVal = values[values.length - 1]
  const color = lastVal < 500 ? '#00ff88' : lastVal < 1500 ? '#ffaa00' : '#ff4444'

  return `<svg class="sparkline-svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    <polyline fill="none" stroke="${color}" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" points="${points}" opacity="0.8"/>
    <circle cx="${((values.length - 1) * step).toFixed(1)}" cy="${(h - ((lastVal - min) / range) * (h - 4) - 2).toFixed(1)}" r="2.5" fill="${color}"/>
  </svg>`
}

// ─── Stats ───────────────────────────────────────────────────────────────────

function updateStats() {
  const total = models.length
  const online = models.filter(m => m.status === 'up').length
  const onlineWithPing = models.filter(m => m.status === 'up' && m.avg !== Infinity && m.avg < 99000)
  const avgLatency = onlineWithPing.length > 0
    ? Math.round(onlineWithPing.reduce((s, m) => s + m.avg, 0) / onlineWithPing.length)
    : null
  const fastest = [...onlineWithPing].sort((a, b) => a.avg - b.avg)[0]
  const providers = new Set(models.map(m => m.providerKey)).size

  animateValue($('#stat-total-value'), total)
  animateValue($('#stat-online-value'), online)
  $('#stat-avg-value').textContent = avgLatency != null ? `${avgLatency}ms` : '—'
  $('#stat-best-value').textContent = fastest ? fastest.label : '—'
  animateValue($('#stat-providers-value'), providers)
}

function animateValue(el, newVal) {
  const current = parseInt(el.textContent) || 0
  if (current === newVal) return
  el.textContent = newVal
}

// ─── Provider Filter Dropdown ────────────────────────────────────────────────

function populateProviderFilter() {
  const providers = [...new Set(models.map(m => m.providerKey))].sort()
  const origins = {}
  models.forEach(m => { origins[m.providerKey] = m.origin })

  providerFilter.innerHTML = '<option value="all">All Providers</option>' +
    providers.map(p => `<option value="${p}">${origins[p]} (${models.filter(m => m.providerKey === p).length})</option>`).join('')
}

// ─── Detail Panel ────────────────────────────────────────────────────────────

function showDetailPanel(modelId) {
  const model = models.find(m => m.modelId === modelId)
  if (!model) return
  detailPanel.removeAttribute('hidden')
  detailTitle.textContent = model.label
  updateDetailPanel()
}

function updateDetailPanel() {
  const model = models.find(m => m.modelId === selectedModelId)
  if (!model) return

  const chartSvg = buildDetailChart(model.pingHistory)

  detailBody.innerHTML = `
    <div class="detail-stat">
      <span class="detail-stat__label">Model ID</span>
      <span class="detail-stat__value" style="font-size:11px; word-break:break-all">${escapeHtml(model.modelId)}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Provider</span>
      <span class="detail-stat__value">${escapeHtml(model.origin)}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Tier</span>
      <span class="detail-stat__value">${tierBadge(model.tier)}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">SWE-bench Score</span>
      <span class="detail-stat__value swe-score ${sweClass(model.sweScore)}">${model.sweScore || '—'}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Context Window</span>
      <span class="detail-stat__value">${model.ctx || '—'}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Status</span>
      <span class="detail-stat__value"><span class="status-dot status-dot--${model.status}"></span>${model.status}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Latest Ping</span>
      <span class="detail-stat__value ${pingClass(model.latestPing)}">${formatPing(model.latestPing, model.latestCode)}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Average Latency</span>
      <span class="detail-stat__value ${pingClass(model.avg)}">${formatAvg(model.avg)}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">P95 Latency</span>
      <span class="detail-stat__value">${model.p95 != null && model.p95 !== Infinity ? model.p95 + 'ms' : '—'}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Jitter (σ)</span>
      <span class="detail-stat__value">${model.jitter != null && model.jitter !== Infinity ? model.jitter + 'ms' : '—'}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Stability Score</span>
      <span class="detail-stat__value">${stabilityCell(model.stability)}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Verdict</span>
      <span class="detail-stat__value">${verdictBadge(model.verdict, model.httpCode)}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Uptime</span>
      <span class="detail-stat__value">${model.uptime > 0 ? model.uptime + '%' : '—'}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">Ping Count</span>
      <span class="detail-stat__value">${model.pingCount}</span>
    </div>
    <div class="detail-stat">
      <span class="detail-stat__label">API Key</span>
      <span class="detail-stat__value">${model.hasApiKey ? '✅ Configured' : '❌ Missing'}</span>
    </div>
    <div class="detail-chart">
      <div class="detail-chart__title">Latency Trend (last 20 pings)</div>
      ${chartSvg}
    </div>
  `
}

function buildDetailChart(history) {
  if (!history || history.length < 2) return '<div style="color:var(--color-text-dim); text-align:center; padding:20px;">Waiting for ping data...</div>'

  const valid = history.filter(p => p.code === '200' || p.code === '401')
  if (valid.length < 2) return '<div style="color:var(--color-text-dim); text-align:center; padding:20px;">Not enough data yet...</div>'

  const values = valid.map(p => p.ms)
  const max = Math.max(...values, 1)
  const min = Math.min(...values, 0)
  const range = max - min || 1
  const w = 340, h = 100
  const padding = 4

  const points = values.map((v, i) => {
    const x = padding + i * ((w - 2 * padding) / (values.length - 1))
    const y = padding + (h - 2 * padding) - ((v - min) / range) * (h - 2 * padding)
    return [x.toFixed(1), y.toFixed(1)]
  })

  const linePoints = points.map(p => p.join(',')).join(' ')
  const areaPoints = `${points[0][0]},${h - padding} ${linePoints} ${points[points.length - 1][0]},${h - padding}`

  return `<svg width="100%" viewBox="0 0 ${w} ${h}" style="display:block;">
    <defs>
      <linearGradient id="chart-grad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--color-accent)" stop-opacity="0.3"/>
        <stop offset="100%" stop-color="var(--color-accent)" stop-opacity="0.02"/>
      </linearGradient>
    </defs>
    <polygon fill="url(#chart-grad)" points="${areaPoints}"/>
    <polyline fill="none" stroke="var(--color-accent)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" points="${linePoints}"/>
    ${points.map(([x, y], i) => i === points.length - 1 ? `<circle cx="${x}" cy="${y}" r="3.5" fill="var(--color-accent)" stroke="var(--color-bg)" stroke-width="1.5"/>` : '').join('')}
    <text x="${padding}" y="${h - 2}" font-size="9" fill="var(--color-text-dim)" font-family="var(--font-mono)">${min}ms</text>
    <text x="${w - padding}" y="${padding + 8}" font-size="9" fill="var(--color-text-dim)" font-family="var(--font-mono)" text-anchor="end">${max}ms</text>
  </svg>`
}

// ═══════ SETTINGS PAGE ═══════════════════════════════════════════════════════

async function loadSettingsPage() {
  try {
    const resp = await fetch('/api/config')
    configData = await resp.json()
    renderSettingsProviders()
  } catch (e) {
    showToast('Failed to load settings', 'error')
  }
}

function renderSettingsProviders(searchFilter = '') {
  if (!configData) return
  const container = $('#settings-providers')
  const entries = Object.entries(configData.providers)
    .filter(([key, p]) => {
      if (!searchFilter) return true
      const q = searchFilter.toLowerCase()
      return p.name.toLowerCase().includes(q) || key.toLowerCase().includes(q)
    })
    .sort((a, b) => a[1].name.localeCompare(b[1].name))

  container.innerHTML = entries.map(([key, p]) => {
    const isRevealed = revealedKeys.has(key)
    const maskedKey = p.hasKey ? (isRevealed ? (p.maskedKey || '••••••••') : maskKey(p.maskedKey || '')) : ''

    return `<div class="settings-card" data-provider="${key}" id="settings-card-${key}">
      <div class="settings-card__header" onclick="toggleSettingsCard('${key}')">
        <div class="settings-card__icon">🔌</div>
        <div class="settings-card__info">
          <div class="settings-card__name">${escapeHtml(p.name)}</div>
          <div class="settings-card__meta">${p.modelCount} models · ${escapeHtml(key)}</div>
        </div>
        <span class="settings-card__status ${p.hasKey ? 'settings-card__status--configured' : 'settings-card__status--missing'}">
          ${p.hasKey ? '✅ Active' : '🔑 No Key'}
        </span>
        <span class="settings-card__toggle-icon">▼</span>
      </div>
      <div class="settings-card__body">
        <div class="settings-card__content">
          ${p.hasKey ? `
            <div class="api-key-group">
              <label class="api-key-group__label">Current API Key</label>
              <div class="api-key-display">
                <span class="api-key-display__value" id="key-display-${key}">${maskedKey}</span>
                <div class="api-key-display__actions">
                  <button class="btn btn--sm btn--icon" onclick="toggleRevealKey('${key}')" title="${isRevealed ? 'Hide' : 'Reveal'}">
                    ${isRevealed ? '🙈' : '👁️'}
                  </button>
                  <button class="btn btn--sm btn--icon" onclick="copyKey('${key}')" title="Copy">📋</button>
                  <button class="btn btn--sm btn--danger" onclick="deleteKey('${key}')" title="Delete Key">🗑️</button>
                </div>
              </div>
            </div>
          ` : ''}
          <div class="api-key-group">
            <label class="api-key-group__label">${p.hasKey ? 'Update API Key' : 'Add API Key'}</label>
            <div class="api-key-group__row">
              <input type="password" class="api-key-group__input" id="key-input-${key}"
                     placeholder="Enter your API key..." autocomplete="off">
              <button class="btn btn--sm btn--success" onclick="saveKey('${key}')">
                ${p.hasKey ? 'Update' : 'Save'}
              </button>
            </div>
          </div>
          <div class="settings-card__enabled">
            <span class="settings-card__enabled-label">Provider Enabled</span>
            <label class="toggle-switch">
              <input type="checkbox" ${p.enabled !== false ? 'checked' : ''} onchange="toggleProvider('${key}', this.checked)">
              <span class="toggle-switch__slider"></span>
            </label>
          </div>
        </div>
      </div>
    </div>`
  }).join('')
}

// Settings: Global actions
window.toggleSettingsCard = function(key) {
  const card = $(`#settings-card-${key}`)
  if (card) card.classList.toggle('settings-card--expanded')
}

window.toggleRevealKey = async function(key) {
  if (revealedKeys.has(key)) {
    revealedKeys.delete(key)
    renderSettingsProviders($('#settings-search')?.value || '')
    return
  }

  try {
    const resp = await fetch(`/api/key/${key}`)
    const data = await resp.json()
    if (data.key) {
      revealedKeys.add(key)
      const display = $(`#key-display-${key}`)
      if (display) display.textContent = data.key
      // Re-render to update button icon
      const card = $(`#settings-card-${key}`)
      const wasExpanded = card?.classList.contains('settings-card--expanded')
      renderSettingsProviders($('#settings-search')?.value || '')
      if (wasExpanded) $(`#settings-card-${key}`)?.classList.add('settings-card--expanded')
    }
  } catch {
    showToast('Failed to reveal key', 'error')
  }
}

window.copyKey = async function(key) {
  try {
    const resp = await fetch(`/api/key/${key}`)
    const data = await resp.json()
    if (data.key) {
      await navigator.clipboard.writeText(data.key)
      showToast('API key copied to clipboard', 'success')
    } else {
      showToast('No key to copy', 'warning')
    }
  } catch {
    showToast('Failed to copy key', 'error')
  }
}

window.saveKey = async function(key) {
  const input = $(`#key-input-${key}`)
  const value = input?.value?.trim()
  if (!value) {
    showToast('Please enter an API key', 'warning')
    return
  }

  try {
    const resp = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKeys: { [key]: value } })
    })
    const result = await resp.json()
    if (result.success) {
      showToast(`API key for ${key} saved successfully!`, 'success')
      input.value = ''
      revealedKeys.delete(key)
      await loadSettingsPage()
      // Re-expand the card
      $(`#settings-card-${key}`)?.classList.add('settings-card--expanded')
    } else {
      showToast(result.error || 'Failed to save', 'error')
    }
  } catch {
    showToast('Network error while saving', 'error')
  }
}

window.deleteKey = async function(key) {
  if (!confirm(`Are you sure you want to delete the API key for "${key}"?`)) return

  try {
    const resp = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apiKeys: { [key]: '' } })
    })
    const result = await resp.json()
    if (result.success) {
      showToast(`API key for ${key} deleted`, 'info')
      revealedKeys.delete(key)
      await loadSettingsPage()
    } else {
      showToast(result.error || 'Failed to delete', 'error')
    }
  } catch {
    showToast('Network error while deleting', 'error')
  }
}

window.toggleProvider = async function(key, enabled) {
  try {
    const resp = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ providers: { [key]: { enabled } } })
    })
    const result = await resp.json()
    if (result.success) {
      showToast(`${key} ${enabled ? 'enabled' : 'disabled'}`, 'success')
    } else {
      showToast(result.error || 'Failed to toggle', 'error')
    }
  } catch {
    showToast('Network error', 'error')
  }
}

function maskKey(key) {
  if (!key || key.length < 8) return '••••••••'
  return '••••••••' + key.slice(-4)
}

// Settings search
$('#settings-search')?.addEventListener('input', (e) => {
  renderSettingsProviders(e.target.value)
})

$('#settings-expand-all')?.addEventListener('click', () => {
  $$('.settings-card').forEach(c => c.classList.add('settings-card--expanded'))
})
$('#settings-collapse-all')?.addEventListener('click', () => {
  $$('.settings-card').forEach(c => c.classList.remove('settings-card--expanded'))
})

// ═══════ ANALYTICS VIEW ═════════════════════════════════════════════════════

function renderAnalytics() {
  if (!models.length) return
  renderProviderHealth()
  renderLeaderboard()
  renderTierDistribution()
}

function renderProviderHealth() {
  const providerMap = {}
  models.forEach(m => {
    if (!providerMap[m.origin]) providerMap[m.origin] = { total: 0, online: 0, key: m.providerKey }
    providerMap[m.origin].total++
    if (m.status === 'up') providerMap[m.origin].online++
  })

  const entries = Object.entries(providerMap).sort((a, b) => {
    const pctA = a[1].online / a[1].total
    const pctB = b[1].online / b[1].total
    return pctB - pctA
  })

  const html = entries.map(([name, data]) => {
    const pct = data.total > 0 ? Math.round((data.online / data.total) * 100) : 0
    return `<div class="provider-health-item">
      <span class="provider-health__name">${escapeHtml(name)}</span>
      <div class="provider-health__bar"><div class="provider-health__fill" style="width:${pct}%"></div></div>
      <span class="provider-health__pct ${pct > 70 ? 'ping-fast' : pct > 30 ? 'ping-medium' : 'ping-slow'}">${pct}%</span>
    </div>`
  }).join('')

  $('#provider-health-body').innerHTML = html || '<div style="color:var(--color-text-dim);">Waiting for data...</div>'
}

function renderLeaderboard() {
  const online = models.filter(m => m.status === 'up' && m.avg !== Infinity && m.avg < 99000)
  const top10 = [...online].sort((a, b) => a.avg - b.avg).slice(0, 10)

  const html = top10.map((m, i) => {
    const rankClass = i < 3 ? `leaderboard__rank--${i + 1}` : ''
    const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : (i + 1)
    return `<div class="leaderboard-item">
      <div class="leaderboard__rank ${rankClass}">${medal}</div>
      <span class="leaderboard__name">${escapeHtml(m.label)}</span>
      <span class="leaderboard__latency">${m.avg}ms</span>
    </div>`
  }).join('')

  $('#leaderboard-body').innerHTML = html || '<div style="color:var(--color-text-dim);">Waiting for ping data...</div>'
}

function renderTierDistribution() {
  const tierColors = { 'S+': '#ffd700', 'S': '#ff8c00', 'A+': '#00c8ff', 'A': '#3ddc84', 'A-': '#7ecf7e', 'B+': '#a8a8c8', 'B': '#808098', 'C': '#606078' }
  const tierCounts = {}
  models.forEach(m => { tierCounts[m.tier] = (tierCounts[m.tier] || 0) + 1 })
  const maxCount = Math.max(...Object.values(tierCounts), 1)

  const tiers = ['S+', 'S', 'A+', 'A', 'A-', 'B+', 'B', 'C']
  const html = tiers.map(t => {
    const count = tierCounts[t] || 0
    const pct = (count / maxCount) * 100
    return `<div class="tier-dist-item">
      <div class="tier-dist__badge">${tierBadge(t)}</div>
      <div class="tier-dist__bar"><div class="tier-dist__fill" style="width:${pct}%; background:${tierColors[t]}"></div></div>
      <span class="tier-dist__count">${count}</span>
    </div>`
  }).join('')

  $('#tier-dist-body').innerHTML = html
}

// ═══════ EXPORT ═════════════════════════════════════════════════════════════

const exportModal = $('#export-modal')
const exportBtn = $('#export-btn')
const exportClose = $('#export-close')

exportBtn?.addEventListener('click', () => { exportModal.hidden = false })
exportClose?.addEventListener('click', () => { exportModal.hidden = true })
exportModal?.addEventListener('click', (e) => { if (e.target === exportModal) exportModal.hidden = true })

$('#export-json')?.addEventListener('click', () => {
  const data = JSON.stringify(getFilteredModels(), null, 2)
  downloadFile(data, 'free-coding-models-export.json', 'application/json')
  showToast('Exported as JSON', 'success')
  exportModal.hidden = true
})

$('#export-csv')?.addEventListener('click', () => {
  const filtered = getFilteredModels()
  const headers = ['Rank', 'Tier', 'Model', 'Provider', 'SWE%', 'Context', 'LatestPing', 'AvgPing', 'Stability', 'Verdict', 'Uptime']
  const rows = filtered.map((m, i) =>
    [i + 1, m.tier, m.label, m.origin, m.sweScore || '', m.ctx || '', m.latestPing || '', m.avg === Infinity ? '' : m.avg, m.stability || '', m.verdict || '', m.uptime || ''].join(',')
  )
  const csv = [headers.join(','), ...rows].join('\n')
  downloadFile(csv, 'free-coding-models-export.csv', 'text/csv')
  showToast('Exported as CSV', 'success')
  exportModal.hidden = true
})

$('#export-clipboard')?.addEventListener('click', async () => {
  const filtered = getFilteredModels()
  const online = filtered.filter(m => m.status === 'up')
  const text = `free-coding-models Dashboard Export\n` +
    `Total: ${filtered.length} | Online: ${online.length}\n\n` +
    online.slice(0, 20).map((m, i) =>
      `${i + 1}. ${m.label} [${m.tier}] — ${m.avg !== Infinity ? m.avg + 'ms' : 'N/A'} (${m.origin})`
    ).join('\n')
  await navigator.clipboard.writeText(text)
  showToast('Copied to clipboard', 'success')
  exportModal.hidden = true
})

function downloadFile(content, filename, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

// ─── Event Handlers ──────────────────────────────────────────────────────────

// Theme toggle
const toggleTheme = () => {
  const html = document.documentElement
  const current = html.getAttribute('data-theme')
  html.setAttribute('data-theme', current === 'dark' ? 'light' : 'dark')
}
themeToggle?.addEventListener('click', toggleTheme)
$('#sidebar-theme-toggle')?.addEventListener('click', toggleTheme)

// Search
searchInput?.addEventListener('input', (e) => {
  searchQuery = e.target.value
  renderTable()
})

// Ctrl+K shortcut
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    if (currentView !== 'dashboard') switchView('dashboard')
    searchInput?.focus()
  }
  if (e.key === 'Escape') {
    if (!detailPanel.hidden) { detailPanel.hidden = true; selectedModelId = null }
    if (!exportModal.hidden) exportModal.hidden = true
  }
})

// Tier filter
$('#tier-filters')?.addEventListener('click', (e) => {
  const btn = e.target.closest('.tier-btn')
  if (!btn) return
  filterTier = btn.dataset.tier
  $$('.tier-btn').forEach(b => b.classList.remove('tier-btn--active'))
  btn.classList.add('tier-btn--active')
  renderTable()
})

// Status filter
$('#status-filters')?.addEventListener('click', (e) => {
  const btn = e.target.closest('.status-btn')
  if (!btn) return
  filterStatus = btn.dataset.status
  $$('.status-btn').forEach(b => b.classList.remove('status-btn--active'))
  btn.classList.add('status-btn--active')
  renderTable()
})

// Provider filter
providerFilter?.addEventListener('change', (e) => {
  filterProvider = e.target.value
  renderTable()
})

// Table header sorting
$('#models-table thead')?.addEventListener('click', (e) => {
  const th = e.target.closest('th.sortable')
  if (!th) return
  const col = th.dataset.sort
  if (sortColumn === col) {
    sortDirection = sortDirection === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn = col
    sortDirection = 'asc'
  }
  $$('th.sortable').forEach(t => t.classList.remove('sort-active'))
  th.classList.add('sort-active')
  renderTable()
})

// Detail panel close
detailClose?.addEventListener('click', () => {
  detailPanel.hidden = true
  selectedModelId = null
})

// ─── Utility Functions ───────────────────────────────────────────────────────

const TIER_RANKS = { 'S+': 0, 'S': 1, 'A+': 2, 'A': 3, 'A-': 4, 'B+': 5, 'B': 6, 'C': 7 }
function tierRank(tier) { return TIER_RANKS[tier] ?? 99 }

const VERDICT_RANKS = { 'Perfect': 0, 'Normal': 1, 'Slow': 2, 'Spiky': 3, 'Very Slow': 4, 'Overloaded': 5, 'Unstable': 6, 'Not Active': 7, 'Pending': 8 }
function verdictRank(verdict) { return VERDICT_RANKS[verdict] ?? 99 }

function parseSwe(s) {
  if (!s || s === '—') return 0
  return parseFloat(s.replace('%', '')) || 0
}

function parseCtx(c) {
  if (!c || c === '—') return 0
  const s = c.toLowerCase()
  if (s.includes('m')) return parseFloat(s) * 1000
  if (s.includes('k')) return parseFloat(s)
  return 0
}

function escapeHtml(str) {
  if (!str) return ''
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

// ─── Initialize ──────────────────────────────────────────────────────────────

connectSSE()
