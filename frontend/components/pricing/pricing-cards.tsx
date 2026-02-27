"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, Star, Loader2 } from "lucide-react"
import { useAuth } from "@/components/auth-provider"
import Link from "next/link"
import { useState } from "react"
import { useToast } from "@/components/ui/use-toast"

interface PricingCardsProps {
  billingPeriod: "monthly" | "annual"
}

export function PricingCards({ billingPeriod }: PricingCardsProps) {
  const { user } = useAuth()
  const { toast } = useToast()
  const [loading, setLoading] = useState<string | null>(null)

  const plans = [
    {
      name: "DetectifAI Basic",
      description: "Essential AI-powered security monitoring for single installations",
      monthlyPrice: 19,
      annualPrice: 11.40,
      popular: false,
      planId: "basic",
      features: [
        "Single video feed processing",
        "AI-powered object detection (fire, weapons)",
        "Facial recognition on suspicious frames",
        "7-day event history",
        "Dashboard access",
        "Basic video reports",
        "Video clip generation",
      ],
      limitations: [
        "Single camera/video source only",
        "7-day event retention",
        "Standard processing queue"
      ],
    },
    {
      name: "DetectifAI Pro",
      description: "Advanced security intelligence with extended capabilities",
      monthlyPrice: 49,
      annualPrice: 29.40,
      popular: true,
      planId: "pro",
      features: [
        "Everything in Basic",
        "30-day event history",
        "Advanced behavior analysis",
        "Person re-occurrence tracking",
        "Natural language event search",
        "Image-based face search",
        "Custom report generation",
        "Priority processing queue",
      ],
      limitations: [],
    },
  ]

  const getPrice = (plan: (typeof plans)[0]) => {
    return billingPeriod === "monthly" ? plan.monthlyPrice : plan.annualPrice
  }

  const getSavings = (plan: (typeof plans)[0]) => {
    if (billingPeriod === "annual") {
      const monthlyCost = plan.monthlyPrice * 12
      const annualCost = plan.annualPrice * 12
      return monthlyCost - annualCost
    }
    return 0
  }

  const handleCheckout = async (planId: string) => {
    if (!user) {
      toast({
        title: "Authentication Required",
        description: "Please sign in to subscribe to a plan.",
        variant: "destructive"
      })
      return
    }

    setLoading(planId)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'
      const response = await fetch(`${apiUrl}/api/subscriptions/create-checkout-session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          user_email: user.email,
          plan_name: planId,
          billing_period: billingPeriod === "monthly" ? "monthly" : "yearly"
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to create checkout session')
      }

      // Redirect to Stripe Checkout
      if (data.url) {
        window.location.href = data.url
      }
    } catch (error) {
      console.error('Checkout error:', error)
      toast({
        title: "Checkout Error",
        description: error instanceof Error ? error.message : "Failed to start checkout process",
        variant: "destructive"
      })
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 max-w-5xl mx-auto">
      {plans.map((plan, index) => (
        <Card key={index} className={`relative border-border ${plan.popular ? "ring-2 ring-primary shadow-lg" : ""}`}>
          {plan.popular && (
            <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
              <Badge className="bg-primary text-primary-foreground px-3 py-1">
                <Star className="w-3 h-3 mr-1" />
                Most Popular
              </Badge>
            </div>
          )}

          <CardHeader className="text-center pb-6">
            <CardTitle className="text-2xl font-bold">{plan.name}</CardTitle>
            <CardDescription className="text-muted-foreground text-pretty">{plan.description}</CardDescription>

            <div className="mt-6">
              <div className="flex items-baseline justify-center space-x-1">
                <span className="text-4xl font-bold">${getPrice(plan)}</span>
                <span className="text-muted-foreground">/{billingPeriod === "monthly" ? "month" : "month"}</span>
              </div>

              {billingPeriod === "annual" && (
                <div className="mt-2 text-sm text-muted-foreground">
                  Billed annually • Save ${getSavings(plan)}/year
                </div>
              )}
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Features */}
            <div className="space-y-3">
              {plan.features.map((feature, featureIndex) => (
                <div key={featureIndex} className="flex items-start space-x-3">
                  <Check className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{feature}</span>
                </div>
              ))}

              {plan.limitations.map((limitation, limitIndex) => (
                <div key={limitIndex} className="flex items-start space-x-3 opacity-60">
                  <div className="h-5 w-5 mt-0.5 flex-shrink-0 flex items-center justify-center">
                    <div className="w-3 h-3 border border-muted-foreground rounded-full"></div>
                  </div>
                  <span className="text-sm text-muted-foreground">{limitation}</span>
                </div>
              ))}
            </div>

            {/* CTA Buttons */}
            <div className="space-y-3 pt-4">
              {user ? (
                <>
                  <Button 
                    className="w-full" 
                    variant={plan.popular ? "default" : "outline"}
                    onClick={() => handleCheckout(plan.planId)}
                    disabled={loading === plan.planId}
                  >
                    {loading === plan.planId ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      `Get ${plan.name.split(' ')[1]}`
                    )}
                  </Button>
                </>
              ) : (
                <>
                  <Link href="/signin">
                    <Button className="w-full" variant={plan.popular ? "default" : "outline"}>
                      Get Started
                    </Button>
                  </Link>
                  <p className="text-xs text-center text-muted-foreground">
                    Sign in to subscribe
                  </p>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
