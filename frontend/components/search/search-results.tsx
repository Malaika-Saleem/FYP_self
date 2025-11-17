"use client"

import { useState } from "react"
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
  const [selectedClip, setSelectedClip] = useState<SearchResult | null>(null)
  const [isLoadingClip, setIsLoadingClip] = useState(false)
  const [videoErrors, setVideoErrors] = useState<Record<string, boolean>>({})
  
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return "bg-green-500"
    if (confidence >= 0.8) return "bg-yellow-500"
    return "bg-orange-500"
  }
  
  const handleViewClip = (result: SearchResult) => {
    if (result.event_id && result.clip_available) {
      setSelectedClip(result)
    } else {
      alert("Clip not available for this result. The event may not have been processed yet.")
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
              <div className="aspect-video relative rounded-lg overflow-hidden bg-muted">
                {result.annotated_clip_available && result.annotated_clip_url && !videoErrors[result.id] ? (
                  <>
                    <video
                      src={result.annotated_clip_url}
                      className="w-full h-full object-cover"
                      controls
                      muted
                      playsInline
                      preload="metadata"
                      onError={(e) => {
                        console.error('Video load error for annotated clip:', e)
                        const videoEl = e.target as HTMLVideoElement
                        console.error('Video error details:', {
                          error: videoEl.error,
                          src: videoEl.src,
                          networkState: videoEl.networkState,
                          readyState: videoEl.readyState
                        })
                        // Mark this video as having an error, fallback to thumbnail
                        setVideoErrors(prev => ({ ...prev, [result.id]: true }))
                      }}
                      onLoadedMetadata={() => {
                        console.log('✅ Annotated clip metadata loaded for result:', result.id)
                      }}
                      onLoadStart={() => {
                        console.log('🔄 Loading annotated clip:', result.annotated_clip_url)
                      }}
                    >
                      Your browser does not support the video tag.
                    </video>
                    <div className="absolute top-2 right-2 bg-green-500/80 text-white text-xs px-2 py-1 rounded z-10">
                      Annotated
                    </div>
                  </>
                ) : result.thumbnail ? (
                  <>
                    <Image
                      src={result.thumbnail}
                      alt={result.description}
                      fill
                      className="object-cover"
                      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                    />
                    <div className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                      <Play className="h-8 w-8 text-white" />
                    </div>
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
                  disabled={!result.clip_available || !result.event_id}
                >
                  <Eye className="mr-2 h-4 w-4" />
                  View Clip
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
      
      {/* Clip Viewer Dialog */}
      <Dialog open={!!selectedClip} onOpenChange={() => setSelectedClip(null)}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>Event Clip - {selectedClip?.description}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedClip(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </DialogTitle>
          </DialogHeader>
          {selectedClip && selectedClip.event_id && (
            <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
              <video
                src={
                  selectedClip.annotated_clip_available && selectedClip.annotated_clip_url
                    ? selectedClip.annotated_clip_url
                    : `/api/event/clip/${selectedClip.event_id}`
                }
                controls
                className="w-full h-full"
                autoPlay
              >
                Your browser does not support the video tag.
              </video>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
