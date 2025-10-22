"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, Star } from "lucide-react"
import { useAuth } from "@/components/auth-provider"
import Link from "next/link"

interface PricingCardsProps {
  billingPeriod: "monthly" | "annual"
}

export function PricingCards({ billingPeriod }: PricingCardsProps) {
  const { user } = useAuth()

  const plans = [
    {
      name: "DetectifAI Basic",
      description: "Perfect for small security teams getting started",
      monthlyPrice: 19,
      annualPrice: 11,
      popular: false,
      features: [
        "Basic CCTV integration",
        "Dashboard access",
        "7-day event history",
        "Email alerts",
        "Up to 5 cameras",
        "Standard support",
      ],
      limitations: ["Limited search queries (50/month)", "Basic reporting"],
    },
    {
      name: "DetectifAI Pro",
      description: "Advanced features for professional security operations",
      monthlyPrice: 49,
      annualPrice: 29,
      popular: true,
      features: [
        "Everything in Basic",
        "Unlimited camera feeds",
        "Real-time AI search",
        "Advanced behavioral detection",
        "Custom report generation",
        "30-day event history",
        "SMS & webhook alerts",
        "Priority support",
        "API access",
        "Custom integrations",
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
                  <Button className="w-full" variant={plan.popular ? "default" : "outline"}>
                    {plan.popular ? "Upgrade to Pro" : "Switch to Basic"}
                  </Button>
                  <Button variant="outline" className="w-full bg-transparent">
                    Edit Plan
                  </Button>
                </>
              ) : (
                <>
                  <Link href="/signup">
                    <Button className="w-full" variant={plan.popular ? "default" : "outline"}>
                      Get Started
                    </Button>
                  </Link>
                  <Button variant="outline" className="w-full bg-transparent">
                    Try for free (7 days)
                  </Button>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
