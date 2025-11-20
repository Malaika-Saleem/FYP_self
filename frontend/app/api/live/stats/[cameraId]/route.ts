import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(
  request: NextRequest,
  { params }: { params: { cameraId: string } }
) {
  try {
    const { cameraId } = params

    const response = await fetch(`${FLASK_API_URL}/api/live/stats/${cameraId}`)

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Error getting live stats:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to get live stats' },
      { status: 500 }
    )
  }
}

