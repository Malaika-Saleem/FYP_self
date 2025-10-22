import { DashboardWidgets } from "./dashboard-widgets"
import { KeyStatistics } from "./key-statistics"
import { AdminControls } from "./admin-controls"
import { SystemHealth } from "./system-health"

export function AdminDashboard() {
  return (
    <div className="space-y-6">
      {/* Admin gets full access to all widgets */}
      <DashboardWidgets key="admin-dashboard" />

      {/* Admin-specific controls */}
      <AdminControls key="admin-controls" />

      {/* System health monitoring */}
      <SystemHealth key="system-health" />

      {/* Key statistics */}
      <KeyStatistics key="key-statistics" />
    </div>
  )
}
