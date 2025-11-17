import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(
  request: NextRequest,
  { params }: { params: { eventId: string } }
) {
  try {
    const eventId = params.eventId
    
    // Forward request to Flask backend for event clip download
    const response = await fetch(`${FLASK_API_URL}/api/event/clip/${eventId}/download`, {
      method: 'GET',
      headers: {
        'Accept': 'video/mp4, video/*, */*',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Failed to download event clip' }))
      return NextResponse.json(errorData, { status: response.status })
    }

    // Stream the video file for download
    const videoStream = response.body
    if (!videoStream) {
      return NextResponse.json(
        { error: 'No video stream received' },
        { status: 500 }
      )
    }

    const headers = new Headers(response.headers)
    const contentType = headers.get('Content-Type') || 'video/mp4'
    const contentDisposition = headers.get('Content-Disposition') || `attachment; filename="event_${eventId}_clip.mp4"`
    
    return new NextResponse(videoStream, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': contentDisposition,
      },
    })
  } catch (error) {
    console.error('Error downloading event clip:', error)
    return NextResponse.json(
      { error: 'Failed to download event clip' },
      { status: 500 }
    )
  }
}

