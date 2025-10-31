import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId
    
    // Forward request to Flask backend - try v2 endpoint first, fallback to legacy
    let response = await fetch(`http://localhost:5000/api/v2/video/results/${videoId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // If v2 endpoint fails, try legacy endpoint
    if (!response.ok) {
      console.log('v2 results endpoint failed, trying legacy endpoint')
      response = await fetch(`http://localhost:5000/api/video/results/${videoId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })
    }

    if (!response.ok) {
      const errorData = await response.json()
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()

    // Ensure compressed_video_available field is always present
    if (!data.hasOwnProperty('compressed_video_available')) {
      data.compressed_video_available = false
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching video results:', error)
    return NextResponse.json(
      { error: 'Failed to fetch video results' },
      { status: 500 }
    )
  }
}