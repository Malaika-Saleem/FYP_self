"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/components/auth-provider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Eye, EyeOff } from "lucide-react"
import Image from "next/image"

export default function AdminSignIn() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState("")
  const { login, isLoading } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    const success = await login(email, password)
    if (success) {
      router.push("/admin/dashboard")
    } else {
      setError("Invalid admin credentials")
    }
  }

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left side - Welcome section */}
      <div className="flex-1 flex flex-col justify-center px-12 lg:px-24">
        <div className="flex items-center gap-3 mb-16">
          <Image src="/logo.png" alt="DetectifAI" width={40} height={40} />
          <span className="text-2xl font-bold text-white">DetectifAI</span>
        </div>

        <div className="max-w-md">
          <h1 className="text-6xl font-bold text-white mb-8">Admin Portal</h1>
          <div className="w-24 h-1 bg-primary mb-8"></div>
          <p className="text-muted-foreground text-lg leading-relaxed mb-8">
            Access the administrative dashboard to manage users, pricing, and system settings.
          </p>
          <Button variant="outline" className="bg-primary text-primary-foreground hover:bg-primary/90 border-primary">
            Learn More
          </Button>
        </div>
      </div>

      {/* Right side - Login form */}
      <div className="flex-1 flex items-center justify-center px-8">
        <div className="w-full max-w-md">
          <h2 className="text-3xl font-bold text-white mb-8">Admin Log in</h2>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm text-muted-foreground mb-2">Admin email address</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full h-12 bg-input border-border text-white rounded-lg"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-muted-foreground mb-2">Your password</label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full h-12 bg-input border-border text-white rounded-lg pr-12"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-white"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  <span className="ml-2 text-sm">Hide</span>
                </button>
              </div>
            </div>

            {error && <p className="text-destructive text-sm">{error}</p>}

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full h-12 bg-white text-black hover:bg-gray-100 rounded-lg font-medium"
            >
              {isLoading ? "Signing in..." : "Log in"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  )
}
