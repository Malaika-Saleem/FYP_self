import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const camera_id = searchParams.get('camera_id') || ''

    const url = camera_id
      ? `${FLASK_API_URL}/api/alerts/active?camera_id=${camera_id}`
      : `${FLASK_API_URL}/api/alerts/active`

    const response = await fetch(url)
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Error fetching active alerts:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch active alerts' },
      { status: 500 }
    )
  }
}
