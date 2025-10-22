"use client"

import { useEffect, useRef } from "react"

export function AlertsSection() {
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

  return (
    <section
      ref={sectionRef}
      className="py-32 px-4 sm:px-6 lg:px-8 opacity-0 translate-y-10 transition-all duration-1000"
    >
      <div className="max-w-7xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div className="space-y-8">
            <div className="text-4xl font-bold text-white">GET ALERTS</div>
            <div className="text-4xl font-bold text-white">GET REPORTS</div>
            <div className="text-4xl font-bold text-white">UPLOAD VIDEOS</div>
            <div className="text-4xl font-bold text-white">PROMPT SEARCH</div>
          </div>

          <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center">
                <span className="text-white text-sm font-bold">D</span>
              </div>
              <span className="text-white font-medium">DetectifAI</span>
            </div>

            <div className="mb-6">
              <h3 className="text-xl font-bold text-white mb-2">Good Morning, Kiki</h3>
              <p className="text-gray-400">Here's your daily report</p>
            </div>

            <div className="bg-gray-800 rounded-lg p-4">
              <h4 className="text-white font-medium mb-3">Real-Time Alerts</h4>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                  <span className="text-sm text-gray-300">Dog PM Suspicious activity - Zone 1</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                  <span className="text-sm text-gray-300">11:32 PM Fire detected - Zone 1</span>
                </div>
                <div className="text-xs text-gray-500 mt-2">2 more alerts</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
