"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Search, BarChart3, CreditCard } from "lucide-react"
import { useEffect, useRef } from "react"

export function NewFeatureCards() {
  const sectionRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("animate-fade-in-up")
          }
        })
      },
      { threshold: 0.1 },
    )

    if (sectionRef.current) {
      observer.observe(sectionRef.current)
    }

    return () => observer.disconnect()
  }, [])

  const features = [
    {
      icon: Search,
      title: "Search Videos",
      description: "Quickly find specific moments in your surveillance footage with AI-powered search capabilities.",
      action: "Start Searching",
      href: "/search",
    },
    {
      icon: BarChart3,
      title: "Dashboard",
      description: "Monitor your security system with real-time analytics and comprehensive reporting tools.",
      action: "Get Dashboard",
      href: "/dashboard",
    },
    {
      icon: CreditCard,
      title: "Get Pricing",
      description: "Choose from flexible pricing plans designed to scale with your surveillance needs.",
      action: "Check Packages",
      href: "/pricing",
    },
  ]

  return (
    <section
      ref={sectionRef}
      className="py-24 px-4 sm:px-6 lg:px-8 opacity-0 translate-y-10 transition-all duration-1000"
    >
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div
              key={feature.title}
              className="bg-gray-900 rounded-2xl p-8 border border-gray-800 hover:border-purple-500 transition-all duration-300 transform hover:scale-105"
              style={{ animationDelay: `${index * 200}ms` }}
            >
              <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mb-6">
                <feature.icon className="w-8 h-8 text-purple-400" />
              </div>

              <h3 className="text-2xl font-bold text-white mb-4">{feature.title}</h3>

              <p className="text-gray-400 mb-8 leading-relaxed">{feature.description}</p>

              <Link href={feature.href}>
                <Button
                  variant="outline"
                  className="w-full bg-transparent border-purple-500 text-purple-400 hover:bg-purple-500 hover:text-white transition-all duration-300"
                >
                  {feature.action} →
                </Button>
              </Link>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
