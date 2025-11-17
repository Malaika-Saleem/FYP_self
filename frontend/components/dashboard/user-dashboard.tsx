"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Search, Upload, Play, Pause, SkipBack, SkipForward, Volume2, FileText, AlertTriangle, Loader2, X } from "lucide-react"
import { Input } from "@/components/ui/input"
import { useRouter } from "next/navigation"
import { useState, useRef, useEffect } from "react"

interface UserDashboardProps {
  userRole: "user" | "admin"
}

interface VideoResults {
  video_info: any
  keyframes_available: boolean
  keyframes_count: number
  events_available: boolean
  events_count: number
  detections_available: boolean
  detections_count: number
  detections_summary?: {
    by_class?: Record<string, number>
    average_confidence?: number
    threat_objects?: string[]
  }
  threat_assessment?: any
  compressed_video_url?: string
  compressed_video_available?: boolean
}

interface Keyframe {
  filename: string
  url?: string
  presigned_url?: string
  annotated_url?: string
  annotated_presigned_url?: string
  timestamp: number
  has_detections: boolean
  has_faces?: boolean
  face_count?: number
  detection_count?: number
  objects?: string[]
  confidence_avg?: number
}

interface DetectedFace {
  face_id: string
  event_id: string
  detected_at: string
  confidence_score?: number
  face_image_path?: string
  minio_object_key?: string
}

export function UserDashboard({ userRole }: UserDashboardProps) {
  const router = useRouter()
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showReportModal, setShowReportModal] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string>("")
  const [currentVideoId, setCurrentVideoId] = useState<string | null>(null)
  const [videoResults, setVideoResults] = useState<VideoResults | null>(null)
  const [compressedVideoUrl, setCompressedVideoUrl] = useState<string | null>(null)
  const [keyframes, setKeyframes] = useState<Keyframe[]>([])
  const [detectedFaces, setDetectedFaces] = useState<DetectedFace[]>([])
  const [statistics, setStatistics] = useState({
    totalIncidents: 0,
    activeAlerts: 0,
    mostCommonIncident: "None",
    mostActiveZone: "N/A"
  })
  const fileInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const handleSearchClick = () => {
    router.push("/search")
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Clear all previous video data when selecting a new file
      console.log('🧹 Clearing previous video data for new upload')
      setKeyframes([])
      setDetectedFaces([])
      setVideoResults(null)
      setCompressedVideoUrl(null)
      setCurrentVideoId(null)
      setStatistics({
        totalIncidents: 0,
        activeAlerts: 0,
        mostCommonIncident: "None",
        mostActiveZone: "N/A"
      })
      
      setSelectedFile(file)
      setUploadStatus("")
      setShowUploadModal(true)
    }
  }

  const handleUpload = () => {
    fileInputRef.current?.click()
  }

  const fetchVideoResults = async (videoId: string) => {
    try {
      console.log('🔄 Fetching video results for:', videoId)
      
      // Clear old data if this is a different video than what's currently displayed
      if (currentVideoId && currentVideoId !== videoId) {
        console.log('🧹 Clearing data for different video:', currentVideoId, '->', videoId)
        setKeyframes([])
        setDetectedFaces([])
        setVideoResults(null)
        setCompressedVideoUrl(null)
      }
      
      // Always set compressed video URL first (will fallback gracefully if not available)
      console.log('✅ Setting compressed video URL')
      setCompressedVideoUrl(`/api/video/compressed/${videoId}`)
      
      // Step 1: Fetch video status (includes metadata)
      console.log('📊 Fetching status data...')
      const statusResponse = await fetch(`/api/video/status/${videoId}`)
      if (!statusResponse.ok) {
        console.error('❌ Failed to fetch video status:', statusResponse.status, statusResponse.statusText)
        const errorText = await statusResponse.text()
        console.error('❌ Status error details:', errorText)
        return
      }
      
      const statusData = await statusResponse.json()
      console.log('📊 Status data received:', JSON.stringify(statusData, null, 2))

      // Update compressed video URL from status if available
      if (statusData.compressed_video_url) {
        // If it's a full URL, use it directly; otherwise use the API route
        if (statusData.compressed_video_url.startsWith('http')) {
          setCompressedVideoUrl(statusData.compressed_video_url)
        } else {
          // Use Next.js API route for proxying
          setCompressedVideoUrl(`/api/video/compressed/${videoId}`)
        }
        console.log('✅ Updated compressed video URL from status:', statusData.compressed_video_url)
      } else {
        // Fallback: always try the API route
        setCompressedVideoUrl(`/api/video/compressed/${videoId}`)
        console.log('✅ Using default compressed video URL')
      }

      // Step 2: Try to fetch comprehensive results with proper error handling
      console.log('📋 Fetching comprehensive results...')
      let videoResultsData: VideoResults | null = null
      
      try {
        const resultsResponse = await fetch(`/api/video/results/${videoId}`)
        if (resultsResponse.ok) {
          videoResultsData = await resultsResponse.json() as VideoResults
          console.log('📋 Comprehensive results received:', JSON.stringify(videoResultsData, null, 2))
          
          // Update compressed video URL from results if available
          if (videoResultsData.compressed_video_url) {
            if (videoResultsData.compressed_video_url.startsWith('http')) {
              setCompressedVideoUrl(videoResultsData.compressed_video_url)
            } else {
              setCompressedVideoUrl(`/api/video/compressed/${videoId}`)
            }
            console.log('✅ Updated compressed video URL from results')
          }
        } else {
          const errorText = await resultsResponse.text()
          console.warn('⚠️ Failed to fetch comprehensive results:', resultsResponse.status, errorText)
        }
      } catch (resultsErr) {
        console.warn('⚠️ Results fetch error:', resultsErr)
      }
      
      // Create fallback results from status data if comprehensive results unavailable
      if (!videoResultsData) {
        console.log('📋 Creating fallback results from status data')
        videoResultsData = {
          video_info: statusData,
          keyframes_available: (statusData.keyframe_count || statusData.meta_data?.keyframe_count || 0) > 0,
          keyframes_count: statusData.keyframe_count || statusData.meta_data?.keyframe_count || 0,
          events_available: (statusData.event_count || statusData.meta_data?.event_count || 0) > 0,
          events_count: statusData.event_count || statusData.meta_data?.event_count || 0,
          detections_available: (statusData.detection_count || statusData.meta_data?.detection_count || 0) > 0,
          detections_count: statusData.detection_count || statusData.meta_data?.detection_count || 0
        }
      }
      
      setVideoResults(videoResultsData)
      updateStatistics(videoResultsData)

      // Step 3: Fetch keyframes with detections (use presigned URLs from status if available)
      let keyframesToSet: Keyframe[] = []
      
      // First try to use keyframes from status if available
      if (statusData.keyframes_urls && Array.isArray(statusData.keyframes_urls)) {
        console.log('✅ Using keyframes from status data:', statusData.keyframes_urls.length)
        keyframesToSet = statusData.keyframes_urls.map((kf: any) => ({
          filename: kf.filename || `frame_${kf.frame_number || 0}.jpg`,
          presigned_url: kf.presigned_url,
          url: kf.presigned_url,
          timestamp: kf.timestamp || 0,
          has_detections: false // Will be updated from detections
        }))
      }
      
      // Also fetch from keyframes endpoint for detection info
      const keyframesResponse = await fetch(`/api/video/keyframes/${videoId}?filter_detections=true`)
      if (keyframesResponse.ok) {
        const keyframesData = await keyframesResponse.json()
        console.log('🖼️ Keyframes data:', keyframesData)
        
        if (keyframesData.keyframes && keyframesData.keyframes.length > 0) {
          // Merge detection info with keyframes
          const keyframesWithDetections = keyframesData.keyframes.map((kf: any) => ({
            filename: kf.filename,
            presigned_url: kf.presigned_url || kf.url,
            url: kf.presigned_url || kf.url,
            timestamp: kf.timestamp || 0,
            has_detections: kf.has_detections || false,
            detection_count: kf.detection_count || 0,
            objects: kf.objects || []
          }))
          
          // Use keyframes from endpoint if they have detection info, otherwise use status keyframes
          if (keyframesWithDetections.some((kf: Keyframe) => kf.has_detections)) {
            keyframesToSet = keyframesWithDetections
          } else if (keyframesToSet.length === 0) {
            keyframesToSet = keyframesWithDetections
          }
        }
      }
      
      if (keyframesToSet.length > 0) {
        console.log('✅ Setting keyframes:', keyframesToSet.length)
        setKeyframes(keyframesToSet)
      } else {
        console.warn('⚠️ No keyframes found')
      }

      // Step 4: Fetch detected faces with proper error handling
      console.log('👤 Fetching detected faces...')
      try {
        const facesResponse = await fetch(`/api/video/faces/${videoId}`)
        if (facesResponse.ok) {
          const facesData = await facesResponse.json()
          console.log('👤 Faces data received:', JSON.stringify(facesData, null, 2))
          
          if (facesData.faces && Array.isArray(facesData.faces)) {
            // Process faces to ensure they have proper URLs for display
            const processedFaces = facesData.faces.map((face: DetectedFace) => {
              // Construct face image URL - try MinIO path first, then local path
              let faceImageUrl = undefined
              if (face.minio_object_key) {
                // Use Next.js API route to proxy MinIO face images
                faceImageUrl = `/api/face-image/${face.face_id}`
              } else if (face.face_image_path) {
                faceImageUrl = face.face_image_path
              }
              
              return {
                ...face,
                face_image_path: faceImageUrl,
                face_image_url: faceImageUrl,
                detected_at: face.detected_at || new Date().toISOString(),
                confidence_score: face.confidence_score || 0
              }
            })
            setDetectedFaces(processedFaces)
            console.log('✅ Set detected faces:', processedFaces.length)
          } else if (Array.isArray(facesData)) {
            // Handle case where API returns array directly
            const processedFaces = facesData.map((face: DetectedFace) => ({
              ...face,
              face_image_url: face.minio_object_key ? `/api/face-image/${face.face_id}` : face.face_image_path
            }))
            setDetectedFaces(processedFaces)
            console.log('✅ Set detected faces (array format):', processedFaces.length)
          } else {
            console.warn('⚠️ Unexpected faces data format:', facesData)
            setDetectedFaces([])
          }
        } else {
          const errorText = await facesResponse.text()
          console.warn('⚠️ Failed to fetch faces:', facesResponse.status, errorText)
          setDetectedFaces([])
        }
      } catch (facesErr) {
        console.warn('⚠️ Faces fetch error:', facesErr)
        setDetectedFaces([])
      }
      
      console.log('✅ Video results fetch complete!')
      
    } catch (err) {
      console.error('❌ Error fetching video results:', err)
      // Still try to set basic info from status if available
      try {
        const statusResponse = await fetch(`/api/video/status/${videoId}`)
        if (statusResponse.ok) {
          const statusData = await statusResponse.json()
          if (statusData.compressed_video_url) {
            if (statusData.compressed_video_url.startsWith('http')) {
              setCompressedVideoUrl(statusData.compressed_video_url)
            } else {
              setCompressedVideoUrl(`/api/video/compressed/${videoId}`)
            }
          } else {
            // Always try the API route as fallback
            setCompressedVideoUrl(`/api/video/compressed/${videoId}`)
          }
        } else {
          // Even if status fails, try the API route
          setCompressedVideoUrl(`/api/video/compressed/${videoId}`)
        }
      } catch (statusErr) {
        console.error('❌ Failed to fetch status as fallback:', statusErr)
        // Still try the API route
        setCompressedVideoUrl(`/api/video/compressed/${videoId}`)
      }
    }
  }

  const updateStatistics = (results: VideoResults) => {
    // Extract detection types from results if available
    let mostCommonIncident = "None"
    if (results.detections_count > 0) {
      // Try to get detection types from results
      const detectionsSummary = results.detections_summary
      if (detectionsSummary && detectionsSummary.by_class) {
        // Find the most common detection class
        const classes = Object.entries(detectionsSummary.by_class) as [string, number][]
        if (classes.length > 0) {
          const sorted = classes.sort((a, b) => b[1] - a[1])
          mostCommonIncident = sorted[0][0].charAt(0).toUpperCase() + sorted[0][0].slice(1)
        } else {
          mostCommonIncident = "Security Threat"
        }
      } else {
        mostCommonIncident = "Security Threat"
      }
    }
    
    setStatistics({
      totalIncidents: results.events_count || 0,
      activeAlerts: results.detections_count || 0,
      mostCommonIncident: mostCommonIncident,
      mostActiveZone: "Current Video"
    })
  }

  const handleFileUpload = async (file: File) => {
    // Clear all previous video data when starting a new upload
    console.log('🧹 Clearing previous video data for new upload')
    setKeyframes([])
    setDetectedFaces([])
    setVideoResults(null)
    setCompressedVideoUrl(null)
    setCurrentVideoId(null)
    setStatistics({
      totalIncidents: 0,
      activeAlerts: 0,
      mostCommonIncident: "None",
      mostActiveZone: "N/A"
    })
    
    setUploading(true)
    setProcessing(true)
    setUploadStatus("Uploading video...")
    setShowUploadModal(true)

    try {
      const formData = new FormData()
      formData.append('video', file)
      formData.append('configType', 'detectifai')

      const response = await fetch('/api/video/upload', {
        method: 'POST',
        body: formData,
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Upload failed')
      }

      if (!data.success) {
        throw new Error(data.error || 'Upload failed')
      }

      const videoId = data.video_id
      setUploadStatus(`✅ Upload successful! Processing video...`)
      setCurrentVideoId(videoId)

      // Poll for processing completion
      pollIntervalRef.current = setInterval(async () => {
        try {
          const statusResponse = await fetch(`/api/video/status/${videoId}`)
          const statusData = await statusResponse.json()
          
          // Debug logging
          console.log('Status check:', {
            status: statusData.status,
            meta_status: statusData.meta_data?.processing_status,
            progress: statusData.processing_progress || statusData.meta_data?.processing_progress,
            fullData: statusData
          })
          
          // Update UI with processing status
          const progress = statusData.processing_progress || statusData.meta_data?.processing_progress || statusData.progress || 0
          const message = statusData.processing_message || statusData.meta_data?.processing_message || statusData.message || 'Processing...'
          setUploadStatus(`${message} (${progress}%)`)
          
          // Check for completion - check multiple possible fields
          // More comprehensive completion check
          const isCompleted = 
            (statusData.status === 'completed') ||
            (statusData.processing_status === 'completed') ||
            (statusData.meta_data?.processing_status === 'completed') ||
            (statusData.progress === 100 && statusData.status !== 'processing') ||
            (statusData.processing_progress === 100 && statusData.status !== 'processing') ||
            (statusData.meta_data?.processing_progress === 100 && statusData.meta_data?.processing_status !== 'processing') ||
            (statusData.meta_data?.progress === 100 && statusData.meta_data?.status !== 'processing')
          
          const isFailed = 
            statusData.status === 'failed' || 
            statusData.processing_status === 'failed' ||
            statusData.meta_data?.processing_status === 'failed' ||
            statusData.meta_data?.status === 'failed'
          
          if (isCompleted) {
            console.log('🎉 Processing completed! Fetching results...')
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            setUploadStatus("✅ Processing complete! Fetching results...")
            
            // Clear processing state BEFORE fetching results to remove blur
            setProcessing(false)
            setUploading(false)
            
            // Fetch results
            try {
              await fetchVideoResults(videoId)
              setUploadStatus("✅ Results loaded successfully!")
            } catch (fetchError) {
              console.error('Failed to fetch results:', fetchError)
              setUploadStatus("⚠️ Processing complete, but failed to load results")
            }
            
            // Close modal after results are fetched
            setTimeout(() => {
              setShowUploadModal(false)
              setUploadStatus("")
            }, 2000)
            
          } else if (isFailed) {
            console.log('❌ Processing failed')
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current)
              pollIntervalRef.current = null
            }
            const errorMessage = statusData.message || statusData.meta_data?.error_message || statusData.error || 'Unknown processing error'
            setUploadStatus(`❌ Processing failed: ${errorMessage}`)
            setProcessing(false)
            setUploading(false)
          } else {
            // Update progress message
            const progress = statusData.progress || statusData.processing_progress || statusData.meta_data?.progress || statusData.meta_data?.processing_progress || 0
            const message = statusData.message || statusData.meta_data?.message || 'Processing...'
            setUploadStatus(`🔄 ${message} (${Math.round(progress)}%)`)
          }
        } catch (err) {
          console.error('Polling error:', err)
        }
      }, 2000) // Poll every 2 seconds

    } catch (err) {
      setUploadStatus(`❌ Error: ${err instanceof Error ? err.message : 'Upload failed'}`)
      setProcessing(false)
      setUploading(false)
    }
  }

  useEffect(() => {
    // Cleanup polling on unmount
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [])

  const handleViewResults = (videoId: string) => {
    router.push(`/results/${videoId}`)
  }

  const handleGenerateReport = () => {
    if (currentVideoId) {
      // Ensure we have fresh data for the current video
      console.log('📊 Generating report for video:', currentVideoId)
      // Fetch latest results before showing modal to ensure we have current video's data
      fetchVideoResults(currentVideoId).then(() => {
        setShowReportModal(true)
      }).catch((error) => {
        console.error('Failed to fetch results for report:', error)
        // Still show modal even if fetch fails, but with warning
        setShowReportModal(true)
      })
    } else {
      alert("Please upload and process a video first")
    }
  }

  return (
    <div className="space-y-8 relative">
      {/* Blur overlay when processing */}
      {processing && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40 pointer-events-none" />
      )}

      {/* Main Dashboard Grid */}
      <div className={`grid grid-cols-1 lg:grid-cols-2 gap-8 ${processing ? 'blur-sm' : ''}`}>
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
              {compressedVideoUrl ? (
                <video
                  ref={videoRef}
                  src={compressedVideoUrl}
                  className="w-full h-48 object-contain bg-black"
                  controls
                  preload="metadata"
                  playsInline
                  onLoadedMetadata={(e) => {
                    console.log('✅ Video metadata loaded successfully')
                    const videoEl = e.target as HTMLVideoElement
                    console.log('Video duration:', videoEl.duration, 'seconds')
                  }}
                  onCanPlay={(e) => {
                    console.log('✅ Video can play')
                  }}
                  onError={(e) => {
                    console.error('❌ Video load error:', e)
                    const videoEl = e.target as HTMLVideoElement
                    const error = videoEl.error
                    if (error) {
                      console.error('Video error code:', error.code)
                      console.error('Video error message:', error.message)
                    }
                    // Don't hide the video element, just log the error
                    // The video element will show its own error state
                  }}
                  onLoadStart={() => {
                    console.log('🔄 Video loading started')
                  }}
                >
                  <source src={compressedVideoUrl} type="video/mp4" />
                  Your browser does not support the video tag.
                </video>
              ) : (
                <div className="w-full h-48 flex items-center justify-center bg-muted">
                  <div className="text-center text-muted-foreground">
                    <Play className="w-12 h-12 mx-auto mb-2 opacity-50" />
                    <p className="text-sm">No video available</p>
                    <p className="text-xs mt-1">Upload a video to see it here</p>
                  </div>
                </div>
              )}

              {/* Video Controls Overlay - only show if no video loaded */}
              {!compressedVideoUrl && (
                <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4">
                  <div className="flex items-center justify-between text-white text-sm mb-2">
                    <span>0:00</span>
                    <span>0:00</span>
                  </div>
                  <div className="w-full bg-gray-600 rounded-full h-1 mb-3">
                    <div className="bg-white h-1 rounded-full" style={{ width: "0%" }}></div>
                  </div>
                  <div className="flex items-center justify-center space-x-4">
                    <Button variant="ghost" size="sm" className="text-white hover:bg-white/20 p-2 rounded-full">
                      <Play className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              )}
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
              onClick={handleGenerateReport}
              className="w-full"
              size="lg"
              disabled={!currentVideoId}
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
              {videoResults && videoResults.detections_count > 0 ? (
                <div className="space-y-2">
                  <div className="flex items-center space-x-3 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                    <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse"></div>
                    <div className="flex-1">
                      <span className="text-sm font-medium">Security Threat Detected</span>
                      <p className="text-xs text-muted-foreground">{videoResults.detections_count} objects detected</p>
                    </div>
                  </div>
                  {/* Show specific detection types */}
                  {videoResults.detections_summary?.by_class && Object.keys(videoResults.detections_summary.by_class).length > 0 && (
                    <div className="p-2 bg-muted/50 rounded-lg">
                      <p className="text-xs font-medium mb-1">Detected Objects:</p>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(videoResults.detections_summary.by_class).map(([className, count]) => (
                          <span 
                            key={className}
                            className="text-xs bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 px-2 py-0.5 rounded font-medium"
                          >
                            {className.charAt(0).toUpperCase() + className.slice(1)}: {count as number}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center space-x-3 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <div>
                    <span className="text-sm font-medium">No Active Alerts</span>
                    <p className="text-xs text-muted-foreground">All systems normal</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Key Statistics Section */}
      <Card className={`shadow-lg border-3 shadow-gray-500/50 hover:shadow-gray-500/70 transition-shadow duration-300 ${processing ? 'blur-sm' : ''}`}>
        <CardHeader className="pb-4">
          <CardTitle className="text-xl">Key Statistics</CardTitle>
          <CardDescription>Overview of security metrics and incidents</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center p-4 bg-muted/50 rounded-lg border">
              <div className="text-2xl font-bold text-primary">{statistics.totalIncidents}</div>
              <div className="text-sm text-muted-foreground">Total Events</div>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg border">
              <div className="text-2xl font-bold text-orange-500">{statistics.activeAlerts}</div>
              <div className="text-sm text-muted-foreground">Detections</div>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg border">
              <div className="text-2xl font-bold text-red-500">{statistics.mostCommonIncident}</div>
              <div className="text-sm text-muted-foreground">Threat Level</div>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg border">
              <div className="text-2xl font-bold text-blue-500">{keyframes.length}</div>
              <div className="text-sm text-muted-foreground">Key Frames</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Upload Modal with Loading */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <Card className="bg-card border-border p-6 w-full max-w-md relative">
            <Button
              variant="ghost"
              size="sm"
              className="absolute top-4 right-4"
              onClick={() => {
                // Always allow closing, but clear processing state
                if (pollIntervalRef.current) {
                  clearInterval(pollIntervalRef.current)
                  pollIntervalRef.current = null
                }
                setProcessing(false)
                setUploading(false)
                setShowUploadModal(false)
                setSelectedFile(null)
                setUploadStatus("")
                // Still fetch results in background if video was processed
                if (currentVideoId) {
                  fetchVideoResults(currentVideoId).catch(console.error)
                }
              }}
            >
              <X className="w-4 h-4" />
            </Button>
            
            <h3 className="text-xl font-semibold mb-4">Upload Video</h3>
            <div className="space-y-4">
              <div 
                className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary transition-colors"
                onClick={() => !processing && !uploading && fileInputRef.current?.click()}
              >
                {processing || uploading ? (
                  <div className="space-y-4">
                    <Loader2 className="w-12 h-12 text-primary mx-auto animate-spin" />
                    <div>
                      <p className="text-lg font-medium">{uploadStatus || "Processing..."}</p>
                      <p className="text-sm text-muted-foreground mt-2">Please wait while we process your video</p>
                    </div>
                  </div>
                ) : selectedFile ? (
                  <div>
                    <p className="font-medium">{selectedFile.name}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                ) : (
                  <>
                    <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                    <p className="text-muted-foreground">Drag and drop videos here or click to browse</p>
                  </>
                )}
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="video/mp4,video/avi,video/mov,video/x-matroska,video/x-ms-wmv,video/x-flv"
                  onChange={handleFileSelect}
                  className="hidden"
                  disabled={processing || uploading}
                />
              </div>
              
              {!processing && !uploading && selectedFile && (
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    onClick={() => {
                      setShowUploadModal(false)
                      setSelectedFile(null)
                      setUploadStatus("")
                    }} 
                    className="flex-1"
                  >
                    Cancel
                  </Button>
                  <Button 
                    onClick={() => selectedFile && handleFileUpload(selectedFile)}
                    className="bg-primary hover:bg-primary/90 text-primary-foreground flex-1"
                  >
                    Upload
                  </Button>
                </div>
              )}
              
              {/* Manual refresh button if stuck */}
              {processing && currentVideoId && (
                <div className="mt-4 space-y-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={async () => {
                      // Manually check status and fetch results
                      try {
                        const statusResponse = await fetch(`/api/video/status/${currentVideoId}`)
                        const statusData = await statusResponse.json()
                        console.log('Manual status check:', statusData)
                        
                        // Check for completion - multiple ways
                        const isCompleted = 
                          statusData.status === 'completed' || 
                          statusData.meta_data?.processing_status === 'completed' ||
                          (statusData.processing_progress === 100) ||
                          (statusData.meta_data?.processing_progress === 100)
                        
                        if (isCompleted) {
                          // Clear polling
                          if (pollIntervalRef.current) {
                            clearInterval(pollIntervalRef.current)
                            pollIntervalRef.current = null
                          }
                          
                          // Clear processing state FIRST to remove blur
                          setProcessing(false)
                          setUploading(false)
                          setUploadStatus("✅ Processing complete!")
                          
                          // Fetch results
                          await fetchVideoResults(currentVideoId)
                          
                          // Close modal
                          setTimeout(() => {
                            setShowUploadModal(false)
                          }, 1500)
                        } else {
                          setUploadStatus(`Status: ${statusData.status || statusData.meta_data?.processing_status || 'unknown'} (${statusData.processing_progress || statusData.meta_data?.processing_progress || 0}%)`)
                        }
                      } catch (err) {
                        console.error('Manual check error:', err)
                        setUploadStatus(`Error checking status: ${err instanceof Error ? err.message : 'Unknown error'}`)
                      }
                    }}
                    className="w-full"
                  >
                    🔄 Check Status Manually
                  </Button>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      // Force clear everything and close modal
                      if (pollIntervalRef.current) {
                        clearInterval(pollIntervalRef.current)
                        pollIntervalRef.current = null
                      }
                      setProcessing(false)
                      setUploading(false)
                      setShowUploadModal(false)
                      setUploadStatus("")
                      // Still try to fetch results in background
                      if (currentVideoId) {
                        fetchVideoResults(currentVideoId).catch(console.error)
                      }
                    }}
                    className="w-full text-muted-foreground"
                  >
                    Dismiss & Continue
                  </Button>
                </div>
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Report Modal with Key Frames and Faces */}
      {showReportModal && currentVideoId && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <Card className="bg-card border-border p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-xl font-semibold">Security Report</h3>
                <p className="text-xs text-muted-foreground mt-1">Video ID: {currentVideoId.substring(0, 20)}...</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowReportModal(false)}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="space-y-6">
              {/* Summary Section */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-3 bg-muted/50 rounded-lg">
                  <div className="text-lg font-bold">{videoResults?.events_count || 0}</div>
                  <div className="text-xs text-muted-foreground">Events</div>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg">
                  <div className="text-lg font-bold">{videoResults?.detections_count || 0}</div>
                  <div className="text-xs text-muted-foreground">Detections</div>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg">
                  <div className="text-lg font-bold">{keyframes.length}</div>
                  <div className="text-xs text-muted-foreground">Key Frames</div>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg">
                  <div className="text-lg font-bold">{detectedFaces.length}</div>
                  <div className="text-xs text-muted-foreground">Faces Detected</div>
                </div>
              </div>

              {/* Key Frames with Detections */}
              {keyframes.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold mb-3">Key Frames with Detections</h4>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {keyframes.map((keyframe, idx) => (
                      <div 
                        key={idx} 
                        className={`border rounded-lg overflow-hidden ${
                          keyframe.has_detections ? 'border-red-500 border-2 shadow-lg' : ''
                        }`}
                      >
                        <div className="relative">
                          <img 
                            src={
                              (keyframe.has_detections && keyframe.annotated_presigned_url) 
                                ? keyframe.annotated_presigned_url 
                                : keyframe.presigned_url || keyframe.url || '/placeholder.jpg'
                            } 
                            alt={`Keyframe ${idx + 1}`}
                            className="w-full h-32 object-cover"
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = "/placeholder.jpg"
                            }}
                          />
                          {keyframe.has_detections && (
                            <div className={`absolute top-2 right-2 text-white text-xs px-2 py-1 rounded font-bold ${
                              keyframe.has_faces 
                                ? 'bg-blue-600' 
                                : 'bg-red-600'
                            }`}>
                              {keyframe.has_faces && keyframe.face_count 
                                ? `${keyframe.face_count} Face${keyframe.face_count !== 1 ? 's' : ''}`
                                : `${keyframe.detection_count || 0} Detection${keyframe.detection_count !== 1 ? 's' : ''}`
                              }
                            </div>
                          )}
                        </div>
                        <div className="p-2 bg-card">
                          <p className="text-xs text-muted-foreground mb-1">
                            Time: {keyframe.timestamp.toFixed(1)}s
                          </p>
                          {keyframe.has_detections && (
                            <div className="space-y-1">
                              {keyframe.objects && keyframe.objects.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {keyframe.objects.map((obj, objIdx) => {
                                    // Highlight "Face Detected" with different styling
                                    const isFace = obj.toLowerCase().includes('face')
                                    return (
                                      <span 
                                        key={objIdx}
                                        className={`text-xs px-2 py-0.5 rounded font-medium ${
                                          isFace 
                                            ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700' 
                                            : 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'
                                        }`}
                                      >
                                        {obj}
                                        {isFace && keyframe.face_count && keyframe.face_count > 1 && (
                                          <span className="ml-1">({keyframe.face_count})</span>
                                        )}
                                      </span>
                                    )
                                  })}
                                </div>
                              )}
                              {keyframe.confidence_avg && (
                                <p className="text-xs text-muted-foreground">
                                  Avg Confidence: {(keyframe.confidence_avg * 100).toFixed(1)}%
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Detected Faces */}
              {detectedFaces.length > 0 && (
                <div>
                  <h4 className="text-lg font-semibold mb-3">Detected Faces in Suspicious Activity</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {detectedFaces.map((face, idx) => (
                      <div key={idx} className="border rounded-lg overflow-hidden">
                        {face.face_image_path ? (
                          <img 
                            src={`/api/face-image/${face.face_id}`}
                            alt={`Face ${idx + 1}`}
                            className="w-full h-32 object-cover"
                            onError={(e) => {
                              (e.target as HTMLImageElement).src = "/placeholder-user.jpg"
                            }}
                          />
                        ) : (
                          <div className="w-full h-32 bg-muted flex items-center justify-center">
                            <span className="text-muted-foreground">No image</span>
                          </div>
                        )}
                        <div className="p-2">
                          <p className="text-xs font-medium">Face ID: {face.face_id.substring(0, 8)}...</p>
                          {face.confidence_score && (
                            <p className="text-xs text-muted-foreground">
                              Confidence: {(face.confidence_score * 100).toFixed(1)}%
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {keyframes.length === 0 && detectedFaces.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <p>No detections or faces found in this video.</p>
                </div>
              )}

              <div className="flex gap-2 pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => setShowReportModal(false)}
                  className="flex-1"
                >
                  Close
                </Button>
                <Button 
                  onClick={() => currentVideoId && handleViewResults(currentVideoId)}
                  className="bg-primary hover:bg-primary/90 text-primary-foreground flex-1"
                >
                  View Full Results
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}
