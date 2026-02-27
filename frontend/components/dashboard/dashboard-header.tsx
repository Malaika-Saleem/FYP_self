"use client"

import { useEffect, useState } from "react"
import { Shield, Zap, Activity, LogOut, Crown, Star } from "lucide-react"
import Image from "next/image"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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

interface SubscriptionData {
  has_subscription: boolean
  plan_name?: string
  status?: string
  billing_period?: string
}

export function DashboardHeader({ user }: DashboardHeaderProps) {
  const { logout } = useAuth()
  const [greeting, setGreeting] = useState("")
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null)
  const [loadingSubscription, setLoadingSubscription] = useState(true)

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

  useEffect(() => {
    const fetchSubscription = async () => {
      if (!user?.id) return

      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/subscriptions/status?user_id=${user.id}`
        )
        
        if (response.ok) {
          const data = await response.json()
          if (data.success) {
            setSubscription(data)
          }
        }
      } catch (error) {
        console.error('Error fetching subscription:', error)
      } finally {
        setLoadingSubscription(false)
      }
    }

    fetchSubscription()
  }, [user?.id])

  return (
    <div className="bg-card p-6 border-b border-border shadow-lg shadow-purple-500/20 hover:shadow-purple-500/30 transition-shadow">
      {/* Plan Header Section */}
      {!loadingSubscription && (
        <div className="text-center space-y-6 mb-6">
          {subscription?.has_subscription && subscription.status === 'active' ? (
            // Active Subscription Header
            <>
              <div className="flex items-center justify-center gap-3">
                {subscription.plan_name?.includes('Pro') ? (
                  <Crown className="w-8 h-8 text-purple-500" />
                ) : (
                  <Star className="w-8 h-8 text-purple-500" />
                )}
                <h1 className="text-4xl md:text-5xl font-bold text-balance text-purple-500">
                  {subscription.plan_name}
                </h1>
                <Badge className="ml-2 bg-green-500/10 text-green-600 border-green-500/20">
                  {subscription.status?.toUpperCase()}
                </Badge>
              </div>

              <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-pretty">
                Your subscription is active. {subscription.plan_name?.includes('Pro') ? 
                  'Enjoy advanced AI security features with priority support.' :
                  'Essential AI-powered monitoring for your security needs.'
                }
              </p>

              <div className="flex items-center justify-center space-x-8 text-sm text-muted-foreground">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-primary rounded-full"></div>
                  <span className="capitalize">{subscription.billing_period} billing</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-primary rounded-full"></div>
                  <Link href="/dashboard/subscription" className="hover:text-primary transition">
                    Manage subscription
                  </Link>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 bg-primary rounded-full"></div>
                  <span>24/7 support</span>
                </div>
              </div>
            </>
          ) : (
            // No Subscription Header
            <>
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
                  <Link href="/pricing" className="hover:text-primary transition">
                    View plans
                  </Link>
                </div>
              </div>
            </>
          )}
        </div>
      )}
      
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
