import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '@/store/auth'
import { useNotificationStore } from '@/store/notifications'
import type { WSMessage, Alert } from '@/types'
import toast from 'react-hot-toast'

type MessageHandler = (message: WSMessage) => void

const RECONNECT_BASE_DELAY = 2000
const RECONNECT_MAX_DELAY = 30000

export function useWebSocket(onMessage?: MessageHandler) {
  const ws = useRef<WebSocket | null>(null)
  const reconnectDelay = useRef(RECONNECT_BASE_DELAY)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const isUnmounted = useRef(false)
  const { accessToken, isAuthenticated } = useAuthStore()
  const addAlert = useNotificationStore((s) => s.addAlert)

  const connect = useCallback(() => {
    if (!isAuthenticated || !accessToken) return

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const wsUrl = `${protocol}://${window.location.host}/ws/console`

    ws.current = new WebSocket(wsUrl)

    ws.current.onopen = () => {
      reconnectDelay.current = RECONNECT_BASE_DELAY
      // Authenticate
      ws.current?.send(JSON.stringify({ token: accessToken }))
    }

    ws.current.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)

        // Handle system-level messages
        if (message.type === 'new_alert') {
          const alertPayload = message.payload as unknown as Alert
          addAlert(alertPayload)
          if (alertPayload.severity === 'critical') {
            toast.error(`Critical Alert: ${alertPayload.title}`, { duration: 8000 })
          }
        }

        onMessage?.(message)
      } catch {
        // ignore parse errors
      }
    }

    ws.current.onclose = () => {
      if (isUnmounted.current) return
      reconnectTimer.current = setTimeout(() => {
        reconnectDelay.current = Math.min(reconnectDelay.current * 1.5, RECONNECT_MAX_DELAY)
        connect()
      }, reconnectDelay.current)
    }

    ws.current.onerror = () => {
      ws.current?.close()
    }
  }, [accessToken, isAuthenticated, onMessage, addAlert])

  useEffect(() => {
    isUnmounted.current = false
    connect()

    return () => {
      isUnmounted.current = true
      clearTimeout(reconnectTimer.current)
      ws.current?.close()
    }
  }, [connect])

  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message))
    }
  }, [])

  return { sendMessage }
}
