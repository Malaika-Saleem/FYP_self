import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    // Try v2 endpoint first, fallback to legacy
    let response = await fetch(`${FLASK_API_URL}/api/v2/video/status/${params.videoId}`)

    // If v2 endpoint fails, try legacy endpoint
    if (!response.ok) {
      console.log('v2 status endpoint failed, trying legacy endpoint')
      response = await fetch(`${FLASK_API_URL}/api/status/${params.videoId}`)
    }
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to get status' },
      { status: 500 }
    )
  }
}