import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { query, top_k = 10, min_score = 0.0 } = body

    if (!query || !query.trim()) {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      )
    }

    // Get auth token from request headers (passed from frontend)
    const authHeader = request.headers.get('authorization')
    
    // Call Flask API
    const response = await fetch(`${FLASK_API_URL}/api/search/captions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader && { 'Authorization': authHeader })
      },
      body: JSON.stringify({
        query: query.trim(),
        top_k,
        min_score
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Search failed' }))
      return NextResponse.json(
        { error: errorData.error || 'Search failed' },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Caption search error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

