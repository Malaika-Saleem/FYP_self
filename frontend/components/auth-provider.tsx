"use client"

import { SessionProvider, signIn, signOut, useSession } from "next-auth/react"

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
      await signOut()
    },
  }
}
