"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Search, Upload, Play, Pause, SkipBack, SkipForward, Volume2, FileText, AlertTriangle, Loader2, X, ImageIcon, Video, Square } from "lucide-react"
import { Input } from "@/components/ui/input"
import { useRouter } from "next/navigation"
import { useState, useRef, useEffect } from "react"
import { useSession } from "next-auth/react"
import { ReportWidget } from "./widgets/report-widget"
import { useAlerts } from "@/lib/useAlerts"
import { AlertPopup } from "./alert-popup"
import { LiveAlertsPanel } from "./live-alerts-panel"
import { useSubscription } from "@/contexts/subscription-context"
import { FeatureGateOverlay, UsageTooltip, UploadLimitIndicator, PlanBadgeCompact, UpgradeDialog } from "./feature-gate-overlay"
import { DASHBOARD_GATES } from "@/contexts/subscription-context"

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
  behaviors_available?: boolean
  behaviors_count?: number
  behaviors_summary?: {
    total_behaviors?: number
    by_type?: Record<string, number>
    most_common?: string
    average_confidence?: number
    behavior_types?: string[]
  }
  behavior_events?: Array<{
    event_id: string
    event_type: string
    confidence_score: number
    start_timestamp_ms: number
    end_timestamp_ms: number
  }>
  threat_assessment?: any
  compressed_video_url?: string
  compressed_video_available?: boolean
  annotated_video_url?: string
  annotated_video_available?: boolean
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
  api_url?: string
  minio_url?: string
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
  const { data: session } = useSession()
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showReportModal, setShowReportModal] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string>("")
  const [currentVideoId, setCurrentVideoId] = useState<string | null>(null)
  const [videoResults, setVideoResults] = useState<VideoResults | null>(null)
  const [compressedVideoUrl, setCompressedVideoUrl] = useState<string | null>(null)
  const [annotatedVideoUrl, setAnnotatedVideoUrl] = useState<string | null>(null)
  const [keyframes, setKeyframes] = useState<Keyframe[]>([])
  const [detectedFaces, setDetectedFaces] = useState<DetectedFace[]>([])
  const [statistics, setStatistics] = useState({
    totalIncidents: 0,
    activeAlerts: 0,
    mostCommonIncident: "None",
    mostActiveZone: "N/A"
  })
  const [isLiveStreamActive, setIsLiveStreamActive] = useState(false)
  const [liveStreamStats, setLiveStreamStats] = useState<any>(null)
  const [liveStreamUrl, setLiveStreamUrl] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const liveVideoRef = useRef<HTMLImageElement>(null)
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const liveStatsIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Real-time alerts hook — connects to SSE stream
  const {
    alerts: liveAlerts,
    pendingAlerts,
    currentPopupAlert,
    isConnected: isAlertStreamConnected,
    connectionError: alertConnectionError,
    stats: alertStats,
    confirmAlert,
    dismissAlert,
    connect: connectAlertStream,
    dismissPopup,
    sendTestAlert,
  } = useAlerts({ autoConnect: true, enableSound: true })

  // Subscription & plan context
  const {
    planId,
    planName,
    hasSubscription,
    hasFeature,
    isGateUnlocked,
    getUsage,
    loading: subscriptionLoading,
    refreshSubscription,
  } = useSubscription()

  // Upgrade prompt state — shown when user tries a gated action (upload / live)
  const [showUpgradePrompt, setShowUpgradePrompt] = useState(false)
  const [upgradeGateId, setUpgradeGateId] = useState<string>("video_upload")

  const handleSearchClick = () => {
    // NLP/Image search is Pro-only — if not unlocked, show upgrade prompt
    if (!isGateUnlocked("nlp_search")) {
      setUpgradeGateId("nlp_search")
      setShowUpgradePrompt(true)
      return
    }
    router.push("/search")
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      // Check upload limits before proceeding (Pro users have unlimited)
      const videoUsage = getUsage("video_processing")
      const isUnlimited = planId === "detectifai_pro" && videoUsage && videoUsage.limit >= 999999
      if (!isUnlimited && videoUsage && videoUsage.remaining <= 0) {
        alert(`You've reached your upload limit (${videoUsage.limit} videos/month). Please upgrade your plan for more uploads.`)
        return
      }

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
    // Guard: must have subscription with video upload access
    if (!isGateUnlocked("video_upload")) {
      setUpgradeGateId("video_upload")
      setShowUpgradePrompt(true)
      return
    }
    fileInputRef.current?.click()
  }

  const handleStartLiveStream = async () => {
    // Guard: must have subscription for live stream
    if (!isGateUnlocked("live_stream")) {
      setUpgradeGateId("live_stream")
      setShowUpgradePrompt(true)
      return
    }

    try {
      const response = await fetch('/api/live/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          camera_id: 'webcam_01',
          camera_index: 0
        })
      })

      const data = await response.json()
      if (data.success) {
        const flaskUrl = process.env.NEXT_PUBLIC_FLASK_API_URL || 'http://localhost:5000'
        const feedUrl = `${flaskUrl}/api/live/feed/webcam_01?t=${Date.now()}`
        console.log('🎥 Live stream started, feed URL:', feedUrl)

        // Set the URL state - useEffect will handle setting it on the image element
        setLiveStreamUrl(feedUrl)
        setIsLiveStreamActive(true)

        // Start polling for stats
        if (liveStatsIntervalRef.current) {
          clearInterval(liveStatsIntervalRef.current)
        }
        liveStatsIntervalRef.current = setInterval(async () => {
          try {
            const statsResponse = await fetch('/api/live/stats/webcam_01')
            if (statsResponse.ok) {
              const statsData = await statsResponse.json()
              if (statsData.success) {
                setLiveStreamStats(statsData.stats)
              }
            }
          } catch (e) {
            console.error('Error fetching live stats:', e)
          }
        }, 2000) // Poll every 2 seconds
      } else {
        alert('Failed to start live stream: ' + (data.error || 'Unknown error'))
      }
    } catch (error) {
      console.error('Error starting live stream:', error)
      alert('Failed to start live stream')
    }
  }

  const handleStopLiveStream = async () => {
    try {
      const response = await fetch('/api/live/stop/webcam_01', {
        method: 'POST'
      })

      const data = await response.json()
      if (data.success) {
        setIsLiveStreamActive(false)
        if (liveVideoRef.current) {
          liveVideoRef.current.src = ''
        }
        if (liveStatsIntervalRef.current) {
          clearInterval(liveStatsIntervalRef.current)
          liveStatsIntervalRef.current = null
        }
        setLiveStreamStats(null)
      }
    } catch (error) {
      console.error('Error stopping live stream:', error)
    }
  }

  // Effect to set image src when live stream becomes active
  useEffect(() => {
    if (isLiveStreamActive && liveStreamUrl && liveVideoRef.current) {
      console.log('🎥 useEffect: Setting live stream src to:', liveStreamUrl)
      liveVideoRef.current.src = liveStreamUrl

      // Add error handler
      liveVideoRef.current.onerror = (e) => {
        console.error('❌ Live stream image error:', e)
        console.error('❌ Image src:', liveVideoRef.current?.src)
        console.error('❌ Image currentSrc:', liveVideoRef.current?.currentSrc)
      }

      // Add load handler
      liveVideoRef.current.onload = () => {
        console.log('✅ Live stream image loaded successfully')
      }
    }
  }, [isLiveStreamActive, liveStreamUrl])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (liveStatsIntervalRef.current) {
        clearInterval(liveStatsIntervalRef.current)
      }
      if (isLiveStreamActive) {
        handleStopLiveStream()
      }
    }
  }, [])

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

      // Clear video URLs initially to prevent stale state
      setAnnotatedVideoUrl(null)
      // Set compressed video URL tentatively, will be updated/confirmed by status
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

      // Update annotated video URL based on results
      if (videoResultsData?.annotated_video_available) {
        console.log('✅ Annotated video available, setting URL')
        setAnnotatedVideoUrl(`/api/video/annotated/${videoId}`)
      } else if (statusData.meta_data?.annotated_video_available) {
        console.log('✅ Annotated video available (from status), setting URL')
        setAnnotatedVideoUrl(`/api/video/annotated/${videoId}`)
      } else {
        console.log('ℹ️ No annotated video available')
        setAnnotatedVideoUrl(null)
      }

      // Step 3: Fetch keyframes with detections (use presigned URLs from status if available)
      let keyframesToSet: Keyframe[] = []

      // First try to use keyframes from status if available
      if (statusData.keyframes_urls && Array.isArray(statusData.keyframes_urls)) {
        console.log('✅ Using keyframes from status data:', statusData.keyframes_urls.length)
        keyframesToSet = statusData.keyframes_urls.map((kf: any) => ({
          filename: kf.filename || `frame_${kf.frame_number || 0}.jpg`,
          presigned_url: kf.presigned_url,
          url: kf.api_url || kf.url || kf.presigned_url, // Prefer API URL
          api_url: kf.api_url,
          minio_url: kf.minio_url,
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
            url: kf.api_url || kf.minio_url || kf.url || kf.presigned_url, // Prefer API URL
            api_url: kf.api_url,
            minio_url: kf.minio_url,
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

    const behaviorUnlocked = isGateUnlocked("behavior_analysis")

    // Prioritize behavior analysis for most common incident — only if Pro
    if (behaviorUnlocked && results.behaviors_summary?.most_common) {
      const behaviorLabels: Record<string, string> = {
        'fighting': 'Fighting',
        'road_accident': 'Road Accident',
        'wallclimb': 'Wall Climbing'
      }
      mostCommonIncident = behaviorLabels[results.behaviors_summary.most_common] ||
        results.behaviors_summary.most_common.charAt(0).toUpperCase() +
        results.behaviors_summary.most_common.slice(1).replace('_', ' ')
    } else if (results.detections_count > 0) {
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

    // Only include behavior counts in alerts if Pro
    const behaviorAlerts = behaviorUnlocked ? (results.behaviors_count || 0) : 0

    setStatistics({
      totalIncidents: results.events_count || 0,
      activeAlerts: (results.detections_count || 0) + behaviorAlerts,
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

      if (session?.user?.id) {
        formData.append('user_id', session.user.id)
      }

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

      // Immediately set compressed video URL (will be updated when processing completes)
      console.log('🎬 Setting initial compressed video URL for:', videoId)
      setCompressedVideoUrl(`/api/video/compressed/${videoId}`)

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

            // Refresh subscription usage counters (upload count changed)
            refreshSubscription().catch(() => {})

            // Fetch results
            try {
              await fetchVideoResults(videoId)
              setUploadStatus("✅ Results loaded successfully!")
            } catch (fetchError) {
              console.error('Failed to fetch results:', fetchError)
              setUploadStatus("⚠️ Processing complete, but failed to load results")
              // Still try to set compressed video URL even if fetch fails
              if (videoId) {
                console.log('🔄 Setting compressed video URL as fallback')
                setCompressedVideoUrl(`/api/video/compressed/${videoId}`)
              }
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

      {/* Plan badge + usage summary bar */}
      {!subscriptionLoading && (
        <div className="flex items-center justify-between bg-card border rounded-xl px-4 py-2.5">
          <div className="flex items-center gap-3">
            <PlanBadgeCompact />
            {hasSubscription && (
              <span className="text-xs text-muted-foreground hidden sm:inline">
                {planName}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {/* Video upload usage inline */}
            {(() => {
              const videoUsage = getUsage("video_processing")
              if (!videoUsage || !hasSubscription) return null
              
              // Pro users have unlimited uploads
              const isUnlimited = planId === "detectifai_pro" && videoUsage.limit >= 999999
              
              if (isUnlimited) {
                return (
                  <UsageTooltip limitType="video_processing">
                    <div className="flex items-center gap-2 cursor-help">
                      <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden hidden sm:block">
                        <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500" style={{ width: "100%" }} />
                      </div>
                      <span className="text-xs font-medium text-emerald-500">
                        ♾️ Unlimited
                      </span>
                    </div>
                  </UsageTooltip>
                )
              }
              
              const color = videoUsage.remaining <= 0 ? "text-red-500" :
                videoUsage.percentage > 80 ? "text-amber-500" : "text-emerald-500"
              return (
                <UsageTooltip limitType="video_processing">
                  <div className="flex items-center gap-2 cursor-help">
                    <div className="w-16 h-1.5 bg-muted rounded-full overflow-hidden hidden sm:block">
                      <div
                        className={`h-full rounded-full ${
                          videoUsage.remaining <= 0 ? "bg-red-500" :
                          videoUsage.percentage > 80 ? "bg-amber-500" : "bg-emerald-500"
                        }`}
                        style={{ width: `${Math.min(100, videoUsage.percentage)}%` }}
                      />
                    </div>
                    <span className={`text-xs font-medium ${color}`}>
                      {videoUsage.remaining}/{videoUsage.limit} uploads
                    </span>
                  </div>
                </UsageTooltip>
              )
            })()}
            {!hasSubscription && (
              <Button
                variant="outline"
                size="sm"
                className="text-xs h-7 border-purple-500/30 text-purple-400 hover:bg-purple-500/10"
                onClick={() => router.push("/pricing")}
              >
                Upgrade Plan
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Main Dashboard Grid */}
      <div className={`grid grid-cols-1 lg:grid-cols-2 gap-8 ${processing ? 'blur-sm' : ''}`}>
        {/* Search By Prompt Widget — Pro only (NLP search + image search) */}
        <FeatureGateOverlay gateId="nlp_search">
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
                className="w-full pl-10 pr-10 py-3"
              />
              <button
                type="button"
                onClick={() => router.push("/search")}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors"
                title="Search by image"
              >
                <ImageIcon className="w-5 h-5" />
              </button>
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
        </FeatureGateOverlay>

        {/* Video Footage Widget */}
        <Card className="shadow-lg border-3 shadow-gray-500/50 hover:shadow-gray-500/70 transition-shadow duration-300">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center justify-between text-xl">
              <div className="flex items-center space-x-2">
                <Play className="h-5 w-5 text-primary" />
                <span>Video Footage</span>
              </div>
              <div className="flex items-center gap-2">
                {/* Upload limit indicator — shows "X/Y uploads left" */}
                <UsageTooltip limitType="video_processing">
                  <UploadLimitIndicator />
                </UsageTooltip>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowUploadModal(true)}
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Upload
                </Button>
                {!isLiveStreamActive ? (
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleStartLiveStream}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <Video className="w-4 h-4 mr-2" />
                    Start Live
                  </Button>
                ) : (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleStopLiveStream}
                  >
                    <Square className="w-4 h-4 mr-2" />
                    Stop Live
                  </Button>
                )}
              </div>
            </CardTitle>
            <CardDescription>Monitor live surveillance feeds and uploaded videos</CardDescription>
          </CardHeader>
          <CardContent>
            {/* Live Stream */}
            {isLiveStreamActive && (
              <div className="mb-4 space-y-2">
                <div className="relative bg-black rounded-lg overflow-hidden border">
                  {liveStreamUrl ? (
                    <img
                      ref={liveVideoRef}
                      src={liveStreamUrl}
                      alt="Live Stream"
                      className="w-full h-64 object-contain"
                      style={{ imageRendering: 'auto' }}
                      crossOrigin="anonymous"
                      onError={(e) => {
                        console.error('❌ Image onError event:', e)
                        console.error('❌ Image src:', (e.target as HTMLImageElement)?.src)
                      }}
                      onLoad={() => {
                        console.log('✅ Image onLoad event fired')
                      }}
                    />
                  ) : (
                    <div className="w-full h-64 flex items-center justify-center text-gray-400">
                      <p>Waiting for stream...</p>
                    </div>
                  )}
                  <div className="absolute top-2 left-2 bg-red-600 text-white px-2 py-1 rounded text-xs font-bold flex items-center gap-1">
                    <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                    LIVE
                  </div>
                </div>
                {liveStreamStats && (
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>Frames: {liveStreamStats.frames_processed} | Objects: {liveStreamStats.objects_detected} | Events: {liveStreamStats.events_created}</p>
                    <p>FPS: {liveStreamStats.fps?.toFixed(1) || 'N/A'} | Runtime: {Math.floor(liveStreamStats.runtime_seconds || 0)}s</p>
                  </div>
                )}
              </div>
            )}

            {/* Video Player */}
            <div className="relative bg-black rounded-lg overflow-hidden border">
              {(annotatedVideoUrl || compressedVideoUrl) ? (
                <video
                  ref={videoRef}
                  src={annotatedVideoUrl || compressedVideoUrl || undefined}
                  className="w-full h-48 object-contain bg-black"
                  controls
                  preload="metadata"
                  playsInline
                  onLoadedMetadata={(e) => {
                    console.log('✅ Video metadata loaded successfully')
                    const videoEl = e.target as HTMLVideoElement
                    console.log('Video duration:', videoEl.duration, 'seconds')
                    console.log('Video source:', videoEl.src)
                  }}
                  onCanPlay={(e) => {
                    console.log('✅ Video can play')
                  }}
                  onError={(e) => {
                    console.error('❌ Video load error:', e)
                    const videoEl = e.target as HTMLVideoElement
                    const error = videoEl.error
                    console.error('Video error details:', {
                      error: error ? {
                        code: error.code,
                        message: error.message
                      } : null,
                      networkState: videoEl.networkState,
                      readyState: videoEl.readyState,
                      src: videoEl.src,
                      currentSrc: videoEl.currentSrc
                    })

                    // Fallback to compressed video if annotated fails
                    if (annotatedVideoUrl && compressedVideoUrl && videoEl.src.includes('annotated')) {
                      console.log('🔄 Annotated video failed, falling back to compressed...')
                      setTimeout(() => {
                        if (currentVideoId) {
                          videoEl.src = `/api/video/compressed/${currentVideoId}?t=${Date.now()}`
                          videoEl.load()
                        }
                      }, 1000)
                    } else if (error && error.code === 4) {
                      console.log('🔄 Media source error, trying to reload...')
                      setTimeout(() => {
                        if (videoEl.src && currentVideoId) {
                          const newUrl = videoEl.src.includes('annotated')
                            ? `/api/video/annotated/${currentVideoId}?t=${Date.now()}`
                            : `/api/video/compressed/${currentVideoId}?t=${Date.now()}`
                          console.log('🔄 Attempting reload with:', newUrl)
                          videoEl.src = newUrl
                          videoEl.load()
                        }
                      }, 1000)
                    }
                  }}
                  onLoadStart={() => {
                    console.log('🔄 Video load started:', annotatedVideoUrl || compressedVideoUrl)
                  }}
                  onWaiting={() => {
                    console.log('⏳ Video waiting for data...')
                  }}
                  onStalled={() => {
                    console.log('⚠️ Video stalled, trying to recover...')
                  }}
                  onProgress={() => {
                    const videoEl = videoRef.current
                    if (videoEl && videoEl.buffered.length > 0) {
                      const buffered = videoEl.buffered.end(videoEl.buffered.length - 1)
                      const duration = videoEl.duration
                      if (duration > 0) {
                        const percent = (buffered / duration) * 100
                        console.log(`📊 Video buffered: ${percent.toFixed(1)}%`)
                      }
                    }
                  }}
                >
                  <source src={annotatedVideoUrl || compressedVideoUrl || undefined} type="video/mp4" />
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

            {/* Suspicious Events Timeline — only for Pro (behavior_analysis) */}
            {isGateUnlocked("behavior_analysis") && (videoResults?.behavior_events && videoResults.behavior_events.length > 0) && (
              <div className="mt-4 border rounded-lg p-3 bg-muted/30">
                <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-orange-500" />
                  Suspicious Events Timeline
                </h4>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                  {videoResults.behavior_events.map((event, index) => {
                    const formatTime = (ms: number) => {
                      const seconds = Math.floor(ms / 1000)
                      const mins = Math.floor(seconds / 60)
                      const secs = seconds % 60
                      return `${mins}:${secs.toString().padStart(2, '0')}`
                    }

                    const handleJumpToTimestamp = (timestampMs: number) => {
                      if (videoRef.current) {
                        videoRef.current.currentTime = timestampMs / 1000
                        videoRef.current.play().catch(e => console.log('Auto-play blocked:', e))
                      }
                    }

                    const label = event.event_type.replace('behavior_', '').replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())

                    return (
                      <div
                        key={event.event_id || index}
                        onClick={() => handleJumpToTimestamp(event.start_timestamp_ms)}
                        className="flex items-center justify-between p-2 rounded-md bg-background hover:bg-accent cursor-pointer transition-colors border group"
                      >
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${event.event_type.includes('fighting') ? 'bg-red-500' :
                            event.event_type.includes('accident') ? 'bg-orange-500' : 'bg-yellow-500'
                            }`} />
                          <span className="text-sm font-medium">{label}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded font-mono">
                            {formatTime(event.start_timestamp_ms)}
                          </span>
                          <Play className="w-3 h-3 text-primary opacity-0 group-hover:opacity-100 transition-opacity" />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Generate Report Widget - only after video uploaded and analysis complete */}
        <ReportWidget 
          videoId={currentVideoId || undefined} 
          processingComplete={!!currentVideoId && !processing} 
        />

        {/* Behavior Analysis Widget — Pro only */}
        <FeatureGateOverlay gateId="behavior_analysis">
        <Card className="shadow-lg border-3 shadow-gray-500/50 hover:shadow-gray-500/70 transition-shadow duration-300">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center space-x-2 text-xl">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              <span>Behavior Analysis</span>
            </CardTitle>
            <CardDescription>Detected suspicious behaviors and activities</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* When locked, show a clean placeholder instead of real data */}
              {!isGateUnlocked("behavior_analysis") ? (
                <div className="space-y-3">
                  <div className="flex items-center space-x-3 p-3 bg-muted/30 border border-border rounded-lg">
                    <div className="w-3 h-3 bg-muted rounded-full"></div>
                    <div>
                      <span className="text-sm font-medium text-muted-foreground">Behavior Detection</span>
                      <p className="text-xs text-muted-foreground">Upgrade to Pro to detect fighting, accidents &amp; more</p>
                    </div>
                  </div>
                  <div className="p-3 bg-muted/20 rounded-lg space-y-2">
                    <div className="h-3 w-2/3 bg-muted/40 rounded animate-pulse"></div>
                    <div className="h-3 w-1/2 bg-muted/40 rounded animate-pulse"></div>
                    <div className="h-3 w-3/4 bg-muted/40 rounded animate-pulse"></div>
                  </div>
                </div>
              ) : videoResults && videoResults.behaviors_available && videoResults.behaviors_count > 0 ? (
                <div className="space-y-3">
                  <div className="flex items-center space-x-3 p-3 bg-orange-500/10 border border-orange-500/20 rounded-lg">
                    <div className="w-3 h-3 bg-orange-500 rounded-full animate-pulse"></div>
                    <div className="flex-1">
                      <span className="text-sm font-medium">Suspicious Behavior Detected</span>
                      <p className="text-xs text-muted-foreground">{videoResults.behaviors_count} behavior event(s) detected</p>
                    </div>
                  </div>

                  {/* Show behavior types */}
                  {videoResults.behaviors_summary?.by_type && Object.keys(videoResults.behaviors_summary.by_type).length > 0 && (
                    <div className="p-3 bg-muted/50 rounded-lg space-y-2">
                      <p className="text-xs font-medium mb-2">Detected Behaviors:</p>
                      <div className="space-y-2">
                        {Object.entries(videoResults.behaviors_summary.by_type).map(([behaviorType, count]) => {
                          const behaviorLabels: Record<string, string> = {
                            'fighting': 'Fighting',
                            'road_accident': 'Road Accident',
                            'wallclimb': 'Wall Climbing',
                            'accident': 'Accident',
                            'climbing': 'Climbing'
                          }
                          const label = behaviorLabels[behaviorType] || behaviorType.charAt(0).toUpperCase() + behaviorType.slice(1).replace('_', ' ')
                          const colorClass = behaviorType === 'fighting' ? 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200' :
                            behaviorType === 'road_accident' ? 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200' :
                              'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'

                          return (
                            <div key={behaviorType} className="flex items-center justify-between p-2 bg-background rounded border">
                              <div className="flex items-center space-x-2">
                                <span className={`text-xs ${colorClass} px-2 py-1 rounded font-medium`}>
                                  {label}
                                </span>
                                <span className="text-xs text-muted-foreground">
                                  {count as number} occurrence{(count as number) > 1 ? 's' : ''}
                                </span>
                              </div>
                            </div>
                          )
                        })}
                      </div>

                      {videoResults.behaviors_summary.most_common && (
                        <div className="mt-2 pt-2 border-t">
                          <p className="text-xs text-muted-foreground">
                            Most common: <span className="font-medium capitalize">{videoResults.behaviors_summary.most_common.replace('_', ' ')}</span>
                          </p>
                          {videoResults.behaviors_summary.average_confidence && (
                            <p className="text-xs text-muted-foreground">
                              Avg. confidence: <span className="font-medium">{(videoResults.behaviors_summary.average_confidence * 100).toFixed(1)}%</span>
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Show recent behavior events */}
                  {videoResults.behavior_events && videoResults.behavior_events.length > 0 && (
                    <div className="p-2 bg-muted/30 rounded-lg">
                      <p className="text-xs font-medium mb-2">Recent Events:</p>
                      <div className="space-y-1 max-h-32 overflow-y-auto">
                        {videoResults.behavior_events.slice(0, 5).map((event, idx) => {
                          const behaviorType = event.event_type.replace('behavior_', '')
                          const behaviorLabels: Record<string, string> = {
                            'fighting': 'Fighting',
                            'road_accident': 'Road Accident',
                            'wallclimb': 'Wall Climbing'
                          }
                          const label = behaviorLabels[behaviorType] || behaviorType.charAt(0).toUpperCase() + behaviorType.slice(1)
                          const startTime = (event.start_timestamp_ms / 1000).toFixed(1)
                          const endTime = (event.end_timestamp_ms / 1000).toFixed(1)

                          return (
                            <div key={idx} className="text-xs text-muted-foreground flex items-center justify-between">
                              <span>{label}</span>
                              <span className="ml-2">{startTime}s - {endTime}s ({(event.confidence_score * 100).toFixed(0)}%)</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center space-x-3 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <div>
                    <span className="text-sm font-medium">No Suspicious Behaviors</span>
                    <p className="text-xs text-muted-foreground">No behavior anomalies detected</p>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
        </FeatureGateOverlay>

        {/* Real-Time Alerts Widget — Live SSE-powered alerts */}
        <div className="shadow-lg border-3 shadow-gray-500/50 hover:shadow-gray-500/70 transition-shadow duration-300 rounded-xl">
          <LiveAlertsPanel
            alerts={liveAlerts}
            pendingAlerts={pendingAlerts}
            stats={alertStats}
            isConnected={isAlertStreamConnected}
            connectionError={alertConnectionError}
            onConnect={connectAlertStream}
            onConfirm={confirmAlert}
            onDismiss={dismissAlert}
            onTestAlert={sendTestAlert}
          />
        </div>
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
              <div className="text-sm text-muted-foreground">
                {isGateUnlocked("behavior_analysis") ? "Detections & Behaviors" : "Detections"}
              </div>
            </div>
            <div className="text-center p-4 bg-muted/50 rounded-lg border relative">
              {!isGateUnlocked("behavior_analysis") && statistics.mostCommonIncident === "None" ? (
                <>
                  <div className="text-2xl font-bold text-muted-foreground/50">—</div>
                  <div className="text-sm text-muted-foreground">Threat Level</div>
                  <div className="text-[10px] text-purple-400 mt-1">Pro: full analysis</div>
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold text-red-500">{statistics.mostCommonIncident}</div>
                  <div className="text-sm text-muted-foreground">Threat Level</div>
                </>
              )}
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
                        className={`border rounded-lg overflow-hidden ${keyframe.has_detections ? 'border-red-500 border-2 shadow-lg' : ''
                          }`}
                      >
                        <div className="relative">
                          <img
                            src={
                              (keyframe.has_detections && keyframe.annotated_url)
                                ? (keyframe.annotated_url.startsWith('http') || keyframe.annotated_url.startsWith('/api/'))
                                  ? keyframe.annotated_url
                                  : `/api/video/${currentVideoId}/keyframe/${keyframe.annotated_url.split('/').pop() || keyframe.filename}`
                                : keyframe.api_url || keyframe.minio_url || keyframe.url || keyframe.presigned_url || '/placeholder.jpg'
                            }
                            alt={`Keyframe ${idx + 1}`}
                            className="w-full h-32 object-cover"
                            onError={(e) => {
                              // Try fallback URLs
                              const img = e.target as HTMLImageElement
                              if (keyframe.presigned_url && img.src !== keyframe.presigned_url) {
                                img.src = keyframe.presigned_url
                              } else {
                                img.src = "/placeholder.jpg"
                              }
                            }}
                          />
                          {keyframe.has_detections && (
                            <div className={`absolute top-2 right-2 text-white text-xs px-2 py-1 rounded font-bold ${keyframe.has_faces
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
                                        className={`text-xs px-2 py-0.5 rounded font-medium ${isFace
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

      {/* Real-Time Alert Popup Modal — shown for each pending alert requiring confirmation */}
      {currentPopupAlert && (
        <AlertPopup
          alert={currentPopupAlert}
          onConfirm={confirmAlert}
          onDismiss={dismissAlert}
          onSkip={dismissPopup}
          pendingCount={pendingAlerts.length}
        />
      )}

      {/* Upgrade Dialog — shown when user clicks a gated action (upload, live, search) */}
      {showUpgradePrompt && DASHBOARD_GATES[upgradeGateId] && (
        <UpgradeDialog
          open={showUpgradePrompt}
          onClose={() => setShowUpgradePrompt(false)}
          gate={DASHBOARD_GATES[upgradeGateId]}
          currentPlan={planId}
        />
      )}
    </div>
  )
}
