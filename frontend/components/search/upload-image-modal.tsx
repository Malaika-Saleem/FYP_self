"use client"

import type React from "react"

import { useState, useRef } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Upload, X, ImageIcon, Search, Loader2 } from "lucide-react"
import { toast } from "sonner"

interface UploadImageModalProps {
  isOpen: boolean
  onClose: () => void
  onSearchResults: (results: any[]) => void
}

export function UploadImageModal({ isOpen, onClose, onSearchResults }: UploadImageModalProps) {
  const [dragActive, setDragActive] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [uploadedFileUrl, setUploadedFileUrl] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [similarityThreshold, setSimilarityThreshold] = useState([0.6])
  const [maxResults, setMaxResults] = useState(10)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      if (file.type.startsWith("image/")) {
        setUploadedFile(file)
      }
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      if (file.type.startsWith("image/")) {
        setUploadedFile(file)
        // Create URL for preview
        const url = URL.createObjectURL(file)
        setUploadedFileUrl(url)
      }
    }
  }

  const handleChooseFile = () => {
    fileInputRef.current?.click()
  }

  const handleScan = async () => {
    if (!uploadedFile) {
      toast.error("Please select an image first")
      return
    }

    setIsSearching(true)
    
    try {
      // Create FormData for file upload
      const formData = new FormData()
      formData.append('image', uploadedFile)
      formData.append('threshold', similarityThreshold[0].toString())
      formData.append('max_results', maxResults.toString())

      // Call the image search API
      const response = await fetch('/api/search/person-by-image', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (data.success) {
        toast.success(`Found ${data.total_matches} matches!`)
        onSearchResults(data.results)
        onClose()
      } else {
        toast.error(data.error || 'Search failed')
      }
    } catch (error) {
      console.error('Image search error:', error)
      toast.error('Failed to search for person. Please try again.')
    } finally {
      setIsSearching(false)
    }
  }

  const handleClose = () => {
    setUploadedFile(null)
    setUploadedFileUrl(null)
    setIsSearching(false)
    setSimilarityThreshold([0.6])
    setMaxResults(10)
    onClose()
  }

  const removeFile = () => {
    setUploadedFile(null)
    if (uploadedFileUrl) {
      URL.revokeObjectURL(uploadedFileUrl)
      setUploadedFileUrl(null)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Person Image Search</DialogTitle>
          <DialogDescription>Upload an image to search for this person across all surveillance footage</DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {!uploadedFile ? (
            <Card
              className={`border-2 border-dashed transition-colors ${
                dragActive ? "border-primary bg-primary/5" : "border-border"
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <CardContent className="flex flex-col items-center justify-center p-8 text-center">
                <div className="mb-4 p-4 bg-primary/10 rounded-full">
                  <Upload className="h-8 w-8 text-primary" />
                </div>
                <h3 className="font-medium mb-2">Drop your image here</h3>
                <p className="text-sm text-muted-foreground mb-4">or click to browse files</p>
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={handleFileInput} 
                  className="hidden" 
                  id="file-upload"
                  ref={fileInputRef}
                />
                <Button 
                  variant="outline" 
                  className="cursor-pointer bg-transparent"
                  onClick={handleChooseFile}
                  type="button"
                >
                  CHOOSE SCAN
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-border">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center space-x-3">
                    <ImageIcon className="h-8 w-8 text-primary" />
                    <div>
                      <p className="font-medium">{uploadedFile.name}</p>
                      <p className="text-sm text-muted-foreground">{(uploadedFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="sm" onClick={removeFile}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                <div className="aspect-video bg-muted rounded-lg flex items-center justify-center mb-4 overflow-hidden">
                  {uploadedFileUrl ? (
                    <img 
                      src={uploadedFileUrl} 
                      alt="Uploaded image preview" 
                      className="w-full h-full object-cover rounded-lg"
                    />
                  ) : (
                    <ImageIcon className="h-12 w-12 text-muted-foreground" />
                  )}
                </div>

                {/* Search Configuration */}
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="similarity">Similarity Threshold: {similarityThreshold[0].toFixed(2)}</Label>
                    <Slider
                      id="similarity"
                      min={0.3}
                      max={0.9}
                      step={0.05}
                      value={similarityThreshold}
                      onValueChange={setSimilarityThreshold}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Higher values = more strict matching (fewer results)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="maxResults">Maximum Results</Label>
                    <Input
                      id="maxResults"
                      type="number"
                      min={1}
                      max={50}
                      value={maxResults}
                      onChange={(e) => setMaxResults(parseInt(e.target.value) || 10)}
                      className="w-full"
                    />
                  </div>
                </div>

                <Button 
                  onClick={handleScan} 
                  className="w-full" 
                  disabled={isSearching}
                >
                  {isSearching ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      Start Person Search
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
