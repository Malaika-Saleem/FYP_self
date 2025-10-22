"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle, Clock, MapPin } from "lucide-react"

export function AlertsWidget() {
  const alerts = [
    {
      id: 1,
      type: "Suspicious activity",
      zone: "Zone 3",
      time: "10:42 PM",
      severity: "high",
      description: "Person loitering near entrance",
    },
    {
      id: 2,
      type: "Fire detected",
      zone: "Zone 1",
      time: "9:15 PM",
      severity: "critical",
      description: "Smoke detected in storage area",
    },
    {
      id: 3,
      type: "Trespassing",
      zone: "Zone 2",
      time: "8:30 PM",
      severity: "medium",
      description: "Unauthorized access attempt",
    },
  ]

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical":
        return "bg-red-500"
      case "high":
        return "bg-orange-500"
      case "medium":
        return "bg-yellow-500"
      default:
        return "bg-gray-500"
    }
  }

  return (
    <Card className="border-border">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <AlertTriangle className="h-5 w-5 text-primary" />
          <span>Real-Time Alerts</span>
        </CardTitle>
        <CardDescription>Live security alerts and incident notifications</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div key={alert.id} className="flex items-start space-x-3 p-3 bg-muted rounded-lg border border-border">
              <div className={`w-3 h-3 rounded-full ${getSeverityColor(alert.severity)} mt-1 flex-shrink-0`}></div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="font-medium text-sm">{alert.type}</h4>
                  <div className="flex items-center space-x-2 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    <span>{alert.time}</span>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground mb-2">{alert.description}</p>
                <div className="flex items-center space-x-1">
                  <MapPin className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs text-muted-foreground">{alert.zone}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
