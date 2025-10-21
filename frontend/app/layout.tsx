import type React from "react"
import type { Metadata } from "next"
import { GeistSans } from "geist/font/sans"
import { GeistMono } from "geist/font/mono"
import { Analytics } from "@vercel/analytics/next"
import { AuthSessionProvider } from "@/components/AuthSessionProvider"
import { Suspense } from "react"
import { Navigation } from "@/components/navigation"
import "./globals.css"

export const metadata: Metadata = {
  title: "DetectifAI - Smarter Surveillance. Instant Awareness.",
  description: "AI-powered real-time alerts and clip retrieval for your CCTV system",
  generator: "v0.app",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`font-sans ${GeistSans.variable} ${GeistMono.variable}`}>
        <Suspense fallback={<div>Loading...</div>}>
          <AuthSessionProvider>
            <Navigation />
            {children}
          </AuthSessionProvider>
        </Suspense>
        <Analytics />
      </body>
    </html>
  )
}
