import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json().catch(() => ({}))

    const response = await fetch(`${FLASK_API_URL}/api/alerts/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('Error creating test alert:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to create test alert' },
      { status: 500 }
    )
  }
}
