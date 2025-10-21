"use client"

import { ReactNode } from "react"
import { SessionProvider } from "next-auth/react"
import { AuthProvider } from "./auth-provider"

export function AuthSessionProvider({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <AuthProvider>{children}</AuthProvider>
    </SessionProvider>
  )
}
