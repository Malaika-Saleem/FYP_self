import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId
    const { searchParams } = new URL(request.url)
    const filterDetections = searchParams.get('filter_detections') || 'true'
    const limit = searchParams.get('limit') || '50'
    
    // Forward request to Flask backend
    const response = await fetch(
      `http://localhost:5000/api/v2/video/keyframes/${videoId}?filter_detections=${filterDetections}&limit=${limit}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Failed to fetch keyframes' }))
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching video keyframes:', error)
    return NextResponse.json(
      { error: 'Failed to fetch video keyframes', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}
