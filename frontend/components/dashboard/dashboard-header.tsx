"use client"

import { useEffect, useState } from "react"
import { Shield, Zap, Activity, LogOut } from "lucide-react"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/components/auth-provider"

interface User {
  id: string
  email: string
  name: string
  organization?: string
  role: "admin" | "user"
}

interface DashboardHeaderProps {
  user: User
}

export function DashboardHeader({ user }: DashboardHeaderProps) {
  const { logout } = useAuth()
  const [greeting, setGreeting] = useState("")

  useEffect(() => {
    const hour = new Date().getHours()
    if (hour < 12) {
      setGreeting("Good Morning")
    } else if (hour < 18) {
      setGreeting("Good Afternoon")
    } else {
      setGreeting("Good Evening")
    }
  }, [])

  return (
    <div className="bg-card p-6 border-b border-border shadow-lg shadow-purple-500/20 hover:shadow-purple-500/30 transition-shadow">
      <div className="text-center space-y-6 mb-6">
       

        <h1 className="text-4xl md:text-5xl font-bold text-balance">Choose Your Security Plan</h1>

        <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-pretty">
          Flexible pricing designed for security teams of all sizes. Start with our basic plan and scale as your
          surveillance needs grow.
        </p>

        <div className="flex items-center justify-center space-x-8 text-sm text-muted-foreground">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-primary rounded-full"></div>
            <span>No setup fees</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-primary rounded-full"></div>
            <span>Cancel anytime</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-primary rounded-full"></div>
            <span>24/7 support</span>
          </div>
        </div>
      </div>
      <div className="flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-4">
          <Image src="/logo.png" alt="DetectifAI" width={40} height={40} />
          <div>
            <h1 className="text-2xl font-bold text-foreground mb-2">
              {greeting}, {user.name.split(" ")[0]}
            </h1>
            <div className="flex items-center space-x-2 text-muted-foreground">
              <Activity className="h-4 w-4 text-zone-indicator" />
              <span>Monitoring your feed now!</span>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-4">
          <div className="text-right">
            <div className="text-sm text-muted-foreground">Organization</div>
            <div className="font-medium text-white">{user.organization}</div>
          </div>
          <div className="p-3 bg-primary/10 rounded-full">
            <Shield className="h-6 w-6 text-primary" />
          </div>
        </div>
      </div>
    </div>
  )
}
