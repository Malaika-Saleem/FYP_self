"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Search, Camera, Loader2, ImageIcon } from "lucide-react"

interface SearchInterfaceProps {
  onSearch: (query: string) => void
  onUploadImage: () => void
  isSearching: boolean
}

export function SearchInterface({ onSearch, onUploadImage, isSearching }: SearchInterfaceProps) {
  const [query, setQuery] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query)
    }
  }

  const exampleQueries = [
    "woman wearing a cap",
    "person in red jacket",
    "suspicious behavior near entrance",
    "vehicle in parking area",
    "person carrying bag",
  ]

  return (
    <Card className="border-border">
      <CardContent className="p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Main Search Bar */}
          <div className="flex space-x-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-5 h-5" />
              <Input
                placeholder="Describe what you're looking for... (e.g., woman wearing a cap)"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="text-lg h-12 pl-10 pr-10"
                disabled={isSearching}
              />
              <button
                type="button"
                onClick={onUploadImage}
                disabled={isSearching}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Search by image"
              >
                <ImageIcon className="w-5 h-5" />
              </button>
            </div>
            <Button type="submit" size="lg" disabled={!query.trim() || isSearching}>
              {isSearching ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="mr-2 h-5 w-5" />
                  Search
                </>
              )}
            </Button>
          </div>

          {/* Example Queries */}
          <div>
            <p className="text-sm text-muted-foreground mb-3">Try these example searches:</p>
            <div className="flex flex-wrap gap-2">
              {exampleQueries.map((example, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  onClick={() => setQuery(example)}
                  disabled={isSearching}
                  className="bg-transparent"
                >
                  {example}
                </Button>
              ))}
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
