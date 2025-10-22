"use client"

import { useAuth } from "@/components/auth-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Users, DollarSign, Settings, LogOut } from "lucide-react"
import Link from "next/link"
import Image from "next/image"

export default function AdminDashboard() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-gray-800 bg-card">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Image src="/logo.png" alt="DetectifAI" width={32} height={32} />
            <span className="text-xl font-bold text-white">DetectifAI Admin</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">Welcome, {user?.name}</span>
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-8">Admin Dashboard</h1>

          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <Card className="bg-card border-gray-800">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Total Users</CardTitle>
                <Users className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-white">1,234</div>
                <p className="text-xs text-muted-foreground">+12% from last month</p>
              </CardContent>
            </Card>

            <Card className="bg-card border-gray-800">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Monthly Revenue</CardTitle>
                <DollarSign className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-white">$45,231</div>
                <p className="text-xs text-muted-foreground">+8% from last month</p>
              </CardContent>
            </Card>

            <Card className="bg-card border-gray-800">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">Active Subscriptions</CardTitle>
                <Settings className="h-4 w-4 text-primary" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-white">892</div>
                <p className="text-xs text-muted-foreground">+5% from last month</p>
              </CardContent>
            </Card>
          </div>

          {/* Admin Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="bg-card border-gray-800">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Users className="h-5 w-5 text-primary" />
                  User Management
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">Manage user accounts, permissions, and access levels.</p>
                <Link href="/admin/users">
                  <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">Manage Users</Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="bg-card border-gray-800">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <DollarSign className="h-5 w-5 text-primary" />
                  Pricing Management
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground mb-4">Update pricing plans, features, and subscription options.</p>
                <Link href="/admin/pricing">
                  <Button className="bg-primary hover:bg-primary/90 text-primary-foreground">Manage Pricing</Button>
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}
