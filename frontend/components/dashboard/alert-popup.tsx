"use client"

import { useState, useEffect, useRef } from "react"
import { 
  AlertTriangle, Flame, Crosshair, Swords, Car, 
  PersonStanding, CheckCircle2, XCircle, Clock,
  Shield, ShieldAlert, ShieldX, ChevronDown, ChevronUp,
  Volume2, VolumeX, Eye
} from "lucide-react"
import { RealTimeAlert } from "@/lib/useAlerts"

// ========================================
// Alert Popup Modal — Shown for each pending alert
// ========================================

interface AlertPopupProps {
  alert: RealTimeAlert
  onConfirm: (alertId: string, note?: string) => Promise<boolean>
  onDismiss: (alertId: string, note?: string) => Promise<boolean>
  onSkip: () => void
  pendingCount: number
}

export function AlertPopup({ alert, onConfirm, onDismiss, onSkip, pendingCount }: AlertPopupProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  const [showNote, setShowNote] = useState(false)
  const [note, setNote] = useState("")
  const [timeElapsed, setTimeElapsed] = useState(0)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  // Timer to show how long the alert has been pending
  useEffect(() => {
    const startTime = alert.timestamp * 1000
    const updateTimer = () => {
      setTimeElapsed(Math.floor((Date.now() - startTime) / 1000))
    }
    updateTimer()
    timerRef.current = setInterval(updateTimer, 1000)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [alert.timestamp])

  const handleConfirm = async () => {
    setIsProcessing(true)
    const success = await onConfirm(alert.alert_id, note || undefined)
    setIsProcessing(false)
    if (!success) {
      console.error("Failed to confirm alert")
    }
  }

  const handleDismiss = async () => {
    setIsProcessing(true)
    const success = await onDismiss(alert.alert_id, note || undefined)
    setIsProcessing(false)
    if (!success) {
      console.error("Failed to dismiss alert")
    }
  }

  const severityConfig = getSeverityConfig(alert.severity)
  const detectionIcon = getDetectionIcon(alert.detection_class)

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-8 pointer-events-none">
      {/* Backdrop with pulse animation for critical */}
      <div 
        className={`fixed inset-0 pointer-events-auto transition-colors duration-300 ${
          alert.severity === "critical" 
            ? "bg-red-950/40 animate-pulse-slow" 
            : "bg-black/30"
        }`}
        onClick={onSkip}
      />
      
      {/* Alert Card */}
      <div className={`
        relative pointer-events-auto w-full max-w-lg mx-4
        rounded-xl shadow-2xl border-2 overflow-hidden
        transform transition-all duration-300 ease-out
        animate-slide-down
        ${severityConfig.borderColor} ${severityConfig.bgColor}
      `}>
        {/* Severity Strip */}
        <div className={`h-1.5 w-full ${severityConfig.stripColor}`} />

        {/* Header */}
        <div className="px-5 pt-4 pb-2">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2.5 rounded-xl ${severityConfig.iconBg} ${severityConfig.iconColor}`}>
                {detectionIcon}
              </div>
              <div>
                <h3 className="text-lg font-bold text-foreground leading-tight">
                  {alert.display_name}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider ${severityConfig.badgeColor}`}>
                    {alert.severity}
                  </span>
                  <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {timeElapsed}s ago
                  </span>
                </div>
              </div>
            </div>
            
            {/* Confidence meter */}
            <div className="text-right">
              <div className="text-2xl font-bold text-foreground">
                {(alert.confidence * 100).toFixed(0)}%
              </div>
              <div className="text-[10px] text-muted-foreground uppercase tracking-wider">
                Confidence
              </div>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="px-5 py-3 space-y-3">
          <p className="text-sm text-muted-foreground leading-relaxed">
            {alert.description}
          </p>

          {/* Snapshot Image */}
          {alert.frame_snapshot_url && (
            <div className="rounded-lg overflow-hidden border border-border">
              <img 
                src={alert.frame_snapshot_url} 
                alt="Detection snapshot"
                className="w-full h-40 object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none'
                }}
              />
            </div>
          )}

          {/* Detection Details */}
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-muted/50 rounded-lg p-2">
              <span className="text-muted-foreground">Camera</span>
              <div className="font-medium text-foreground">{alert.camera_id}</div>
            </div>
            <div className="bg-muted/50 rounded-lg p-2">
              <span className="text-muted-foreground">Type</span>
              <div className="font-medium text-foreground capitalize">{alert.alert_type.replace(/_/g, ' ')}</div>
            </div>
          </div>

          {/* Face match info */}
          {alert.face_id && (
            <div className="flex items-center gap-2 p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <Eye className="h-4 w-4 text-blue-400" />
              <span className="text-xs text-blue-300">
                Person previously flagged — Match score: {((alert.face_match_score || 0) * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* Optional Note */}
          <button 
            onClick={() => setShowNote(!showNote)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            {showNote ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            Add a note (optional)
          </button>
          
          {showNote && (
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add details about this detection..."
              className="w-full h-16 text-sm bg-muted border border-border rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-primary"
            />
          )}
        </div>

        {/* Action Buttons */}
        <div className="px-5 pb-4 pt-1">
          <div className="flex gap-3">
            <button
              onClick={handleConfirm}
              disabled={isProcessing}
              className={`
                flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                font-semibold text-sm transition-all duration-200
                ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-[0.98]'}
                bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-600/25
              `}
            >
              {isProcessing ? (
                <div className="h-4 w-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <CheckCircle2 className="h-4 w-4" />
              )}
              Yes, Real Threat
            </button>
            
            <button
              onClick={handleDismiss}
              disabled={isProcessing}
              className={`
                flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl
                font-semibold text-sm transition-all duration-200
                ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02] active:scale-[0.98]'}
                bg-muted hover:bg-muted/80 text-foreground border border-border
              `}
            >
              {isProcessing ? (
                <div className="h-4 w-4 border-2 border-foreground/30 border-t-foreground rounded-full animate-spin" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              No, False Alarm
            </button>
          </div>
          
          {/* Pending count & skip */}
          {pendingCount > 1 && (
            <div className="flex items-center justify-between mt-3 pt-2 border-t border-border/50">
              <span className="text-xs text-muted-foreground">
                {pendingCount - 1} more alert{pendingCount - 1 > 1 ? 's' : ''} pending
              </span>
              <button
                onClick={onSkip}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors underline"
              >
                Review later
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


// ========================================
// Alert Toast — Small notification in corner
// ========================================

interface AlertToastProps {
  alert: RealTimeAlert
  onClose: () => void
}

export function AlertToast({ alert, onClose }: AlertToastProps) {
  const severityConfig = getSeverityConfig(alert.severity)
  
  useEffect(() => {
    const timer = setTimeout(onClose, 8000)
    return () => clearTimeout(timer)
  }, [onClose])

  return (
    <div className={`
      flex items-center gap-3 p-3 rounded-lg border shadow-lg 
      animate-slide-in-right
      ${severityConfig.borderColor} ${severityConfig.bgColor}
    `}>
      <div className={`p-1.5 rounded-lg ${severityConfig.iconBg} ${severityConfig.iconColor}`}>
        {getDetectionIcon(alert.detection_class, 16)}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">{alert.display_name}</p>
        <p className="text-xs text-muted-foreground">
          {(alert.confidence * 100).toFixed(0)}% confidence · {alert.camera_id}
        </p>
      </div>
      <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
        <XCircle className="h-4 w-4" />
      </button>
    </div>
  )
}


// ========================================
// Connection Status Indicator
// ========================================

interface AlertConnectionStatusProps {
  isConnected: boolean
  error: string | null
  onConnect: () => void
}

export function AlertConnectionStatus({ isConnected, error, onConnect }: AlertConnectionStatusProps) {
  if (isConnected) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-emerald-400">
        <div className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        Live Monitoring
      </div>
    )
  }
  
  return (
    <button 
      onClick={onConnect}
      className="flex items-center gap-1.5 text-xs text-amber-400 hover:text-amber-300 transition-colors"
    >
      <div className="h-2 w-2 rounded-full bg-amber-400" />
      {error ? "Reconnect" : "Connecting..."}
    </button>
  )
}


// ========================================
// Helpers
// ========================================

function getSeverityConfig(severity: string) {
  switch (severity) {
    case "critical":
      return {
        borderColor: "border-red-500/60",
        bgColor: "bg-card",
        stripColor: "bg-gradient-to-r from-red-600 via-red-500 to-orange-500",
        iconBg: "bg-red-500/20",
        iconColor: "text-red-400",
        badgeColor: "bg-red-500/20 text-red-400 border border-red-500/30",
      }
    case "high":
      return {
        borderColor: "border-orange-500/60",
        bgColor: "bg-card",
        stripColor: "bg-gradient-to-r from-orange-600 via-orange-500 to-yellow-500",
        iconBg: "bg-orange-500/20",
        iconColor: "text-orange-400",
        badgeColor: "bg-orange-500/20 text-orange-400 border border-orange-500/30",
      }
    case "medium":
      return {
        borderColor: "border-yellow-500/60",
        bgColor: "bg-card",
        stripColor: "bg-gradient-to-r from-yellow-600 via-yellow-500 to-amber-400",
        iconBg: "bg-yellow-500/20",
        iconColor: "text-yellow-400",
        badgeColor: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
      }
    default:
      return {
        borderColor: "border-blue-500/60",
        bgColor: "bg-card",
        stripColor: "bg-gradient-to-r from-blue-600 via-blue-500 to-cyan-400",
        iconBg: "bg-blue-500/20",
        iconColor: "text-blue-400",
        badgeColor: "bg-blue-500/20 text-blue-400 border border-blue-500/30",
      }
  }
}

function getDetectionIcon(detectionClass: string, size: number = 22) {
  const iconProps = { className: `h-[${size}px] w-[${size}px]`, style: { width: size, height: size } }
  
  switch (detectionClass.toLowerCase()) {
    case "fire":
      return <Flame {...iconProps} />
    case "gun":
      return <Crosshair {...iconProps} />
    case "knife":
      return <ShieldAlert {...iconProps} />
    case "fighting":
      return <Swords {...iconProps} />
    case "road_accident":
      return <Car {...iconProps} />
    case "wallclimb":
      return <PersonStanding {...iconProps} />
    case "suspicious_reappearance":
      return <Eye {...iconProps} />
    default:
      return <AlertTriangle {...iconProps} />
  }
}
