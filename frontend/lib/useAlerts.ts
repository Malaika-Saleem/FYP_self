"use client"

import { useState, useEffect, useCallback, useRef } from "react"

// ========================================
// Types
// ========================================

export interface RealTimeAlert {
  alert_id: string
  camera_id: string
  alert_type: "object_detection" | "behavior_detection" | "suspicious_person"
  detection_class: string
  severity: "critical" | "high" | "medium" | "low"
  display_name: string
  description: string
  confidence: number
  timestamp: number
  timestamp_iso: string
  status: "pending" | "confirmed" | "dismissed" | "auto_expired"
  bounding_boxes: Array<{
    class?: string
    confidence?: number
    bbox?: number[]
  }>
  frame_snapshot_url?: string | null
  face_id?: string | null
  face_match_score?: number | null
  requires_confirmation: boolean
  event_id?: string | null
}

export interface AlertStats {
  total_alerts: number
  confirmed_alerts: number
  dismissed_alerts: number
  pending_alerts: number
  alerts_by_type: Record<string, number>
  alerts_by_severity: Record<string, number>
  active_subscribers: number
  active_pending_count: number
}

interface UseAlertsOptions {
  /** Whether to auto-connect the SSE stream */
  autoConnect?: boolean
  /** Max number of alerts to keep in state */
  maxAlerts?: number
  /** Whether to play sound on new alerts */
  enableSound?: boolean
  /** Camera ID filter (null = all cameras) */
  cameraId?: string | null
}

interface UseAlertsReturn {
  /** List of all alerts (newest first) */
  alerts: RealTimeAlert[]
  /** Currently pending alerts requiring user action */
  pendingAlerts: RealTimeAlert[]
  /** The most recent unhandled alert (for popup) */
  currentPopupAlert: RealTimeAlert | null
  /** Whether SSE is connected */
  isConnected: boolean
  /** Connection error message */
  connectionError: string | null
  /** Alert statistics */
  stats: AlertStats | null
  /** Confirm an alert (mark as real threat) */
  confirmAlert: (alertId: string, note?: string) => Promise<boolean>
  /** Dismiss an alert (mark as false positive) */
  dismissAlert: (alertId: string, note?: string) => Promise<boolean>
  /** Manually connect to SSE stream */
  connect: () => void
  /** Disconnect from SSE stream */
  disconnect: () => void
  /** Clear the popup alert (move to next pending) */
  dismissPopup: () => void
  /** Send a test alert (development only) */
  sendTestAlert: (detectionClass: string, confidence?: number) => Promise<void>
}

// ========================================
// Alert Sound
// ========================================

function playAlertSound(severity: string) {
  if (typeof window === "undefined") return
  
  try {
    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
    const oscillator = audioCtx.createOscillator()
    const gainNode = audioCtx.createGain()
    
    oscillator.connect(gainNode)
    gainNode.connect(audioCtx.destination)
    
    // Different sounds for different severity
    switch (severity) {
      case "critical":
        oscillator.frequency.value = 880 // High A
        oscillator.type = "square"
        gainNode.gain.value = 0.3
        // Rapid beeping for critical
        const criticalDuration = 0.15
        for (let i = 0; i < 4; i++) {
          gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime + i * criticalDuration * 2)
          gainNode.gain.setValueAtTime(0, audioCtx.currentTime + i * criticalDuration * 2 + criticalDuration)
        }
        oscillator.start()
        oscillator.stop(audioCtx.currentTime + 1.2)
        break
        
      case "high":
        oscillator.frequency.value = 660
        oscillator.type = "sawtooth"
        gainNode.gain.value = 0.2
        oscillator.start()
        oscillator.stop(audioCtx.currentTime + 0.5)
        break
        
      case "medium":
        oscillator.frequency.value = 440
        oscillator.type = "triangle"
        gainNode.gain.value = 0.15
        oscillator.start()
        oscillator.stop(audioCtx.currentTime + 0.3)
        break
        
      default:
        oscillator.frequency.value = 330
        oscillator.type = "sine"
        gainNode.gain.value = 0.1
        oscillator.start()
        oscillator.stop(audioCtx.currentTime + 0.2)
    }
  } catch {
    // Audio not available — silent fallback
  }
}

// ========================================
// Hook Implementation
// ========================================

export function useAlerts(options: UseAlertsOptions = {}): UseAlertsReturn {
  const {
    autoConnect = true,
    maxAlerts = 100,
    enableSound = true,
    cameraId = null,
  } = options

  const [alerts, setAlerts] = useState<RealTimeAlert[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [stats, setStats] = useState<AlertStats | null>(null)
  const [popupQueue, setPopupQueue] = useState<string[]>([]) // Queue of alert IDs awaiting popup
  
  const eventSourceRef = useRef<EventSource | null>(null)
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttempts = useRef(0)
  const maxReconnectAttempts = 10
  
  const flaskUrl = typeof window !== "undefined" 
    ? (process.env.NEXT_PUBLIC_FLASK_API_URL || "http://localhost:5000")
    : "http://localhost:5000"

  // ---- Derived state ----
  const pendingAlerts = alerts.filter(a => a.status === "pending")
  const currentPopupAlert = popupQueue.length > 0
    ? alerts.find(a => a.alert_id === popupQueue[0]) || null
    : null

  // ---- SSE Connection ----
  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    try {
      const sseUrl = `${flaskUrl}/api/alerts/stream`
      console.log("🔔 Connecting to alert stream:", sseUrl)
      
      const eventSource = new EventSource(sseUrl)
      eventSourceRef.current = eventSource

      eventSource.addEventListener("connected", (event) => {
        console.log("✅ Alert stream connected")
        setIsConnected(true)
        setConnectionError(null)
        reconnectAttempts.current = 0
      })

      eventSource.addEventListener("alert", (event) => {
        try {
          const alertData: RealTimeAlert = JSON.parse(event.data)
          console.log("🚨 New alert received:", alertData.display_name, alertData.severity)
          
          // Filter by camera if specified
          if (cameraId && alertData.camera_id !== cameraId) return

          setAlerts(prev => {
            const exists = prev.some(a => a.alert_id === alertData.alert_id)
            if (exists) return prev
            const updated = [alertData, ...prev].slice(0, maxAlerts)
            return updated
          })

          // Add to popup queue if requires confirmation
          if (alertData.requires_confirmation && alertData.status === "pending") {
            setPopupQueue(prev => [...prev, alertData.alert_id])
          }

          // Play sound
          if (enableSound) {
            playAlertSound(alertData.severity)
          }
        } catch (err) {
          console.error("Failed to parse alert:", err)
        }
      })

      eventSource.addEventListener("alert_update", (event) => {
        try {
          const updateData = JSON.parse(event.data)
          console.log("📝 Alert update:", updateData.alert_id, updateData.status)
          
          setAlerts(prev => prev.map(a => 
            a.alert_id === updateData.alert_id
              ? { ...a, status: updateData.status }
              : a
          ))

          // Remove from popup queue if resolved
          if (updateData.status !== "pending") {
            setPopupQueue(prev => prev.filter(id => id !== updateData.alert_id))
          }
        } catch (err) {
          console.error("Failed to parse alert update:", err)
        }
      })

      eventSource.addEventListener("active_alerts", (event) => {
        try {
          const activeAlerts: RealTimeAlert[] = JSON.parse(event.data)
          console.log(`📋 Received ${activeAlerts.length} active alerts`)
          
          setAlerts(prev => {
            const existingIds = new Set(prev.map(a => a.alert_id))
            const newAlerts = activeAlerts.filter(a => !existingIds.has(a.alert_id))
            return [...newAlerts, ...prev].slice(0, maxAlerts)
          })

          // Queue pending alerts for popup
          const pendingIds = activeAlerts
            .filter(a => a.status === "pending" && a.requires_confirmation)
            .map(a => a.alert_id)
          setPopupQueue(prev => {
            const existing = new Set(prev)
            const newIds = pendingIds.filter(id => !existing.has(id))
            return [...prev, ...newIds]
          })
        } catch (err) {
          console.error("Failed to parse active alerts:", err)
        }
      })

      eventSource.addEventListener("heartbeat", (event) => {
        try {
          const data = JSON.parse(event.data)
          // Update pending count from heartbeat
          if (data.pending !== undefined) {
            setStats(prev => prev ? { ...prev, active_pending_count: data.pending } : null)
          }
        } catch {
          // Heartbeat parse error is non-critical
        }
      })

      eventSource.onerror = () => {
        console.warn("⚠️ Alert stream connection error")
        setIsConnected(false)
        eventSource.close()
        eventSourceRef.current = null

        // Auto-reconnect with backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000)
          console.log(`🔄 Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current + 1})`)
          reconnectTimerRef.current = setTimeout(() => {
            reconnectAttempts.current++
            connect()
          }, delay)
        } else {
          setConnectionError("Failed to connect to alert stream after multiple attempts")
        }
      }
    } catch (err) {
      console.error("Failed to create EventSource:", err)
      setConnectionError("Failed to connect to alert stream")
    }
  }, [flaskUrl, cameraId, maxAlerts, enableSound])

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current)
      reconnectTimerRef.current = null
    }
    setIsConnected(false)
    reconnectAttempts.current = 0
  }, [])

  // ---- Alert Actions ----
  const confirmAlert = useCallback(async (alertId: string, note?: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/alerts/confirm/${alertId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note }),
      })
      const data = await response.json()
      
      if (data.success) {
        setAlerts(prev => prev.map(a =>
          a.alert_id === alertId ? { ...a, status: "confirmed" as const } : a
        ))
        setPopupQueue(prev => prev.filter(id => id !== alertId))
        return true
      }
      return false
    } catch (err) {
      console.error("Failed to confirm alert:", err)
      return false
    }
  }, [])

  const dismissAlert = useCallback(async (alertId: string, note?: string): Promise<boolean> => {
    try {
      const response = await fetch(`/api/alerts/dismiss/${alertId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note }),
      })
      const data = await response.json()
      
      if (data.success) {
        setAlerts(prev => prev.map(a =>
          a.alert_id === alertId ? { ...a, status: "dismissed" as const } : a
        ))
        setPopupQueue(prev => prev.filter(id => id !== alertId))
        return true
      }
      return false
    } catch (err) {
      console.error("Failed to dismiss alert:", err)
      return false
    }
  }, [])

  const dismissPopup = useCallback(() => {
    setPopupQueue(prev => prev.slice(1))
  }, [])

  const sendTestAlert = useCallback(async (detectionClass: string, confidence: number = 0.85) => {
    try {
      await fetch("/api/alerts/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ detection_class: detectionClass, confidence }),
      })
    } catch (err) {
      console.error("Failed to send test alert:", err)
    }
  }, [])

  // ---- Fetch stats periodically ----
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch("/api/alerts/stats")
        const data = await res.json()
        if (data.success) setStats(data.stats)
      } catch {
        // Stats fetch failed silently
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 10000) // Every 10 seconds
    return () => clearInterval(interval)
  }, [])

  // ---- Auto-connect ----
  useEffect(() => {
    if (autoConnect) {
      connect()
    }
    return () => disconnect()
  }, [autoConnect, connect, disconnect])

  return {
    alerts,
    pendingAlerts,
    currentPopupAlert,
    isConnected,
    connectionError,
    stats,
    confirmAlert,
    dismissAlert,
    connect,
    disconnect,
    dismissPopup,
    sendTestAlert,
  }
}
