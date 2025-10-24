'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Download, Play, Pause } from 'lucide-react'

interface Keyframe {
  filename: string
  url: string
  annotated_url?: string
  timestamp: string
  has_detections?: boolean
  detection_count?: number
  objects?: string[]
  confidence_avg?: number
}

interface VideoResults {
  video_id: string
  compressed_video_available: boolean
  compressed_video_url?: string
  keyframes_available: boolean
  keyframes_count?: number
  keyframes_url?: string
  reports_available: boolean
  reports?: string[]
}

interface KeyframesData {
  video_id: string
  keyframes: Keyframe[]
  total_keyframes: number
  keyframes_with_detections: number
  objects_detected: Record<string, number>
  filter_applied: boolean
}

interface ProcessingSummary {
  video_id: string
  filename: string
  processing_time: number
  keyframes_extracted: number
  keyframes_with_detections: number
  objects_detected: Record<string, number>
  total_objects: number
  component_times: Record<string, number>
}

export default function VideoResults({ params }: { params: { videoId: string } }) {
  const router = useRouter()
  const [results, setResults] = useState<VideoResults | null>(null)
  const [keyframes, setKeyframes] = useState<Keyframe[]>([])
  const [keyframesData, setKeyframesData] = useState<KeyframesData | null>(null)
  const [processingSummary, setProcessingSummary] = useState<ProcessingSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showOnlyDetections, setShowOnlyDetections] = useState(true)

  useEffect(() => {
    fetchVideoResults()
  }, [params.videoId])

  const fetchVideoResults = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch video results
      const resultsResponse = await fetch(`/api/video/results/${params.videoId}`)
      if (!resultsResponse.ok) {
        throw new Error('Failed to fetch video results')
      }
      const resultsData = await resultsResponse.json()
      setResults(resultsData)

      // Fetch keyframes if available (filter to show only detections by default)
      if (resultsData.keyframes_available) {
        const keyframesResponse = await fetch(`/api/video/keyframes/${params.videoId}?filter_detections=${showOnlyDetections}`)
        if (keyframesResponse.ok) {
          const keyframesData: KeyframesData = await keyframesResponse.json()
          setKeyframes(keyframesData.keyframes)
          setKeyframesData(keyframesData)
        }
      }

      // Fetch processing summary
      const summaryResponse = await fetch(`/api/video/processing-summary/${params.videoId}`)
      if (summaryResponse.ok) {
        const summaryData: ProcessingSummary = await summaryResponse.json()
        setProcessingSummary(summaryData)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  const toggleDetectionFilter = async () => {
    const newFilter = !showOnlyDetections
    setShowOnlyDetections(newFilter)
    
    // Refetch keyframes with new filter
    if (results?.keyframes_available) {
      const keyframesResponse = await fetch(`/api/video/keyframes/${params.videoId}?filter_detections=${newFilter}`)
      if (keyframesResponse.ok) {
        const keyframesData: KeyframesData = await keyframesResponse.json()
        setKeyframes(keyframesData.keyframes)
        setKeyframesData(keyframesData)
      }
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 rounded w-1/4"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-40 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
        <div className="max-w-7xl mx-auto">
          <Card className="border-red-200">
            <CardContent className="p-6">
              <div className="text-center">
                <h2 className="text-xl font-semibold text-red-600 mb-2">Error Loading Results</h2>
                <p className="text-gray-600 mb-4">{error}</p>
                <Button onClick={() => router.back()} variant="outline">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Go Back
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button 
              onClick={() => router.back()} 
              variant="outline" 
              size="sm"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                DetectifAI Results
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Video ID: {params.videoId}
              </p>
            </div>
          </div>
        </div>

        {/* Processed Video */}
        {results?.compressed_video_available && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Play className="w-5 h-5" />
                <span>Processed Video with Fire Detection</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="aspect-video bg-black rounded-lg overflow-hidden">
                <video 
                  controls 
                  className="w-full h-full"
                  preload="metadata"
                >
                  <source 
                    src={`/api/video/compressed/${params.videoId}`} 
                    type="video/mp4" 
                  />
                  Your browser does not support the video tag.
                </video>
              </div>
              <div className="mt-4 flex items-center justify-between">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Fire detection results with corrected labels (fire/smoke)
                </p>
                <Button variant="outline" size="sm">
                  <Download className="w-4 h-4 mr-2" />
                  Download Video
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Processing Summary */}
        {processingSummary && (
          <Card>
            <CardHeader>
              <CardTitle>Processing Summary</CardTitle>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Video processing statistics and object detection results
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">{processingSummary.keyframes_extracted}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Keyframes Extracted</div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">{processingSummary.keyframes_with_detections}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Frames with Objects</div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-2xl font-bold text-red-600">{processingSummary.total_objects}</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Total Objects Detected</div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">{processingSummary.processing_time.toFixed(1)}s</div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">Processing Time</div>
                </div>
              </div>
              
              {/* Objects Detected Breakdown */}
              {Object.keys(processingSummary.objects_detected).length > 0 && (
                <div className="mt-4">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Objects Detected:</h4>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(processingSummary.objects_detected).map(([object, count]) => (
                      <span
                        key={object}
                        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                      >
                        {object}: {count}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Keyframes with Detection Results */}
        {results?.keyframes_available && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>
                    Detection Keyframes ({keyframes.length} frames)
                  </CardTitle>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {showOnlyDetections 
                      ? "Frames that contain detected objects" 
                      : "All extracted keyframes"}
                  </p>
                </div>
                <Button
                  onClick={toggleDetectionFilter}
                  variant="outline"
                  size="sm"
                >
                  {showOnlyDetections ? "Show All Frames" : "Show Only Detections"}
                </Button>
              </div>
              
              {keyframesData && (
                <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                  {keyframesData.keyframes_with_detections} frames with detections out of {keyframesData.total_keyframes} total frames
                </div>
              )}
            </CardHeader>
            <CardContent>
              {keyframes.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {keyframes.map((keyframe, index) => (
                    <div 
                      key={index}
                      className={`bg-white dark:bg-gray-800 rounded-lg border shadow-sm overflow-hidden ${
                        keyframe.has_detections ? 'border-red-200 dark:border-red-800' : ''
                      }`}
                    >
                      <div className="aspect-video bg-gray-100 dark:bg-gray-700 relative">
                        <img
                          src={`http://localhost:5000${showOnlyDetections && keyframe.annotated_url ? keyframe.annotated_url : keyframe.url}`}
                          alt={`Keyframe at ${keyframe.timestamp}s`}
                          className="w-full h-full object-cover"
                          loading="lazy"
                        />
                        {keyframe.has_detections && (
                          <div className="absolute top-2 right-2 bg-red-600 text-white text-xs px-2 py-1 rounded">
                            {keyframe.detection_count || 0} objects
                          </div>
                        )}
                      </div>
                      <div className="p-3">
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          Frame {index + 1}
                        </p>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          Time: {parseFloat(keyframe.timestamp).toFixed(2)}s
                        </p>
                        {keyframe.objects && keyframe.objects.length > 0 && (
                          <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                            {keyframe.objects.join(', ')}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  {showOnlyDetections ? "No frames with detections found" : "No keyframes available"}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Processing Summary */}
        <Card>
          <CardHeader>
            <CardTitle>Processing Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {results?.compressed_video_available ? '✓' : '✗'}
                </div>
                <p className="text-sm text-green-700 dark:text-green-300">
                  Video Processing
                </p>
              </div>
              <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {results?.keyframes_count || 0}
                </div>
                <p className="text-sm text-blue-700 dark:text-blue-300">
                  Keyframes Extracted
                </p>
              </div>
              <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {results?.reports_available ? '✓' : '✗'}
                </div>
                <p className="text-sm text-purple-700 dark:text-purple-300">
                  Analysis Reports
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* No Results Message */}
        {!results?.compressed_video_available && !results?.keyframes_available && (
          <Card className="border-yellow-200">
            <CardContent className="p-6">
              <div className="text-center">
                <h3 className="text-lg font-medium text-yellow-800 mb-2">
                  No Processed Results Available
                </h3>
                <p className="text-yellow-700 mb-4">
                  The video processing may still be in progress or may have encountered an issue.
                </p>
                <Button onClick={fetchVideoResults} variant="outline">
                  Refresh Results
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}