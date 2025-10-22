"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { useEffect, useRef } from "react"

export function PlatformSection() {
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
        <h2 className="text-4xl md:text-6xl font-bold text-white mb-8 text-balance">
          A platform for automating your surveillance tasks
        </h2>

        <p className="text-xl text-gray-400 mb-12 max-w-3xl mx-auto text-pretty">
          Streamline your security operations with intelligent automation that works around the clock to keep your
          premises safe.
        </p>

        <Link href="/signup">
          <Button
            size="lg"
            className="px-12 py-4 text-lg bg-white text-black hover:bg-gray-200 transition-all duration-300 transform hover:scale-105"
          >
            Get Started
          </Button>
        </Link>
      </div>
    </section>
  )
}
