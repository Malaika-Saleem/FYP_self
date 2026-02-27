"use client"

import { SessionProvider, signIn, signOut, useSession } from "next-auth/react"
import { setAuthToken, removeAuthToken } from "@/lib/api"

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>
}

// convenient hooks
export const useAuth = () => {
  const { data: session, status } = useSession()

  const user = session?.user ? {
    id: (session.user as any).id,
    email: session.user.email || "",
    name: session.user.name || "",
    role: (session.user as any).role || "user",
  } : null

  const isLoading = status === "loading"

  return {
    user,
    isLoading,
    login: async (email: string, password: string) => {
      const res = await signIn("credentials", {
        redirect: false,
        email,
        password,
      })
      
      if (!res?.error) {
        // After successful NextAuth login, get JWT token from backend for API calls
        try {
          const FLASK_API_URL = process.env.NEXT_PUBLIC_FLASK_API_URL || 'http://localhost:5000'
          const tokenRes = await fetch(`${FLASK_API_URL}/api/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
          })
          
          if (tokenRes.ok) {
            const data = await tokenRes.json()
            if (data.token) {
              setAuthToken(data.token)
            }
          }
        } catch (error) {
          console.error('Failed to get JWT token from backend:', error)
          // Continue anyway - NextAuth session is still valid
        }
      }
      
      return !res?.error
    },

    signup: async (email: string, password: string, name: string, organization?: string) => {
      try {
        const response = await fetch('/api/auth/signup', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, password, name, organization }),
        })
        return response.ok
      } catch (error) {
        console.error('Signup error:', error)
        return false
      }
    },

    googleLogin: async () => {
      await signIn("google", { callbackUrl: "/dashboard" })
    },

    logout: async () => {
      removeAuthToken()
      await signOut()
    },
  }
}
