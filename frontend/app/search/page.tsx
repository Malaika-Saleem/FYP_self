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
    setSearchType('text')

    try {
      // Call the Next.js API route (which proxies to Flask)
      const response = await fetch('/api/search/captions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          top_k: 10,
          min_score: 0.0
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Search failed' }))
        console.error('Search error:', errorData)
        setSearchResults([])
        setIsSearching(false)
        return
      }

      const data = await response.json()
      
      // Format results for the SearchResults component
      const formattedResults = data.results.map((result: any, index: number) => {
        // Build thumbnail URL from video_reference if thumbnail is not provided
        let thumbnail = result.thumbnail
        if (!thumbnail && result.video_reference?.object_name && result.video_reference?.bucket) {
          thumbnail = `/api/minio/image/${result.video_reference.bucket}/${result.video_reference.object_name}`
        }
        
        return {
          id: result.id || result.description_id || index + 1,
          timestamp: result.timestamp 
            ? new Date(result.timestamp).toLocaleTimeString() 
            : 'N/A',
          description: result.description || result.caption || '',
          zone: result.zone || 'N/A',
          thumbnail: thumbnail || null,  // Don't use placeholder, handle null in component
          confidence: result.confidence || result.similarity_score || 0.0,
          similarity_score: result.similarity_score,
          event_id: result.event_id,
          video_reference: result.video_reference
        }
      })

      setSearchResults(formattedResults)
    } catch (error) {
      console.error('Error performing search:', error)
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
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
