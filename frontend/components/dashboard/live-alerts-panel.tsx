"use client"

import { useState } from "react"
import {
  AlertTriangle, CheckCircle2, XCircle, Clock, Filter,
  Flame, Crosshair, Swords, Car, PersonStanding, Eye,
  ShieldAlert, ShieldCheck, Shield, Bell, BellOff,
  ChevronDown, BarChart3, Wifi, WifiOff
} from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { RealTimeAlert, AlertStats } from "@/lib/useAlerts"
import { AlertConnectionStatus } from "./alert-popup"

// ========================================
// Live Alerts Panel — Full alert feed
// ========================================

interface LiveAlertsPanelProps {
  alerts: RealTimeAlert[]
  pendingAlerts: RealTimeAlert[]
  stats: AlertStats | null
  isConnected: boolean
  connectionError: string | null
  onConnect: () => void
  onConfirm: (alertId: string, note?: string) => Promise<boolean>
  onDismiss: (alertId: string, note?: string) => Promise<boolean>
  onTestAlert?: (detectionClass: string) => void
}

export function LiveAlertsPanel({
  alerts,
  pendingAlerts,
  stats,
  isConnected,
  connectionError,
  onConnect,
  onConfirm,
  onDismiss,
  onTestAlert,
}: LiveAlertsPanelProps) {
  const [filterSeverity, setFilterSeverity] = useState<string>("all")
  const [filterStatus, setFilterStatus] = useState<string>("all")
  const [showFilters, setShowFilters] = useState(false)

  const filteredAlerts = alerts.filter(alert => {
    if (filterSeverity !== "all" && alert.severity !== filterSeverity) return false
    if (filterStatus !== "all" && alert.status !== filterStatus) return false
    return true
  })

  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-primary" />
              <span>Real-Time Alerts</span>
            </CardTitle>
            {pendingAlerts.length > 0 && (
              <span className="relative flex h-6 w-6">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex items-center justify-center rounded-full h-6 w-6 bg-red-500 text-white text-xs font-bold">
                  {pendingAlerts.length}
                </span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <AlertConnectionStatus 
              isConnected={isConnected} 
              error={connectionError}
              onConnect={onConnect}
            />
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              <Filter className="h-4 w-4" />
            </button>
          </div>
        </div>
        <CardDescription>
          Live security alerts from AI detection pipeline
        </CardDescription>

        {/* Filters */}
        {showFilters && (
          <div className="flex flex-wrap gap-2 pt-2">
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="text-xs bg-muted border border-border rounded-md px-2 py-1 text-foreground"
            >
              <option value="all">All Severity</option>
              <option value="critical">🔴 Critical</option>
              <option value="high">🟠 High</option>
              <option value="medium">🟡 Medium</option>
              <option value="low">🔵 Low</option>
            </select>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="text-xs bg-muted border border-border rounded-md px-2 py-1 text-foreground"
            >
              <option value="all">All Status</option>
              <option value="pending">⏳ Pending</option>
              <option value="confirmed">✅ Confirmed</option>
              <option value="dismissed">❌ Dismissed</option>
            </select>

            {/* Test buttons (development) */}
            {onTestAlert && (
              <div className="flex gap-1 ml-auto">
                <button
                  onClick={() => onTestAlert("fire")}
                  className="text-[10px] px-2 py-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors"
                >
                  Test Fire
                </button>
                <button
                  onClick={() => onTestAlert("gun")}
                  className="text-[10px] px-2 py-1 bg-orange-500/20 text-orange-400 rounded hover:bg-orange-500/30 transition-colors"
                >
                  Test Gun
                </button>
                <button
                  onClick={() => onTestAlert("fighting")}
                  className="text-[10px] px-2 py-1 bg-yellow-500/20 text-yellow-400 rounded hover:bg-yellow-500/30 transition-colors"
                >
                  Test Fight
                </button>
                <button
                  onClick={() => onTestAlert("knife")}
                  className="text-[10px] px-2 py-1 bg-purple-500/20 text-purple-400 rounded hover:bg-purple-500/30 transition-colors"
                >
                  Test Knife
                </button>
                <button
                  onClick={() => onTestAlert("wallclimb")}
                  className="text-[10px] px-2 py-1 bg-blue-500/20 text-blue-400 rounded hover:bg-blue-500/30 transition-colors"
                >
                  Test Climb
                </button>
              </div>
            )}
          </div>
        )}

        {/* Quick Stats Bar */}
        {stats && (
          <div className="flex gap-3 pt-2">
            <StatBadge label="Total" value={stats.total_alerts} color="text-foreground" />
            <StatBadge label="Confirmed" value={stats.confirmed_alerts} color="text-red-400" icon={<ShieldCheck className="h-3 w-3" />} />
            <StatBadge label="Dismissed" value={stats.dismissed_alerts} color="text-green-400" icon={<ShieldAlert className="h-3 w-3" />} />
            <StatBadge label="Pending" value={stats.active_pending_count} color="text-yellow-400" icon={<Clock className="h-3 w-3" />} />
          </div>
        )}
      </CardHeader>

      <CardContent>
        <div className="space-y-2 max-h-[400px] overflow-y-auto pr-1 custom-scrollbar">
          {filteredAlerts.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Shield className="h-10 w-10 mb-3 opacity-40" />
              <p className="text-sm font-medium">No alerts detected</p>
              <p className="text-xs mt-1">
                {isConnected 
                  ? "System is monitoring. Alerts will appear here in real-time."
                  : "Connect to start receiving alerts."}
              </p>
            </div>
          ) : (
            filteredAlerts.map((alert) => (
              <AlertListItem
                key={alert.alert_id}
                alert={alert}
                onConfirm={onConfirm}
                onDismiss={onDismiss}
              />
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}


// ========================================
// Alert List Item
// ========================================

interface AlertListItemProps {
  alert: RealTimeAlert
  onConfirm: (alertId: string, note?: string) => Promise<boolean>
  onDismiss: (alertId: string, note?: string) => Promise<boolean>
}

function AlertListItem({ alert, onConfirm, onDismiss }: AlertListItemProps) {
  const [isProcessing, setIsProcessing] = useState(false)
  
  const severityColor = {
    critical: "bg-red-500",
    high: "bg-orange-500", 
    medium: "bg-yellow-500",
    low: "bg-blue-500"
  }[alert.severity] || "bg-gray-500"

  const statusIcon = {
    pending: <Clock className="h-3.5 w-3.5 text-yellow-400" />,
    confirmed: <CheckCircle2 className="h-3.5 w-3.5 text-red-400" />,
    dismissed: <XCircle className="h-3.5 w-3.5 text-green-400" />,
    auto_expired: <Clock className="h-3.5 w-3.5 text-gray-400" />,
  }[alert.status] || null

  const handleAction = async (action: "confirm" | "dismiss") => {
    setIsProcessing(true)
    if (action === "confirm") {
      await onConfirm(alert.alert_id)
    } else {
      await onDismiss(alert.alert_id)
    }
    setIsProcessing(false)
  }

  const timeAgo = getTimeAgo(alert.timestamp)

  return (
    <div className={`
      flex items-start gap-3 p-3 rounded-lg border transition-all duration-200
      ${alert.status === "pending" 
        ? "bg-muted/80 border-border hover:border-primary/40" 
        : "bg-muted/40 border-border/50 opacity-75"
      }
    `}>
      {/* Severity indicator */}
      <div className={`w-2.5 h-2.5 rounded-full ${severityColor} mt-1.5 flex-shrink-0 ${
        alert.status === "pending" && alert.severity === "critical" ? "animate-pulse" : ""
      }`} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-1">
          <div className="flex items-center gap-2">
            <h4 className="font-medium text-sm text-foreground truncate">
              {alert.display_name}
            </h4>
            {statusIcon}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground flex-shrink-0">
            <Clock className="h-3 w-3" />
            <span>{timeAgo}</span>
          </div>
        </div>
        
        <p className="text-xs text-muted-foreground mb-1.5 line-clamp-2">
          {alert.description}
        </p>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded text-muted-foreground">
              {(alert.confidence * 100).toFixed(0)}% conf.
            </span>
            <span className="text-[10px] px-1.5 py-0.5 bg-muted rounded text-muted-foreground">
              {alert.camera_id}
            </span>
            {alert.face_id && (
              <span className="text-[10px] px-1.5 py-0.5 bg-blue-500/20 rounded text-blue-400 flex items-center gap-1">
                <Eye className="h-2.5 w-2.5" /> Tracked
              </span>
            )}
          </div>

          {/* Inline action buttons for pending alerts */}
          {alert.status === "pending" && (
            <div className="flex gap-1.5">
              <button
                onClick={() => handleAction("confirm")}
                disabled={isProcessing}
                className="text-[10px] px-2 py-1 bg-red-500/20 text-red-400 rounded hover:bg-red-500/30 transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                <CheckCircle2 className="h-3 w-3" />
                Confirm
              </button>
              <button
                onClick={() => handleAction("dismiss")}
                disabled={isProcessing}
                className="text-[10px] px-2 py-1 bg-muted text-muted-foreground rounded hover:bg-muted/80 transition-colors disabled:opacity-50 flex items-center gap-1"
              >
                <XCircle className="h-3 w-3" />
                Dismiss
              </button>
            </div>
          )}

          {/* Status label for resolved alerts */}
          {alert.status === "confirmed" && (
            <span className="text-[10px] px-2 py-0.5 bg-red-500/10 text-red-400 rounded-full font-medium">
              ✓ Confirmed Threat
            </span>
          )}
          {alert.status === "dismissed" && (
            <span className="text-[10px] px-2 py-0.5 bg-green-500/10 text-green-400 rounded-full font-medium">
              ✗ False Positive
            </span>
          )}
        </div>
      </div>
    </div>
  )
}


// ========================================
// Stat Badge
// ========================================

function StatBadge({ label, value, color, icon }: { 
  label: string; value: number; color: string; icon?: React.ReactNode 
}) {
  return (
    <div className="flex items-center gap-1.5 text-xs">
      {icon}
      <span className={`font-bold ${color}`}>{value}</span>
      <span className="text-muted-foreground">{label}</span>
    </div>
  )
}


// ========================================
// Helpers
// ========================================

function getTimeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() / 1000) - timestamp)
  
  if (seconds < 10) return "just now"
  if (seconds < 60) return `${seconds}s ago`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}
