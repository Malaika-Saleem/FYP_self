"use client"

import Link from "next/link"
import Image from "next/image"
import { useSession, signOut } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { Search, DollarSign, Info, LogOut, Users } from "lucide-react"

export function Navigation() {
  const { data: session, status } = useSession()
  const user = session?.user

  return (
    <nav className="relative top-0 left-0 right-0 z-50 bg-transparent">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center space-x-2">
            <Image src="/logo.png" alt="DetectifAI" width={32} height={32} className="h-8 w-8" />
            <span className="text-xl font-bold text-white">DetectifAI</span>
          </Link>

          {/* Navigation Links */}
          <div className="hidden md:flex items-center space-x-8">
            {user ? (
              <>
                <Link href="/dashboard" className="text-white hover:text-purple-400 transition-colors">
                  Dashboard
                </Link>
                {(user as any).role === "admin" ? (
                  <>
                    <Link
                      href="/admin/users"
                      className="text-white hover:text-purple-400 transition-colors flex items-center space-x-1"
                    >
                      <Users className="h-4 w-4" />
                      <span>Users</span>
                    </Link>
                    <Link
                      href="/admin/pricing"
                      className="text-white hover:text-purple-400 transition-colors flex items-center space-x-1"
                    >
                      <DollarSign className="h-4 w-4" />
                      <span>Pricing Management</span>
                    </Link>
                  </>
                ) : (
                  <>
                    <Link
                      href="/search"
                      className="text-white hover:text-purple-400 transition-colors flex items-center space-x-1"
                    >
                      <Search className="h-4 w-4" />
                      <span>Search</span>
                    </Link>
                    <Link
                      href="/pricing"
                      className="text-white hover:text-purple-400 transition-colors flex items-center space-x-1"
                    >
                      <DollarSign className="h-4 w-4" />
                      <span>Pricing</span>
                    </Link>
                    <Link
                      href="/about"
                      className="text-white hover:text-purple-400 transition-colors flex items-center space-x-1"
                    >
                      <Info className="h-4 w-4" />
                      <span>About</span>
                    </Link>
                  </>
                )}
              </>
            ) : (
              <>
                <Link href="/" className="text-white hover:text-purple-400 transition-colors">
                  Home
                </Link>
                <Link href="/search" className="text-gray-500 cursor-not-allowed">
                  Search
                </Link>
                <Link href="/pricing" className="text-white hover:text-purple-400 transition-colors">
                  Pricing
                </Link>
                <Link href="/about" className="text-white hover:text-purple-400 transition-colors">
                  About
                </Link>
              </>
            )}
          </div>

          {/* Auth Buttons */}
          <div className="flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-300">Welcome, {user.name}</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => signOut()}
                  className="flex items-center space-x-1 bg-transparent border-white text-white hover:bg-white hover:text-black"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Logout</span>
                </Button>
              </div>
            ) : (
              <>
                <Link href="/signin">
                  <Button
                    variant="outline"
                    size="sm"
                    className="bg-transparent border-white text-white hover:bg-white hover:text-black"
                  >
                    Sign In
                  </Button>
                </Link>
                <Link href="/signup">
                  <Button size="sm" className="bg-white text-black hover:bg-gray-200">
                    Sign Up
                  </Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
