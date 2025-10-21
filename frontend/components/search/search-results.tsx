"use client"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Clock, MapPin, Eye, Download, Play } from "lucide-react"
import Image from "next/image"

interface SearchResult {
  id: number
  timestamp: string
  description: string
  zone: string
  thumbnail: string
  confidence: number
}

interface SearchResultsProps {
  results: SearchResult[]
  query: string
}

export function SearchResults({ results, query }: SearchResultsProps) {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return "bg-green-500"
    if (confidence >= 0.8) return "bg-yellow-500"
    return "bg-orange-500"
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
                <Image
                  src={result.thumbnail || "/placeholder.svg"}
                  alt={result.description}
                  fill
                  className="object-cover"
                  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
                />
                <div className="absolute inset-0 bg-black/20 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                  <Play className="h-8 w-8 text-white" />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Timestamp and Zone */}
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-1 text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>{result.timestamp}</span>
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
                <Button size="sm" className="flex-1">
                  <Eye className="mr-2 h-4 w-4" />
                  View Clip
                </Button>
                <Button variant="outline" size="sm" className="bg-transparent">
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
    </div>
  )
}
