import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit') || '50'
    const camera_id = searchParams.get('camera_id') || ''
    const severity = searchParams.get('severity') || ''
    const status = searchParams.get('status') || ''

    const queryParams = new URLSearchParams()
    queryParams.set('limit', limit)
    if (camera_id) queryParams.set('camera_id', camera_id)
    if (severity) queryParams.set('severity', severity)
    if (status) queryParams.set('status', status)

    const response = await fetch(
      `${FLASK_API_URL}/api/alerts/history?${queryParams.toString()}`
    )
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Error fetching alert history:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch alert history' },
      { status: 500 }
    )
  }
}
