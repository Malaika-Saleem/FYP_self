"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Search, Upload, Play, Pause, SkipBack, SkipForward, Volume2, FileText, AlertTriangle, Loader2 } from "lucide-react"
import { Input } from "@/components/ui/input"
import { useRouter } from "next/navigation"
import { useState, useRef } from "react"

interface UserDashboardProps {
  userRole: "user" | "admin"
}

export function UserDashboard({ userRole }: UserDashboardProps) {
  const router = useRouter()
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showReportModal, setShowReportModal] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string>("")
  const [currentVideoId, setCurrentVideoId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSearchClick = () => {
    router.push("/search")
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setUploadStatus("")
      // Automatically start upload when file is selected
      handleFileUpload(file)
    }
  }

  const handleUpload = () => {
    // Trigger file selection dialog
    fileInputRef.current?.click()
  }

  const handleFileUpload = async (file: File) => {
    setUploading(true)
    setUploadStatus("Uploading video...")

    try {
      const formData = new FormData()
      formData.append('video', file)
      formData.append('configType', 'detectifai') // Use detectifai config for fire detection

      const response = await fetch('/api/video/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Upload failed')
      }

      const videoId = data.video_id
      setUploadStatus(`✅ Upload successful! Processing video...`)
      setCurrentVideoId(videoId)

      // Poll for processing completion
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`/api/video/status/${videoId}`)
          const statusData = await statusResponse.json()
          
          if (statusData.status === 'completed') {
            clearInterval(pollInterval)
            setUploadStatus("✅ Processing complete! Redirecting...")
            setTimeout(() => {
              router.push(`/results/${videoId}`)
            }, 1000)
          } else if (statusData.status === 'error') {
            clearInterval(pollInterval)
            setUploadStatus(`❌ Processing error: ${statusData.message}`)
          } else {
            setUploadStatus(`🔄 Processing... ${statusData.progress}%`)
          }
        } catch (err) {
          console.error('Polling error:', err)
        }
      }, 2000) // Poll every 2 seconds

    } catch (err) {
      setUploadStatus(`❌ Error: ${err instanceof Error ? err.message : 'Upload failed'}`)
    } finally {
      setUploading(false)
    }
  }

  const handleViewResults = (videoId: string) => {
    router.push(`/results/${videoId}`)
  }

  const handleViewDemoResults = () => {
    // Use the existing processed video ID
    router.push('/results/video_20251012_203718_54bd730c')
  }

  return (
    <div className="space-y-8">
      {/* Main Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Search By Prompt Widget */}
        <Card className="shadow-lg border-3 shadow-gray-500/50 hover:shadow-gray-500/70 transition-shadow duration-300">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center space-x-2 text-xl">
              <Search className="h-5 w-5 text-primary" />
              <span>Search By Prompt</span>
            </CardTitle>
            <CardDescription>Use natural language to find specific moments in your surveillance footage</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-5 h-5" />
              <Input
                placeholder="Describe what you're looking for..."
                className="w-full pl-10 py-3"
              />
            </div>
            <Button
              onClick={handleSearchClick}
              className="w-full"
              size="lg"
            >
              Search →
            </Button>
          </CardContent>
        </Card>

        {/* Video Footage Widget */}
        <Card className="shadow-lg border-3 shadow-gray-500/50 hover:shadow-gray-500/70 transition-shadow duration-300">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center justify-between text-xl">
              <div className="flex items-center space-x-2">
                <Play className="h-5 w-5 text-primary" />
                <span>Video Footage</span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowUploadModal(true)}
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload Videos
              </Button>
            </CardTitle>
            <CardDescription>Monitor live surveillance feeds and uploaded videos</CardDescription>
          </CardHeader>
          <CardContent>
            {/* Video Player */}
            <div className="relative bg-black rounded-lg overflow-hidden border">
              <img src="/surveillance-camera-footage.jpg" alt="Surveillance footage" className="w-full h-48 object-cover" />

              {/* Video Controls Overlay */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4">
                <div className="flex items-center justify-between text-white text-sm mb-2">
                  <span>38:5</span>
                  <span>1:56:30</span>
                </div>

                {/* Progress Bar */}
                <div className="w-full bg-gray-600 rounded-full h-1 mb-3">
                  <div className="bg-white h-1 rounded-full" style={{ width: "35%" }}></div>
                </div>

                {/* Control Buttons */}
                <div className="flex items-center justify-center space-x-4">
                  <Button variant="ghost" size="sm" className="text-white hover:bg-white/20 p-2 rounded-full">
                    <SkipBack className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm" className="text-white hover:bg-white/20 p-2 rounded-full">
                    <Play className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm" className="text-white hover:bg-white/20 p-2 rounded-full">
                    <Pause className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm" className="text-white hover:bg-white/20 p-2 rounded-full">
                    <SkipForward className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm" className="text-white hover:bg-white/20 p-2 rounded-full">
                    <Volume2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
            
            {/* Upload Video Button */}
            <div className="mt-4 space-y-2">
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button 
                onClick={handleUpload}
                variant="default"
                size="lg"
                className="w-full bg-blue-600 hover:bg-blue-700"
                disabled={uploading}
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    📤 Upload Video for Fire Detection Analysis
                  </>
                )}
              </Button>
              
              {uploadStatus && (
                <div className="text-sm text-center p-2 rounded bg-muted">
                  {uploadStatus}
                </div>
              )}
              
              <p className="text-xs text-muted-foreground text-center">
                Upload a video to analyze for fire, smoke, and security threats
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Generate Report Widget */}
        <Card className="shadow-lg border-3 shadow-gray-500/50 hover:shadow-gray-500/70 transition-shadow duration-300">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center space-x-2 text-xl">
              <FileText className="h-5 w-5 text-primary" />
              <span>Generate Report</span>
            </CardTitle>
            <CardDescription>Get comprehensive summaries of suspicious behaviors and alerts</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-muted-foreground text-sm leading-relaxed">
              Generate detailed reports with incident summaries, timelines, and analytics.
            </p>
            <Button
              onClick={() => setShowReportModal(true)}
              className="w-full"
              size="lg"
            >
              Get Report →
            </Button>
          </CardContent>
        </Card>

        {/* Real-Time Alerts Widget */}
        <Card className="shadow-lg border-3 shadow-gray-500/50 hover:shadow-gray-500/70 transition-shadow duration-300">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center space-x-2 text-xl">
              <AlertTriangle className="h-5 w-5 text-primary" />
              <span>Real-Time Alerts</span>
            </CardTitle>
            <CardDescription>Live notifications of detected security incidents</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center space-x-3 p-3 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                <div className="w-3 h-3 bg-orange-500 rounded-full animate-pulse"></div>
                <div>
                  <span className="text-sm font-medium">[2:04 PM] Suspicious activity - Zone 3</span>
                  <p className="text-xs text-muted-foreground">Person loitering near entrance</p>
                </div>
              </div>
              <div className="flex items-center space-x-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                <div>
                  <span className="text-sm font-medium">[1:32 PM] Fire detected - Zone 1</span>
                  <p className="text-xs text-muted-foreground">Smoke detected in warehouse</p>
                </div>
              </div>
              <div className="flex items-center space-x-3 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <div className="w-3 h-3 bg-yellow-500 rounded-full animate-pulse"></div>
                <div>
                  <span className="text-sm font-medium">[1:10 PM] Trespassing - Zone 2</span>
                  <p className="text-xs text-muted-foreground">Unauthorized access detected</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Key Statistics Section */}
      <Card className="shadow-lg border-3 shadow-gray-500/50 hover:shadow-gray-500/70 transition-shadow duration-300">
        <CardHeader className="pb-4">
          <CardTitle className="text-xl">Key Statistics</CardTitle>
          <CardDescription>Overview of today's security metrics and incidents</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center p-4 bg-muted/50 rounded-lg border">
              <div className="text-2xl font-bold text-primary">12</div>
              <div className="text-sm text-muted-foreground">Total Incidents Today</div>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg border">
              <div className="text-2xl font-bold text-orange-500">3</div>
              <div className="text-sm text-muted-foreground">Active Alerts</div>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg border">
              <div className="text-2xl font-bold text-red-500">Fighting</div>
              <div className="text-sm text-muted-foreground">Most Common Incident</div>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg border">
              <div className="text-2xl font-bold text-blue-500">Zone 3</div>
              <div className="text-sm text-muted-foreground">Most Active Zone</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Upload Modal - ONLY THIS CHANGED */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-card border-border p-6 w-full max-w-md">
            <h3 className="text-white text-xl font-semibold mb-4">Upload Videos</h3>
            <div className="space-y-4">
              <div 
                className="border-3 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                {selectedFile ? (
                  <div>
                    <p className="text-white font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <p className="text-muted-foreground">Drag and drop videos here or click to browse</p>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/mp4,video/avi,video/mov,video/x-matroska,video/x-ms-wmv,video/x-flv"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </div>
              
              {uploadStatus && (
                <div className="text-center space-y-2">
                  <p className="text-sm">{uploadStatus}</p>
                  {currentVideoId && uploadStatus.includes('✅') && (
                    <Button 
                      onClick={() => handleViewResults(currentVideoId)}
                      variant="outline"
                      size="sm"
                      className="w-full"
                    >
                      View Processing Results →
                    </Button>
                  )}
                  {/* Manual navigation button for stuck processing */}
                  {currentVideoId && (uploadStatus.includes('Processing... 10%') || uploadStatus.includes('Processing...')) && (
                    <div className="space-y-2">
                      <p className="text-xs text-muted-foreground">
                        Processing taking too long? Check if results are available:
                      </p>
                      <Button 
                        onClick={() => handleViewResults(currentVideoId)}
                        variant="secondary"
                        size="sm"
                        className="w-full"
                      >
                        🔍 Check Results Manually
                      </Button>
                    </div>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setShowUploadModal(false)
                    setSelectedFile(null)
                    setUploadStatus("")
                  }} 
                  className="flex-1"
                  disabled={uploading}
                >
                  Cancel
                </Button>
                <Button 
                  onClick={handleUpload}
                  className="bg-primary hover:bg-primary/90 text-primary-foreground flex-1"
                  disabled={!selectedFile || uploading}
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    'Upload'
                  )}
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Report Modal */}
      {showReportModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="bg-card border-border p-6 w-full max-w-md">
            <h3 className="text-white text-xl font-semibold mb-4">Generate Report</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-muted-foreground mb-2">Date Range</label>
                <div className="grid grid-cols-2 gap-2">
                  <Input type="date" className="bg-input border-border text-white" />
                  <Input type="date" className="bg-input border-border text-white" />
                </div>
              </div>
              <div>
                <label className="block text-sm text-muted-foreground mb-2">Format</label>
                <select className="w-full bg-input border border-border rounded-lg px-3 py-2 text-white">
                  <option value="pdf">PDF</option>
                  <option value="excel">Excel</option>
                  <option value="csv">CSV</option>
                </select>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setShowReportModal(false)} className="flex-1">
                  Cancel
                </Button>
                <Button className="bg-primary hover:bg-primary/90 text-primary-foreground flex-1">Download</Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}