"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Clock, MapPin, Eye, Download, Play, X, ImageIcon } from "lucide-react"
import Image from "next/image"

interface SearchResult {
  id: number | string
  face_id?: string
  event_id?: string
  video_id?: string
  timestamp: string | number
  description: string
  zone: string
  thumbnail: string | null
  confidence: number
  clip_available?: boolean
  annotated_clip_available?: boolean
  annotated_clip_url?: string | null
  start_timestamp?: number
  end_timestamp?: number
}

interface SearchResultsProps {
  results: SearchResult[]
  query: string
}

export function SearchResults({ results, query }: SearchResultsProps) {
  const router = useRouter()
  const [selectedClip, setSelectedClip] = useState<SearchResult | null>(null)
  const [isLoadingClip, setIsLoadingClip] = useState(false)
  const [videoErrors, setVideoErrors] = useState<Record<string, boolean>>({})
  
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return "bg-green-500"
    if (confidence >= 0.8) return "bg-yellow-500"
    return "bg-orange-500"
  }
  
  const handleViewClip = (result: SearchResult) => {
    if (result.event_id || result.video_id) {
      // Open video player modal — works for both event clips and full videos
      setSelectedClip(result)
    } else {
      alert("No video linked to this search result.")
    }
  }
  
  const handleDownloadClip = async (result: SearchResult) => {
    if (!result.event_id || !result.clip_available) {
      alert("Clip not available for download.")
      return
    }
    
    try {
      setIsLoadingClip(true)
      const response = await fetch(`/api/event/clip/${result.event_id}/download`)
      
      if (!response.ok) {
        throw new Error('Failed to download clip')
      }
      
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `event_${result.event_id}_clip.mp4`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Error downloading clip:', error)
      alert('Failed to download clip. Please try again.')
    } finally {
      setIsLoadingClip(false)
    }
  }
  
  const formatTimestamp = (timestamp: string | number) => {
    if (typeof timestamp === 'number') {
      const date = new Date(timestamp * 1000)
      return date.toLocaleTimeString()
    }
    return timestamp
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">
          Search Results for "{query}" ({results.length} found)
        </h2>
        <div className="text-sm text-muted-foreground">Sorted by relevance</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {results.map((result) => (
          <Card key={result.id} className="border-border hover:shadow-lg transition-shadow">
            <CardHeader className="pb-3">
              {/* Use square aspect for face images, 16:9 for video thumbnails */}
              <div className={`relative rounded-lg overflow-hidden bg-muted ${
                result.thumbnail?.includes('/api/face-image/') ? 'aspect-square' : 'aspect-video'
              }`}>
                {/* Always show thumbnail for face search results, not annotated clip preview */}
                {result.thumbnail ? (
                  <>
                    <img
                      src={result.thumbnail}
                      alt={result.description}
                      className={`w-full h-full ${
                        result.thumbnail?.includes('/api/face-image/')
                          ? 'object-contain bg-gradient-to-br from-gray-900 to-gray-800'
                          : 'object-cover'
                      }`}
                      onError={(e) => {
                        // Use data URI placeholder instead of trying to load a file
                        const img = e.target as HTMLImageElement
                        if (!img.src.includes('data:image')) {
                          img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAwIiBoZWlnaHQ9IjQwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPk5vIEltYWdlPC90ZXh0Pjwvc3ZnPg=='
                        }
                      }}
                    />
                    {result.annotated_clip_available && (
                      <div className="absolute top-2 right-2 bg-blue-500/80 text-white text-xs px-2 py-1 rounded z-10">
                        Clip Available
                      </div>
                    )}
                    {result.clip_available && (
                      <div className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity cursor-pointer"
                        onClick={() => handleViewClip(result)}
                      >
                        <Play className="h-8 w-8 text-white drop-shadow-lg" />
                      </div>
                    )}
                  </>
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <ImageIcon className="h-12 w-12 text-muted-foreground" />
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Timestamp and Zone */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-1 text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>{formatTimestamp(result.timestamp)}</span>
                </div>
                <div className="flex items-center space-x-1 text-muted-foreground">
                  <MapPin className="h-4 w-4" />
                  <span>{result.zone}</span>
                </div>
              </div>

              {/* Description */}
              <p className="text-sm font-medium text-pretty">{result.description}</p>

              {/* Confidence Badge */}
              <div className="flex items-center space-x-2">
                <Badge variant="secondary" className="text-xs">
                  <div className={`w-2 h-2 rounded-full ${getConfidenceColor(result.confidence)} mr-1`}></div>
                  {Math.round(result.confidence * 100)}% match
                </Badge>
              </div>

              {/* Action Buttons */}
              <div className="flex space-x-2">
                <Button 
                  size="sm" 
                  className="flex-1"
                  onClick={() => handleViewClip(result)}
                  disabled={!result.event_id && !result.video_id}
                >
                  <Eye className="mr-2 h-4 w-4" />
                  {result.event_id ? 'View Clip' : result.video_id ? 'View Video' : 'No Video'}
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="bg-transparent"
                  onClick={() => handleDownloadClip(result)}
                  disabled={!result.clip_available || !result.event_id || isLoadingClip}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Load More */}
      <div className="text-center">
        <Button variant="outline" className="bg-transparent">
          Load More Results
        </Button>
      </div>
      
      {/* Video Player Dialog */}
      <Dialog open={!!selectedClip} onOpenChange={() => setSelectedClip(null)}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>{selectedClip?.description || 'Video'}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedClip(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>
          {selectedClip && (selectedClip.event_id || selectedClip.video_id) ? (
            <div className="space-y-3">
              <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
                <video
                  key={selectedClip.event_id || selectedClip.video_id}
                  src={
                    selectedClip.event_id
                      ? `/api/event/clip/${selectedClip.event_id}`
                      : `/api/video/compressed/${selectedClip.video_id}`
                  }
                  controls
                  className="w-full h-full"
                  autoPlay
                  onError={(e) => {
                    const videoEl = e.target as HTMLVideoElement
                    setVideoErrors(prev => ({
                      ...prev,
                      [selectedClip.event_id || selectedClip.video_id || '']: true
                    }))
                  }}
                >
                  Your browser does not support the video tag.
                </video>
              </div>
              {videoErrors[selectedClip.event_id || selectedClip.video_id || ''] && (
                <p className="text-sm text-destructive text-center">
                  Video could not be loaded. The source file may no longer be available.
                </p>
              )}
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>Match: {Math.round(selectedClip.confidence * 100)}%</span>
                {selectedClip.video_id && (
                  <Button
                    variant="link"
                    size="sm"
                    className="p-0 h-auto"
                    onClick={() => {
                      setSelectedClip(null)
                      router.push(`/results/${selectedClip.video_id}`)
                    }}
                  >
                    View Full Analysis →
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-muted-foreground">
              <p>No video available for this result.</p>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
