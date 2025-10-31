import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId
    
    // Forward request to Flask backend for compressed video
    const response = await fetch(`http://localhost:5000/api/video/compressed/${videoId}`, {
      method: 'GET',
    })

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(errorData, { status: response.status })
    }

    // Stream the video file
    const videoStream = response.body
    const headers = new Headers(response.headers)
    
    return new NextResponse(videoStream, {
      status: 200,
      headers: {
        'Content-Type': 'video/mp4',
        'Content-Disposition': headers.get('Content-Disposition') || 'inline',
      },
    })
  } catch (error) {
    console.error('Error fetching compressed video:', error)
    return NextResponse.json(
      { error: 'Failed to fetch compressed video' },
      { status: 500 }
    )
  }
}