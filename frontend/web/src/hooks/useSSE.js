/**
 * @file web/src/hooks/useSSE.js
 * @description React hook for SSE (Server-Sent Events) connection.
 * 📖 Connects to /api/events, auto-reconnects on failure, returns live model data.
 * → useSSE
 */
import { useState, useEffect, useRef, useCallback } from 'react'

const RECONNECT_DELAY = 2000

export function useSSE(url = '/api/events') {
  const [models, setModels] = useState([])
  const [connected, setConnected] = useState(false)
  const [updateCount, setUpdateCount] = useState(0)
  const esRef = useRef(null)
  const reconnectRef = useRef(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return

    // Close existing connection
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }

    clearTimeout(reconnectRef.current)

    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      if (mountedRef.current) setConnected(true)
    }

    es.onmessage = (event) => {
      if (!mountedRef.current) return
      try {
        const data = JSON.parse(event.data)
        setModels(data)
        setUpdateCount(c => c + 1)
      } catch (e) {
        console.warn('[useSSE] parse error:', e)
      }
    }

    es.onerror = () => {
      setConnected(false)
      es.close()
      esRef.current = null

      if (mountedRef.current) {
        reconnectRef.current = setTimeout(() => {
          if (mountedRef.current) connect()
        }, RECONNECT_DELAY)
      }
    }
  }, [url])

  useEffect(() => {
    mountedRef.current = true
    connect()

    return () => {
      mountedRef.current = false
      clearTimeout(reconnectRef.current)
      esRef.current?.close()
    }
  }, [connect])

  return { models, connected, updateCount }
}