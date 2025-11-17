import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(
  request: NextRequest,
  { params }: { params: { eventId: string } }
) {
  try {
    const eventId = params.eventId
    
    // Forward request to Flask backend for event clip
    const response = await fetch(`${FLASK_API_URL}/api/event/clip/${eventId}`, {
      method: 'GET',
      headers: {
        'Accept': 'video/mp4, video/*, */*',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Failed to fetch event clip' }))
      return NextResponse.json(errorData, { status: response.status })
    }

    // Stream the video file
    const videoStream = response.body
    if (!videoStream) {
      return NextResponse.json(
        { error: 'No video stream received' },
        { status: 500 }
      )
    }

    const headers = new Headers(response.headers)
    const contentType = headers.get('Content-Type') || 'video/mp4'
    
    return new NextResponse(videoStream, {
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=3600',
      },
    })
  } catch (error) {
    console.error('Error fetching event clip:', error)
    return NextResponse.json(
      { error: 'Failed to fetch event clip' },
      { status: 500 }
    )
  }
}

