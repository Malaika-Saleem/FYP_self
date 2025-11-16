import { NextRequest, NextResponse } from 'next/server'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string } }
) {
  try {
    const videoId = params.videoId
    
    // Forward request to Flask backend for detected faces
    const response = await fetch(`http://localhost:5000/api/v2/video/faces/${videoId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      // Return empty array if faces not found instead of error
      if (response.status === 404) {
        return NextResponse.json([])
      }
      const errorData = await response.json()
      return NextResponse.json(errorData, { status: response.status })
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching detected faces:', error)
    // Return empty array on error to prevent breaking the UI
    return NextResponse.json([])
  }
}