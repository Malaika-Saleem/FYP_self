import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function POST(request: NextRequest) {
  try {
    // Get the form data from the request
    const formData = await request.formData()
    
    // Forward the form data to Flask backend
    const response = await fetch(`${FLASK_API_URL}/api/search/person-by-image`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Failed to search for person' }))
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error in person image search:', error)
    return NextResponse.json(
      { 
        success: false,
        error: 'Failed to search for person. Please try again.' 
      },
      { status: 500 }
    )
  }
}

