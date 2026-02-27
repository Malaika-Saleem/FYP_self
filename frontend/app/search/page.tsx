"use client"

import { useAuth } from "@/components/auth-provider"
import { SearchInterface } from "@/components/search/search-interface"
import { SearchResults } from "@/components/search/search-results"
import { UploadImageModal } from "@/components/search/upload-image-modal"
import { Button } from "@/components/ui/button"
import { ArrowLeft, LogOut, Lock, Crown, Shield, Sparkles, TrendingUp, Zap, X } from "lucide-react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import Link from "next/link"
import Image from "next/image"
import { SubscriptionProvider, useSubscription } from "@/contexts/subscription-context"

// ─── Wrapper that injects SubscriptionProvider ───────────────────────────────
export default function SearchPage() {
  return (
    <SubscriptionProvider>
      <SearchPageInner />
    </SubscriptionProvider>
  )
}

// ─── Full-page Pro-only lock screen ──────────────────────────────────────────
function SearchLockedScreen() {
  const router = useRouter()

  const proFeatures = [
    { icon: Sparkles, text: "NLP Search — find moments with natural language" },
    { icon: Crown, text: "Image Search — find people by photo" },
    { icon: Shield, text: "Behavior Analysis (Fighting, Accident, Wall Climbing)" },
    { icon: TrendingUp, text: "Person Tracking & Re-appearance Detection" },
    { icon: Zap, text: "Unlimited video uploads" },
    { icon: Crown, text: "Custom Advanced Reports" },
  ]

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="max-w-lg w-full text-center space-y-6">
        {/* Lock icon */}
        <div className="flex justify-center">
          <div className="p-5 bg-gradient-to-br from-purple-600/20 to-blue-600/20 border border-purple-500/30 rounded-full">
            <Lock className="w-10 h-10 text-purple-400" />
          </div>
        </div>

        <div>
          <h1 className="text-2xl font-bold mb-2 text-white">Search is a Pro Feature</h1>
          <p className="text-muted-foreground max-w-md mx-auto">
            NLP Search and Image Search require the <span className="text-purple-400 font-semibold">DetectifAI Pro</span> plan.
            Upgrade to search through your surveillance footage using natural language or photos.
          </p>
        </div>

        {/* Pro features */}
        <div className="bg-card border border-border rounded-xl p-5 text-left space-y-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Everything in Pro:</p>
          {proFeatures.map(({ icon: Icon, text }, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <Icon className="w-4 h-4 text-purple-500 flex-shrink-0" />
              <span>{text}</span>
            </div>
          ))}
        </div>

        {/* CTAs */}
        <div className="flex gap-3 justify-center">
          <Button variant="outline" onClick={() => router.push("/dashboard")}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Dashboard
          </Button>
          <Button
            className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white border-0"
            onClick={() => router.push("/pricing")}
          >
            <Crown className="w-4 h-4 mr-2" />
            Upgrade to Pro
          </Button>
        </div>

        <p className="text-xs text-muted-foreground">Starting at $49/mo · Cancel anytime</p>
      </div>
    </div>
  )
}

function SearchPageInner() {
  const { user, isLoading, logout } = useAuth()
  const { isGateUnlocked, loading: subLoading } = useSubscription()
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
      
      // Check if results exist and format them
      if (!data.results || data.results.length === 0) {
        setSearchResults([])
        setIsSearching(false)
        return
      }
      
      // Format results for the SearchResults component
      const formattedResults = data.results.map((result: any, index: number) => {
        // Build thumbnail URL from video_reference if thumbnail is not provided
        let thumbnail = result.thumbnail
        if (!thumbnail && result.video_reference?.object_name && result.video_reference?.bucket) {
          thumbnail = `/api/minio/image/${result.video_reference.bucket}/${result.video_reference.object_name}`
        }
        
        return {
          id: result.id || result.description_id || index + 1,
          timestamp: result.start_timestamp_ms 
            ? new Date(result.start_timestamp_ms).toLocaleTimeString() 
            : result.timestamp 
              ? (typeof result.timestamp === 'number' ? new Date(result.timestamp).toLocaleTimeString() : result.timestamp)
              : 'N/A',
          description: result.description || result.caption || '',
          zone: result.zone || 'N/A',
          thumbnail: thumbnail || null,  // Don't use placeholder, handle null in component
          confidence: result.confidence || result.similarity_score || 0.0,
          similarity_score: result.similarity_score || result.similarity || 0.0,
          event_id: result.event_id,
          video_id: result.video_id,
          start_timestamp_ms: result.start_timestamp_ms,
          end_timestamp_ms: result.end_timestamp_ms,
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

  if (isLoading || subLoading) {
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

  // ── Subscription gate: NLP Search requires Pro ──────────────────────────
  if (!isGateUnlocked("nlp_search")) {
    return <SearchLockedScreen />
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

          {/* Show results or no results message */}
          {searchQuery && !isSearching && (
            <>
              {searchResults.length > 0 ? (
                <SearchResults results={searchResults} query={searchQuery} />
              ) : (
                <div className="text-center py-12">
                  <div className="text-muted-foreground text-lg mb-2">No results found</div>
                  <div className="text-sm text-muted-foreground">
                    No matches found for "{searchQuery}". Try adjusting your search terms or using different keywords.
                  </div>
                </div>
              )}
            </>
          )}

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
