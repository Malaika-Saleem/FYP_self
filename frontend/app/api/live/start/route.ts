import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { camera_id = 'webcam_01', camera_index = 0 } = body

    const response = await fetch(`${FLASK_API_URL}/api/live/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ camera_id, camera_index })
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Error starting live stream:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to start live stream' },
      { status: 500 }
    )
  }
}

