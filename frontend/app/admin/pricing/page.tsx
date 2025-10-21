"use client"

import { useState } from "react"
import { useAuth } from "@/components/auth-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ArrowLeft, Save, Edit } from "lucide-react"
import Link from "next/link"
import Image from "next/image"

// Mock pricing data
const initialPricing = [
  {
    id: 1,
    name: "Basic",
    price: 29,
    features: ["Up to 5 cameras", "Basic analytics", "Email support", "7-day storage"],
  },
  {
    id: 2,
    name: "Pro",
    price: 79,
    features: ["Up to 20 cameras", "Advanced analytics", "Priority support", "30-day storage", "Custom alerts"],
  },
  {
    id: 3,
    name: "Enterprise",
    price: 199,
    features: [
      "Unlimited cameras",
      "AI-powered analytics",
      "24/7 phone support",
      "90-day storage",
      "Custom integrations",
      "Dedicated account manager",
    ],
  },
]

export default function AdminPricing() {
  const { user, logout } = useAuth()
  const [pricing, setPricing] = useState(initialPricing)
  const [editingPlan, setEditingPlan] = useState<number | null>(null)

  const handlePriceChange = (planId: number, newPrice: number) => {
    setPricing(pricing.map((plan) => (plan.id === planId ? { ...plan, price: newPrice } : plan)))
  }

  const handleSave = () => {
    setEditingPlan(null)
    // In a real app, this would save to the backend
    console.log("Pricing updated:", pricing)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Image src="/logo.png" alt="DetectifAI" width={32} height={32} />
            <span className="text-xl font-bold text-white">DetectifAI Admin</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">Welcome, {user?.name}</span>
            <Button variant="ghost" size="sm" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6">
        <div className="max-w-6xl mx-auto">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 mb-6">
            <Link href="/admin/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
          </div>

          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-white">Pricing Management</h1>
            <Button onClick={handleSave} className="bg-primary hover:bg-primary/90 text-primary-foreground">
              <Save className="h-4 w-4 mr-2" />
              Save Changes
            </Button>
          </div>

          {/* Pricing Plans */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {pricing.map((plan) => (
              <Card key={plan.id} className="bg-card border-border">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-white">{plan.name}</CardTitle>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingPlan(editingPlan === plan.id ? null : plan.id)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="mb-4">
                    {editingPlan === plan.id ? (
                      <div className="space-y-2">
                        <Label htmlFor={`price-${plan.id}`} className="text-muted-foreground">
                          Monthly Price ($)
                        </Label>
                        <Input
                          id={`price-${plan.id}`}
                          type="number"
                          value={plan.price}
                          onChange={(e) => handlePriceChange(plan.id, Number.parseInt(e.target.value))}
                          className="bg-input border-border text-white"
                        />
                      </div>
                    ) : (
                      <div className="text-3xl font-bold text-white">
                        ${plan.price}
                        <span className="text-sm text-muted-foreground font-normal">/month</span>
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <h4 className="font-medium text-white">Features:</h4>
                    <ul className="space-y-1">
                      {plan.features.map((feature, index) => (
                        <li key={index} className="text-sm text-muted-foreground flex items-center">
                          <span className="w-2 h-2 bg-primary rounded-full mr-2"></span>
                          {feature}
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
