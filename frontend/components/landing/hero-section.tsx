import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Shield, Camera, Eye } from "lucide-react"

export function HeroSection() {
  return (
    <section className="relative py-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-card opacity-50"></div>
      <div className="absolute top-20 left-10 opacity-20">
        <Camera className="h-16 w-16 text-primary" />
      </div>
      <div className="absolute bottom-20 right-10 opacity-20">
        <Shield className="h-20 w-20 text-primary" />
      </div>
      <div className="absolute top-1/2 left-1/4 opacity-10">
        <Eye className="h-12 w-12 text-primary" />
      </div>

      {/* Curved Lines */}
      <svg
        className="absolute inset-0 w-full h-full opacity-10"
        viewBox="0 0 1200 800"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <path d="M0 400C300 200 600 600 1200 400" stroke="currentColor" strokeWidth="2" className="text-primary" />
        <path
          d="M0 300C400 100 800 500 1200 300"
          stroke="currentColor"
          strokeWidth="1"
          className="text-primary opacity-50"
        />
      </svg>

      <div className="relative max-w-7xl mx-auto text-center">
        <h1 className="text-4xl md:text-6xl font-bold mb-6 text-balance">
          <span className="text-foreground">Smarter Surveillance.</span>
          <br />
          <span className="text-primary">Instant Awareness.</span>
        </h1>

        <p className="text-xl md:text-2xl text-muted-foreground mb-8 max-w-3xl mx-auto text-pretty">
          AI-powered real-time alerts and clip retrieval for your CCTV system
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Link href="/signup">
            <Button size="lg" className="px-8 py-3 text-lg">
              Get Started
            </Button>
          </Link>
          <Link href="/about">
            <Button variant="outline" size="lg" className="px-8 py-3 text-lg bg-transparent">
              Learn More
            </Button>
          </Link>
        </div>

        {/* Stats */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
          <div className="text-center">
            <div className="text-3xl font-bold text-primary mb-2">99.9%</div>
            <div className="text-muted-foreground">Threat Detection Accuracy</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-primary mb-2">24/7</div>
            <div className="text-muted-foreground">Real-time Monitoring</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-primary mb-2">&lt; 1s</div>
            <div className="text-muted-foreground">Alert Response Time</div>
          </div>
        </div>
      </div>
    </section>
  )
}
