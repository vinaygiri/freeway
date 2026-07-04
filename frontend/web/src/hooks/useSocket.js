/**
 * @file web/src/hooks/useSocket.js
 * @description Realtime model-data hook with Socket.IO primary, SSE fallback, and REST polling safety net.
 *
 * 📖 The dashboard runs locally, so freshness matters more than shaving every
 * byte. Socket.IO gives the snappiest path in `pnpm dev:web`; SSE keeps Docker /
 * daemon-style servers working without Socket.IO; REST polling guarantees the UI
 * eventually recovers if both streaming transports are interrupted.
 *
 * @functions
 *   → useSocket(serverUrl) — Subscribe to live dashboard state
 * @exports useSocket
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { io } from 'socket.io-client'

const REST_FALLBACK_INTERVAL_MS = 2_000
const STALE_UPDATE_MS = 4_000
const ACTIVITY_THROTTLE_MS = 1_000

function normalizePayload(data) {
  if (!data) return null
  if (Array.isArray(data)) return { models: data }
  if (Array.isArray(data.models)) return data
  return null
}

function sameOriginUrl(path, serverUrl) {
  if (!serverUrl) return path
  return `${serverUrl.replace(/\/$/, '')}${path}`
}

export function useSocket(serverUrl = '') {
  const [models, setModels] = useState([])
  const [connected, setConnected] = useState(false)
  const [transport, setTransport] = useState('connecting')
  const [updateCount, setUpdateCount] = useState(0)
  const [nextPingAt, setNextPingAt] = useState(null)
  const [serverIsPinging, setServerIsPinging] = useState(false)
  const [pendingPings, setPendingPings] = useState(0)
  const [pingMode, setPingMode] = useState('speed')
  const [globalBenchmarkRunning, setGlobalBenchmarkRunning] = useState(false)
  const [globalBenchmarkTotal, setGlobalBenchmarkTotal] = useState(0)
  const [globalBenchmarkCompleted, setGlobalBenchmarkCompleted] = useState(0)
  const [updateStatus, setUpdateStatus] = useState(null)

  const socketRef = useRef(null)
  const esRef = useRef(null)
  const pollRef = useRef(null)
  const lastUpdateRef = useRef(0)
  const lastActivityRef = useRef(0)
  const mountedRef = useRef(false)

  const applyPayload = useCallback((raw, source = 'unknown') => {
    const data = normalizePayload(raw)
    if (!data || !mountedRef.current) return

    setModels(data.models ?? [])
    setPingMode(data.pingMode ?? 'speed')
    setNextPingAt(data.nextPingAt ?? null)
    setServerIsPinging(Boolean(data.isPinging))
    setPendingPings(Number.isFinite(data.pendingPings) ? data.pendingPings : 0)
    setGlobalBenchmarkRunning(Boolean(data.globalBenchmarkRunning))
    setGlobalBenchmarkTotal(Number.isFinite(data.globalBenchmarkTotal) ? data.globalBenchmarkTotal : 0)
    setGlobalBenchmarkCompleted(Number.isFinite(data.globalBenchmarkCompleted) ? data.globalBenchmarkCompleted : 0)
    setUpdateStatus(data.updateStatus && data.updateStatus.allowedOutdated ? data.updateStatus : null)
    setUpdateCount((count) => count + 1)
    lastUpdateRef.current = Date.now()
    if (source !== 'poll') {
      setConnected(true)
      setTransport(source)
    }
  }, [])

  const fetchSnapshot = useCallback(async () => {
    try {
      const stateResponse = await fetch(sameOriginUrl('/api/state', serverUrl), { headers: { Accept: 'application/json' } })
      if (stateResponse.ok) {
        applyPayload(await stateResponse.json(), 'poll')
        setConnected(true)
        setTransport((current) => current === 'socket' || current === 'sse' ? current : 'poll')
        return
      }
    } catch {}

    try {
      const response = await fetch(sameOriginUrl('/api/models', serverUrl), { headers: { Accept: 'application/json' } })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      applyPayload(await response.json(), 'poll')
      setConnected(true)
      setTransport((current) => current === 'socket' || current === 'sse' ? current : 'poll')
    } catch {
      setConnected(false)
      setTransport('offline')
    }
  }, [applyPayload, serverUrl])

  const startSse = useCallback(() => {
    if (esRef.current || !mountedRef.current) return
    try {
      const es = new EventSource(sameOriginUrl('/api/events', serverUrl))
      esRef.current = es
      es.onopen = () => {
        if (!mountedRef.current) return
        setConnected(true)
        setTransport('sse')
      }
      const handleSsePayload = (event) => {
        try { applyPayload(JSON.parse(event.data), 'sse') }
        catch (err) { console.warn('[useSocket] SSE parse error:', err) }
      }
      es.onmessage = handleSsePayload
      es.addEventListener('models', handleSsePayload)
      es.onerror = () => {
        es.close()
        if (esRef.current === es) esRef.current = null
        if (!socketRef.current?.connected) setConnected(false)
      }
    } catch {
      esRef.current = null
    }
  }, [applyPayload, serverUrl])

  const sendActivity = useCallback(() => {
    const now = Date.now()
    if (now - lastActivityRef.current < ACTIVITY_THROTTLE_MS) return
    lastActivityRef.current = now

    if (socketRef.current?.connected) {
      socketRef.current.emit('client:activity')
      return
    }

    fetch(sameOriginUrl('/api/activity', serverUrl), { method: 'POST' }).catch(() => {})
  }, [serverUrl])

  useEffect(() => {
    mountedRef.current = true

    const socket = io(serverUrl || undefined, {
      transports: ['websocket', 'polling'],
      reconnectionDelay: 500,
      reconnectionDelayMax: 2500,
      timeout: 1200,
    })
    socketRef.current = socket

    socket.on('connect', () => {
      setConnected(true)
      setTransport('socket')
      esRef.current?.close()
      esRef.current = null
      socket.emit('models:refresh')
      socket.emit('client:activity')
    })
    socket.on('disconnect', () => {
      if (!mountedRef.current) return
      setConnected(false)
      startSse()
    })
    socket.on('connect_error', () => {
      if (!mountedRef.current) return
      setConnected(false)
      startSse()
    })
    socket.on('models:update', (data) => applyPayload(data, 'socket'))

    pollRef.current = setInterval(() => {
      const stale = Date.now() - lastUpdateRef.current > STALE_UPDATE_MS
      if (!socket.connected || stale) void fetchSnapshot()
    }, REST_FALLBACK_INTERVAL_MS)

    void fetchSnapshot()

    const activityEvents = ['keydown', 'pointerdown', 'mousemove', 'focus']
    for (const eventName of activityEvents) window.addEventListener(eventName, sendActivity, { passive: true })

    return () => {
      mountedRef.current = false
      for (const eventName of activityEvents) window.removeEventListener(eventName, sendActivity)
      if (pollRef.current) clearInterval(pollRef.current)
      socket.disconnect()
      esRef.current?.close()
      socketRef.current = null
      esRef.current = null
    }
  }, [applyPayload, fetchSnapshot, sendActivity, serverUrl, startSse])

  return {
    models,
    connected,
    transport,
    updateCount,
    nextPingAt,
    isPinging: serverIsPinging,
    pendingPings,
    pingMode,
    globalBenchmarkRunning,
    globalBenchmarkTotal,
    globalBenchmarkCompleted,
    updateStatus,
  }
}
