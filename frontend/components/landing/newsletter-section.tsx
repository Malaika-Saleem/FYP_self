"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useEffect, useRef } from "react"

export function NewsletterSection() {
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
      <div className="max-w-4xl mx-auto text-center">
        <h2 className="text-4xl md:text-5xl font-bold text-white mb-8">Receive Updates</h2>

        <p className="text-xl text-gray-400 mb-12">Stay informed about the latest features and security insights.</p>

        <div className="flex flex-col sm:flex-row gap-4 max-w-md mx-auto">
          <Input
            type="email"
            placeholder="Enter email"
            className="bg-gray-900 border-gray-700 text-white placeholder-gray-400"
          />
          <Button className="bg-white text-black hover:bg-gray-200 transition-all duration-300">Subscribe</Button>
        </div>

        <div className="mt-16 pt-8 border-t border-gray-800">
          <div className="flex items-center justify-center gap-2 text-gray-400">
            <div className="w-6 h-6 bg-purple-500 rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-bold">D</span>
            </div>
            <span>DetectifAI</span>
          </div>
        </div>
      </div>
    </section>
  )
}
