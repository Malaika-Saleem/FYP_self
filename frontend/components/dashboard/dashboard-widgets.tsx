"use client"
import { SearchReportWidget } from "@/components/dashboard/widgets/search-report-widget"
import { VideoWidget } from "@/components/dashboard/widgets/video-widget"
import { AlertsWidget } from "@/components/dashboard/widgets/alerts-widget"
import { KeyStatistics } from "@/components/dashboard/key-statistics"

export function DashboardWidgets() {
  return (
    <div className="space-y-6">
      <SearchReportWidget />
      <VideoWidget />
      <AlertsWidget />
      <KeyStatistics />
    </div>
  )
}
