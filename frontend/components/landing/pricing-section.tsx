"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { useEffect, useRef } from "react"

export function PricingSection() {
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
          <div>
            <h2 className="text-8xl md:text-9xl font-bold text-white mb-8 leading-none">
              PRIC
              <br />
              INGS
            </h2>
          </div>

          <div>
            <h3 className="text-3xl md:text-4xl font-bold text-white mb-6">Select from a variety of packages to buy</h3>

            <p className="text-xl text-gray-400 mb-8">
              Choose the perfect plan that fits your surveillance needs and budget.
            </p>

            <Link href="/pricing">
              <Button
                size="lg"
                className="px-12 py-4 text-lg bg-white text-black hover:bg-gray-200 transition-all duration-300 transform hover:scale-105"
              >
                See Plans
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
