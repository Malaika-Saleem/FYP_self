"use client"

import { PricingHeader } from "@/components/pricing/pricing-header"
import { PricingToggle } from "@/components/pricing/pricing-toggle"
import { PricingCards } from "@/components/pricing/pricing-cards"
import { PricingFAQ } from "@/components/pricing/pricing-faq"
import { useState } from "react"

export default function PricingPage() {
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "annual">("monthly")

  return (
    <div className="min-h-screen bg-background">
      <main className="pt-20 pb-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <PricingHeader />
          <PricingToggle billingPeriod={billingPeriod} onToggle={setBillingPeriod} />
          <PricingCards billingPeriod={billingPeriod} />
          <PricingFAQ />
        </div>
      </main>
    </div>
  )
}
