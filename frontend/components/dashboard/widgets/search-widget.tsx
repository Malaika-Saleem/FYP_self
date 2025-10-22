"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, Camera } from "lucide-react"

export function SearchWidget() {
  const [searchQuery, setSearchQuery] = useState("")

  const handleSearch = () => {
    if (searchQuery.trim()) {
      // In a real app, this would trigger the search functionality
      console.log("Searching for:", searchQuery)
    }
  }

  return (
    <Card className="border-gray-800">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <Search className="h-5 w-5 text-primary" />
          <span>Search By Prompt</span>
        </CardTitle>
        <CardDescription>Use natural language to find specific moments in your surveillance footage</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex space-x-2">
          <Input
            placeholder="e.g., woman wearing a cap"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSearch()}
          />
          <Button size="icon" variant="outline">
            <Camera className="h-4 w-4" />
          </Button>
        </div>
        <Button onClick={handleSearch} className="w-full" disabled={!searchQuery.trim()}>
          <Search className="mr-2 h-4 w-4" />
          Search
        </Button>
      </CardContent>
    </Card>
  )
}
