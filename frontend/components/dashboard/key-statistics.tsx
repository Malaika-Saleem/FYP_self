"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { TrendingUp, AlertTriangle, Activity, MapPin } from "lucide-react"

export function KeyStatistics() {
  const stats = [
    {
      label: "Total Incidents Today",
      value: "12",
      icon: <TrendingUp className="h-5 w-5 text-primary" />,
      change: "+3 from yesterday",
    },
    {
      label: "Active Alerts",
      value: "3",
      icon: <AlertTriangle className="h-5 w-5 text-red-500" />,
      change: "2 high priority",
    },
    {
      label: "Most Common",
      value: "Fighting",
      icon: <Activity className="h-5 w-5 text-orange-500" />,
      change: "4 incidents today",
    },
    {
      label: "Most Active Zone",
      value: "Zone 3",
      icon: <MapPin className="h-5 w-5 text-green-500" />,
      change: "Main entrance area",
    },
  ]

  return (
    <Card className="border-border">
      <CardHeader>
        <CardTitle>Key Statistics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, index) => (
            <div key={index} className="text-center">
              <div className="flex items-center justify-center mb-2">{stat.icon}</div>
              <div className="text-2xl font-bold mb-1">{stat.value}</div>
              <div className="text-sm font-medium text-foreground mb-1">{stat.label}</div>
              <div className="text-xs text-muted-foreground">{stat.change}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
