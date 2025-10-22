"use client"

import type React from "react"
import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useAuth } from "@/components/auth-provider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Eye, EyeOff, Loader2 } from "lucide-react"
import { signIn } from "next-auth/react"
import Image from "next/image"

export default function SignInPage() {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const { login, googleLogin } = useAuth()
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setError("");
  setIsLoading(true);

  try {
    const success = await login(email, password);
    if (success) {
      router.push("/dashboard");
    } else {
      setError("Invalid email or password");
    }
  } catch (err) {
    setError("Something went wrong");
  } finally {
    setIsLoading(false);
  }
};


  return (
    <div className="min-h-screen bg-background flex">
      {/* Left Side - Welcome Message */}
      <div className="flex-1 flex items-center justify-center p-12">
        <div className="max-w-md">
          <div className="flex items-center space-x-2 mb-8">
            <Image src="/logo.png" alt="DetectifAI" width={32} height={32} />
            <span className="text-white text-xl font-medium">DetectifAI</span>
          </div>

          <h1 className="text-white text-6xl font-bold mb-8">Welcome!</h1>
          <div className="w-16 h-1 bg-white mb-8"></div>

          <p className="text-gray-400 text-sm mb-8 leading-relaxed">
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Aenean commodo ligula eget dolor.
          </p>

          <Button className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-2 rounded-full">
            Learn More
          </Button>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-12">
        <div className="w-full max-w-md">
          <h2 className="text-white text-3xl font-medium mb-8">Log in</h2>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-white text-sm mb-2 block">Phone number, user name, or email address</label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-transparent border-2 border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-white focus:ring-0"
                required
              />
            </div>

            <div>
              <label className="text-white text-sm mb-2 block">Your password</label>
              <div className="relative">
                <Input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-transparent border-2 border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-white focus:ring-0 pr-12"
                  required
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white hover:bg-transparent"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  <span className="ml-2 text-sm">Hide</span>
                </Button>
              </div>
            </div>

            {error && <div className="text-red-500 text-sm">{error}</div>}

            <Button
              type="submit"
              className="w-full bg-white text-black hover:bg-gray-100 py-3 rounded-lg font-medium"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing In...
                </>
              ) : (
                "Log in"
              )}
            </Button>

            <div className="text-center">
              <div className="text-gray-500 text-sm mb-4">OR</div>
              <div className="text-primary text-sm mb-6">or continue with</div>

              <Button
                type="button"
                variant="ghost"
                className="w-12 h-12 rounded-full bg-transparent hover:bg-gray-800 p-0"
                onClick={() => googleLogin()}
              >
                <svg className="w-6 h-6" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
              </Button>
            </div>

            <div className="text-center text-sm text-gray-400 mt-8">
              {"Don't have an account? "}
              <Link href="/signup" className="text-primary hover:underline">
                Sign up
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
