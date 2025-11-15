"use client"

import { useAuth } from "@/components/auth-provider"
import { SearchInterface } from "@/components/search/search-interface"
import { SearchResults } from "@/components/search/search-results"
import { UploadImageModal } from "@/components/search/upload-image-modal"
import { Button } from "@/components/ui/button"
import { ArrowLeft, LogOut } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import Link from "next/link"
import Image from "next/image"

export default function SearchPage() {
  const { user, isLoading, logout } = useAuth()
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [searchType, setSearchType] = useState<'text' | 'image'>('text')

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/signin")
    }
  }, [user, isLoading, router])

  const handleSearch = async (query: string) => {
    if (!query.trim()) return

    setIsSearching(true)
    setSearchQuery(query)

    // Simulate API call with mock results
    await new Promise((resolve) => setTimeout(resolve, 1500))

    // Mock search results based on the design document
    const mockResults = [
      {
        id: 1,
        timestamp: "10:42 PM",
        description: "Man in red shirt jumping a wall",
        zone: "Zone 2",
        thumbnail: "/man-in-red-shirt-jumping-wall-surveillance-footage.jpg",
        confidence: 0.92,
      },
      {
        id: 2,
        timestamp: "1:13 AM",
        description: "Woman fighting with another person",
        zone: "Zone 1",
        thumbnail: "/woman-fighting-surveillance-footage.jpg",
        confidence: 0.87,
      },
      {
        id: 3,
        timestamp: "3:25 PM",
        description: "Person loitering near entrance",
        zone: "Zone 3",
        thumbnail: "/person-loitering-entrance-surveillance-footage.jpg",
        confidence: 0.78,
      },
      {
        id: 4,
        timestamp: "7:18 AM",
        description: "Suspicious package left unattended",
        zone: "Zone 2",
        thumbnail: "/suspicious-package-surveillance-footage.jpg",
        confidence: 0.85,
      },
    ]

    setSearchResults(mockResults)
    setIsSearching(false)
  }

  const handleImageSearchResults = (results: any[]) => {
    setSearchResults(results)
    setSearchType('image')
    setSearchQuery(`Image search - ${results.length} matches found`)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading search...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header
      <header className="border-b border-border bg-card">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-4">
            <Link href="/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
            <div className="flex items-center gap-3">
              <Image src="/logo.png" alt="DetectifAI" width={32} height={32} />
              <span className="text-xl font-bold text-white">DetectifAI</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">Welcome, {user?.name}</span>
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="h-4 w-4 mr-2" />
              Logout
            </Button>
          </div>
        </div>
      </header> */}

      <main className="p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-4 text-white">Search Incidents by Description</h1>
            <p className="text-muted-foreground max-w-2xl mx-auto text-pretty">
              Search through your surveillance footage using natural language descriptions or upload an image to find
              similar scenes.
            </p>
          </div>

          <SearchInterface
            onSearch={handleSearch}
            onUploadImage={() => setShowUploadModal(true)}
            isSearching={isSearching}
          />

          {searchResults.length > 0 && <SearchResults results={searchResults} query={searchQuery} />}

          <UploadImageModal 
            isOpen={showUploadModal} 
            onClose={() => setShowUploadModal(false)}
            onSearchResults={handleImageSearchResults}
          />
        </div>
      </main>
    </div>
  )
}
