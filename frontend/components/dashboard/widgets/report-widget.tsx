"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { FileText, Download } from "lucide-react"

export function ReportWidget() {
  return (
    <Card className="border-border">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <FileText className="h-5 w-5 text-primary" />
          <span>Generate Report</span>
        </CardTitle>
        <CardDescription>Get summary of all suspicious behaviours and alerts</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="bg-muted rounded-lg p-4 border border-border">
          <h4 className="font-medium mb-2">Latest Report Summary</h4>
          <div className="space-y-2 text-sm text-muted-foreground">
            <div className="flex justify-between">
              <span>Total Incidents Today:</span>
              <span className="font-medium text-foreground">12</span>
            </div>
            <div className="flex justify-between">
              <span>High Priority Alerts:</span>
              <span className="font-medium text-red-500">3</span>
            </div>
            <div className="flex justify-between">
              <span>Most Active Zone:</span>
              <span className="font-medium text-foreground">Zone 3</span>
            </div>
          </div>
        </div>

        <div className="flex space-x-2">
          <Button className="flex-1">
            <FileText className="mr-2 h-4 w-4" />
            Get Report
          </Button>
          <Button variant="outline" size="icon">
            <Download className="h-4 w-4" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
