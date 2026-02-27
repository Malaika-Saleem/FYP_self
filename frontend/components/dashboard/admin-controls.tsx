"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Settings, Users, Database, Shield } from "lucide-react"
import { useRouter } from "next/navigation"

export function AdminControls() {
  const router = useRouter()

  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-primary" />
          Admin Controls
        </CardTitle>
        <CardDescription>System management and configuration</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* User Management */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-primary" />
              <span className="font-medium">User Management</span>
            </div>
            <div className="text-sm text-muted-foreground mb-2">Manage user accounts and permissions</div>
            <Button 
              variant="outline" 
              size="sm" 
              className="w-full bg-transparent"
              onClick={() => router.push("/admin/users")}
            >
              Manage Users
            </Button>
          </div>

          {/* System Settings */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Settings className="w-4 h-4 text-primary" />
              <span className="font-medium">System Settings</span>
            </div>
            <div className="text-sm text-muted-foreground mb-2">Configure surveillance parameters</div>
            <Button 
              variant="outline" 
              size="sm" 
              className="w-full bg-transparent"
              onClick={() => router.push("/admin/settings")}
            >
              Settings
            </Button>
          </div>

          {/* Database Management */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Database className="w-4 h-4 text-primary" />
              <span className="font-medium">Database</span>
            </div>
            <div className="text-sm text-muted-foreground mb-2">Backup and maintenance tools</div>
            <Button 
              variant="outline" 
              size="sm" 
              className="w-full bg-transparent"
              onClick={() => router.push("/admin/database")}
            >
              Database Tools
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
