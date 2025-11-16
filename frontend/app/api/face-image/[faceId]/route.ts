import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(
  request: NextRequest,
  { params }: { params: { faceId: string } }
) {
  try {
    const faceId = params.faceId
    
    // Forward request to Flask backend
    const response = await fetch(`${FLASK_API_URL}/api/face-image/${faceId}`, {
      method: 'GET',
    })

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Face image not found' },
        { status: 404 }
      )
    }

    // Get the image blob and return it
    const blob = await response.blob()
    return new NextResponse(blob, {
      headers: {
        'Content-Type': 'image/jpeg',
      },
    })
  } catch (error) {
    console.error('Error fetching face image:', error)
    return NextResponse.json(
      { error: 'Failed to fetch face image' },
      { status: 500 }
    )
  }
}

