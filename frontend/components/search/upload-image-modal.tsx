"use client"

import type React from "react"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Upload, X, ImageIcon } from "lucide-react"

interface UploadImageModalProps {
  isOpen: boolean
  onClose: () => void
}

export function UploadImageModal({ isOpen, onClose }: UploadImageModalProps) {
  const [dragActive, setDragActive] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

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
      }
    }
  }

  const handleScan = () => {
    if (uploadedFile) {
      // In a real app, this would process the image and search for similar scenes
      console.log("Scanning image:", uploadedFile.name)
      onClose()
    }
  }

  const handleClose = () => {
    setUploadedFile(null)
    onClose()
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Image Search</DialogTitle>
          <DialogDescription>Upload image of a person that might be involved in suspicious behaviour</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
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
                <input type="file" accept="image/*" onChange={handleFileInput} className="hidden" id="file-upload" />
                <label htmlFor="file-upload">
                  <Button variant="outline" className="cursor-pointer bg-transparent">
                    CHOOSE SCAN
                  </Button>
                </label>
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
                  <Button variant="ghost" size="sm" onClick={() => setUploadedFile(null)}>
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                <div className="aspect-video bg-muted rounded-lg flex items-center justify-center mb-4">
                  <ImageIcon className="h-12 w-12 text-muted-foreground" />
                </div>

                <Button onClick={handleScan} className="w-full">
                  <Upload className="mr-2 h-4 w-4" />
                  Start Image Search
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
