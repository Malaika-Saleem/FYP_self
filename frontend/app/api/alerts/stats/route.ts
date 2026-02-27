import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET() {
  try {
    const response = await fetch(`${FLASK_API_URL}/api/alerts/stats`)
    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Error fetching alert stats:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to fetch alert stats' },
      { status: 500 }
    )
  }
}
