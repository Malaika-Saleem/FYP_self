"use client"

import Link from "next/link"
import { TrendingUp } from "lucide-react"
import { useEffect, useRef } from "react"

export function AnalyticsSection() {
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

  const analytics = [
    { label: "Fighting", count: 3, trend: "up" },
    { label: "Car Accidents", count: 5, trend: "up" },
    { label: "Fire Detected", count: 0, trend: "neutral" },
    { label: "Guns Detected", count: 1, trend: "up" },
    { label: "Trespassing", count: 8, trend: "up" },
  ]

  return (
    <section
      ref={sectionRef}
      className="py-32 px-4 sm:px-6 lg:px-8 opacity-0 translate-y-10 transition-all duration-1000"
    >
      <div className="max-w-4xl mx-auto text-center mb-16">
        <h2 className="text-4xl md:text-5xl font-bold text-white mb-8">
          Get analysis of your video footages in one click
        </h2>

        <p className="text-xl text-gray-400 mb-12">
          Our AI analyzes your surveillance footage and provides detailed insights about security events.
        </p>

        <Link
          href="/dashboard"
          className="inline-flex items-center text-purple-400 hover:text-purple-300 transition-colors"
        >
          Explore Dashboard →
        </Link>
      </div>

      <div className="max-w-2xl mx-auto bg-gray-900 rounded-2xl p-8 border border-gray-800">
        <div className="space-y-6">
          {analytics.map((item, index) => (
            <div
              key={item.label}
              className="flex items-center justify-between p-4 bg-gray-800 rounded-lg"
              style={{ animationDelay: `${index * 100}ms` }}
            >
              <span className="text-white font-medium">{item.label}</span>
              <div className="flex items-center gap-4">
                <span className="text-2xl font-bold text-white">{item.count}</span>
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-purple-400" />
                  <span className="text-purple-400 text-sm">Check Now →</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
