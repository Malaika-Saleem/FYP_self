import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId
    
    // Forward request to Flask backend v2 endpoint
    const response = await fetch(`http://localhost:5000/api/v2/video/results/${videoId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Failed to fetch results' }))
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()

    // Ensure required fields are present
    if (!data.hasOwnProperty('compressed_video_available')) {
      data.compressed_video_available = false
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching video results:', error)
    return NextResponse.json(
      { error: 'Failed to fetch video results', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}
