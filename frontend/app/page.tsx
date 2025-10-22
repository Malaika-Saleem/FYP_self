import { NewHeroSection } from "@/components/landing/new-hero-section"
import { NewFeatureCards } from "@/components/landing/new-feature-cards"
import { PlatformSection } from "@/components/landing/platform-section"
import { PricingSection } from "@/components/landing/pricing-section"
import { AnalyticsSection } from "@/components/landing/analytics-section"
import { AlertsSection } from "@/components/landing/alerts-section"
import { NewsletterSection } from "@/components/landing/newsletter-section"

export default function HomePage() {
  return (
    <div className="min-h-screen bg-black text-white overflow-x-hidden">
      <main>
        <NewHeroSection />
        <NewFeatureCards />
        <PlatformSection />
        <PricingSection />
        <AnalyticsSection />
        <AlertsSection />
        <NewsletterSection />
      </main>
    </div>
  )
}
