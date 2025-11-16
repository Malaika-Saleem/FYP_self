import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId
    const { searchParams } = new URL(request.url)
    const filterDetections = searchParams.get('filter_detections') || 'false'
    
    // Forward request to Flask backend for keyframes list - try v2 endpoint first, fallback to legacy
    let response = await fetch(`http://localhost:5000/api/v2/video/keyframes/${videoId}?filter_detections=${filterDetections}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // If v2 endpoint fails, try legacy endpoint
    if (!response.ok) {
      console.log('v2 keyframes endpoint failed, trying legacy endpoint')
      response = await fetch(`http://localhost:5000/api/video/keyframes/${videoId}`, {
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
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching keyframes:', error)
    return NextResponse.json(
      { error: 'Failed to fetch keyframes' },
      { status: 500 }
    )
  }
}