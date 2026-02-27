import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth-config'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function POST(request: NextRequest) {
  try {
    // Get session server-side to ensure user_id is always available
    const session = await getServerSession(authOptions)

    if (!session || !session.user) {
      return NextResponse.json(
        { error: 'Authentication required', message: 'Please sign in to search' },
        { status: 401 }
      )
    }

    const userId = (session.user as any).id
    if (!userId) {
      return NextResponse.json(
        { error: 'User ID not found in session', message: 'Please sign in again' },
        { status: 401 }
      )
    }

    const body = await request.json()
    const { query, top_k = 10, min_score = 0.0 } = body

    if (!query || !query.trim()) {
      return NextResponse.json(
        { error: 'Query is required' },
        { status: 400 }
      )
    }

    // Call Flask API with user_id for subscription/feature gating
    const response = await fetch(`${FLASK_API_URL}/api/search/captions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query.trim(),
        top_k,
        min_score,
        user_id: userId
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

