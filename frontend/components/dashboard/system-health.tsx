import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Server, Wifi, HardDrive, Cpu } from "lucide-react"

export function SystemHealth() {
  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          System Health
        </CardTitle>
        <CardDescription>Real-time system monitoring</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {/* Server Status */}
          <div className="flex items-center justify-between p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium">Server</span>
            </div>
            <Badge variant="secondary" className="bg-green-500/20 text-green-700">
              Online
            </Badge>
          </div>

          {/* Network Status */}
          <div className="flex items-center justify-between p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
            <div className="flex items-center gap-2">
              <Wifi className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium">Network</span>
            </div>
            <Badge variant="secondary" className="bg-green-500/20 text-green-700">
              Stable
            </Badge>
          </div>

          {/* Storage */}
          <div className="flex items-center justify-between p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <div className="flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-yellow-500" />
              <span className="text-sm font-medium">Storage</span>
            </div>
            <Badge variant="secondary" className="bg-yellow-500/20 text-yellow-700">
              78% Full
            </Badge>
          </div>

          {/* CPU Usage */}
          <div className="flex items-center justify-between p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium">CPU</span>
            </div>
            <Badge variant="secondary" className="bg-green-500/20 text-green-700">
              45%
            </Badge>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
