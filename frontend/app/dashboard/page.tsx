"use client"

import { useAuth } from "@/components/auth-provider"
import { DashboardHeader } from "@/components/dashboard/dashboard-header"
import { UserDashboard } from "@/components/dashboard/user-dashboard"
import { AdminDashboard } from "@/components/dashboard/admin-dashboard"
import { SubscriptionProvider } from "@/contexts/subscription-context"
import { useRouter } from "next/navigation"
import { useEffect } from "react"

export default function DashboardPage() {
  const { user, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/signin")
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <SubscriptionProvider>
      <div className="min-h-screen bg-background">
        <main className="p-6">
          <div className="max-w-7xl mx-auto space-y-6">
            <DashboardHeader user={user} />
            {user.role === "admin" ? (
              <AdminDashboard />
            ) : (
              <UserDashboard userRole={user.role} />
            )}
          </div>
        </main>
      </div>
    </SubscriptionProvider>
  )
}
