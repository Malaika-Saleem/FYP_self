import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId
    console.log('🎬 Next.js API: Fetching compressed video for:', videoId)
    
    // Forward request to Flask backend for compressed video (using working V3 endpoint)
    const response = await fetch(`http://localhost:5000/api/v3/video/compressed/${videoId}`, {
      method: 'GET',
      headers: {
        'Accept': 'video/mp4, video/*, */*',
      },
    })

    console.log('🎬 Flask response status:', response.status, response.statusText)
    console.log('🎬 Flask response headers:', Object.fromEntries(response.headers.entries()))

    if (!response.ok) {
      // Try to get error message, but don't fail if it's not JSON
      let errorMessage = 'Failed to fetch compressed video'
      try {
        const contentType = response.headers.get('content-type')
        if (contentType && contentType.includes('application/json')) {
          const errorData = await response.json()
          errorMessage = errorData.error || errorMessage
        } else {
          const errorText = await response.text()
          errorMessage = errorText || errorMessage
        }
      } catch (e) {
        console.error('Error parsing error response:', e)
      }
      console.error('❌ Failed to fetch compressed video:', response.status, errorMessage)
      return NextResponse.json(
        { error: errorMessage, status: response.status },
        { status: response.status }
      )
    }

    // Stream the video file
    const videoStream = response.body
    if (!videoStream) {
      console.error('❌ No video stream in response')
      return NextResponse.json(
        { error: 'No video stream received' },
        { status: 500 }
      )
    }

    const headers = new Headers(response.headers)
    const contentType = headers.get('Content-Type') || 'video/mp4'
    
    console.log('✅ Streaming video with Content-Type:', contentType)
    
    return new NextResponse(videoStream, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': headers.get('Content-Disposition') || 'inline',
        'Accept-Ranges': headers.get('Accept-Ranges') || 'bytes',
        'Cache-Control': 'no-cache',
      },
    })
  } catch (error) {
    console.error('❌ Error fetching compressed video:', error)
    return NextResponse.json(
      { error: `Failed to fetch compressed video: ${error instanceof Error ? error.message : 'Unknown error'}` },
      { status: 500 }
    )
  }
}