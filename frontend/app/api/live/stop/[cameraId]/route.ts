import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function POST(
  request: NextRequest,
  { params }: { params: { cameraId: string } }
) {
  try {
    const { cameraId } = params

    const response = await fetch(`${FLASK_API_URL}/api/live/stop/${cameraId}`, {
      method: 'POST'
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Error stopping live stream:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to stop live stream' },
      { status: 500 }
    )
  }
}

