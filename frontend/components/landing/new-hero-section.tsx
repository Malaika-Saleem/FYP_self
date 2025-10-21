"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { useEffect, useRef } from "react"

export function NewHeroSection() {
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
      className="relative min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8 overflow-hidden opacity-0 translate-y-10 transition-all duration-1000"
    >
      {/* Curved Background Graphics */}
      <svg
        className="absolute inset-0 w-full h-full opacity-20"
        viewBox="0 0 1200 800"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M-200 400C200 200 600 600 1400 400" stroke="url(#gradient1)" strokeWidth="2" />
        <path d="M-200 300C300 100 700 500 1400 300" stroke="url(#gradient2)" strokeWidth="1" />
        <path d="M-200 500C400 300 800 700 1400 500" stroke="url(#gradient3)" strokeWidth="1" />
        <defs>
          <linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.3" />
            <stop offset="50%" stopColor="#A855F7" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.3" />
          </linearGradient>
          <linearGradient id="gradient2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#A855F7" stopOpacity="0.4" />
          </linearGradient>
          <linearGradient id="gradient3" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#A855F7" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.3" />
          </linearGradient>
        </defs>
      </svg>

      {/* Security Camera Images */}
      <div className="absolute top-20 left-20 opacity-80 animate-float">
        <div className="w-24 h-24 bg-gray-800 rounded-full flex items-center justify-center border border-gray-700">
          <div className="w-16 h-16 bg-gray-900 rounded-full flex items-center justify-center">
            <div className="w-8 h-8 bg-purple-500 rounded-full"></div>
          </div>
        </div>
      </div>

      <div className="absolute bottom-32 right-20 opacity-80 animate-float-delayed">
        <div className="w-28 h-28 bg-gray-800 rounded-full flex items-center justify-center border border-gray-700">
          <div className="w-20 h-20 bg-gray-900 rounded-full flex items-center justify-center">
            <div className="w-10 h-10 bg-purple-500 rounded-full"></div>
          </div>
        </div>
      </div>

      <div className="relative max-w-6xl mx-auto text-center z-10">
        <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold mb-8 text-balance leading-tight">
          <span className="text-white">Smarter Surveillance.</span>
          <br />
          <span className="text-white">Instant Awareness.</span>
        </h1>

        <p className="text-xl md:text-2xl text-gray-400 mb-12 max-w-3xl mx-auto text-pretty">
          AI-powered real-time alerts and clip retrieval for your CCTV system.
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
