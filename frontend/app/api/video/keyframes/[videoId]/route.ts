import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId
    
    // Forward request to Flask backend for keyframes list
    const response = await fetch(`http://localhost:5000/api/video/${videoId}/keyframes`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

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