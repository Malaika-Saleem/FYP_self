import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(
  request: NextRequest,
  { params }: { params: { eventId: string } }
) {
  try {
    const eventId = params.eventId
    const { searchParams } = new URL(request.url)
    const faceId = searchParams.get('face_id')
    const personName = searchParams.get('person_name')
    
    if (!faceId) {
      return NextResponse.json(
        { error: 'face_id parameter is required' },
        { status: 400 }
      )
    }
    
    // Build query string
    const queryParams = new URLSearchParams({ face_id: faceId })
    if (personName) {
      queryParams.append('person_name', personName)
    }
    
    // Forward request to Flask backend for annotated event clip
    const response = await fetch(
      `${FLASK_API_URL}/api/event/clip/${eventId}/annotated?${queryParams.toString()}`,
      {
        method: 'GET',
        headers: {
          'Accept': 'video/mp4, video/*, */*',
        },
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Failed to fetch annotated event clip' }))
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
    console.error('Error fetching annotated event clip:', error)
    return NextResponse.json(
      { error: 'Failed to fetch annotated event clip' },
      { status: 500 }
    )
  }
}

