"use client"

import { Badge } from "@/components/ui/badge"

interface PricingToggleProps {
  billingPeriod: "monthly" | "annual"
  onToggle: (period: "monthly" | "annual") => void
}

export function PricingToggle({ billingPeriod, onToggle }: PricingToggleProps) {
  return (
    <div className="flex items-center justify-center space-x-4">
      <span
        className={`text-sm ${billingPeriod === "monthly" ? "text-foreground font-medium" : "text-muted-foreground"}`}
      >
        Monthly
      </span>

      <button
        onClick={() => onToggle(billingPeriod === "monthly" ? "annual" : "monthly")}
        className="relative inline-flex h-6 w-11 items-center rounded-full bg-muted transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-primary transition-transform ${
            billingPeriod === "annual" ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>

      <div className="flex items-center space-x-2">
        <span
          className={`text-sm ${billingPeriod === "annual" ? "text-foreground font-medium" : "text-muted-foreground"}`}
        >
          Annual
        </span>
        <Badge variant="secondary" className="text-xs bg-primary/10 text-primary border-primary/20">
          Save 40%
        </Badge>
      </div>
    </div>
  )
}
