import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId
    const range = request.headers.get('range')
    console.log('🎬 Next.js API: Fetching compressed video for:', videoId, 'Range:', range)

    const fetchHeaders: Record<string, string> = {
      'Accept': 'video/mp4, video/*, */*',
    }

    // Forward Range header if present
    if (range) {
      fetchHeaders['Range'] = range
    }

    // Forward request to Flask backend for compressed video (using working V3 endpoint)
    const response = await fetch(`${FLASK_API_URL}/api/v3/video/compressed/${videoId}`, {
      method: 'GET',
      headers: fetchHeaders,
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

    const responseHeaders = new Headers()
    const contentType = response.headers.get('Content-Type') || 'video/mp4'
    responseHeaders.set('Content-Type', contentType)
    responseHeaders.set('Cache-Control', 'no-cache')

    // Forward critical video headers
    const headersToForward = ['Content-Length', 'Content-Range', 'Accept-Ranges', 'Content-Disposition']
    headersToForward.forEach(header => {
      const value = response.headers.get(header)
      if (value) {
        responseHeaders.set(header, value)
      }
    })

    console.log('✅ Streaming video with Content-Type:', contentType, 'Status:', response.status)

    return new NextResponse(videoStream, {
      status: response.status,
      headers: responseHeaders,
    })
  } catch (error) {
    console.error('❌ Error fetching compressed video:', error)
    return NextResponse.json(
      { error: `Failed to fetch compressed video: ${error instanceof Error ? error.message : 'Unknown error'}` },
      { status: 500 }
    )
  }
}