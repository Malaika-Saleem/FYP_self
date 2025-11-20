import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(
  request: NextRequest,
  { params }: { params: { bucket: string; path: string[] } }
) {
  try {
    const { bucket, path } = params
    const objectPath = path.join('/')

    if (!bucket || !objectPath) {
      return NextResponse.json(
        { error: 'Bucket and object path are required' },
        { status: 400 }
      )
    }

    // Proxy request to Flask backend
    const response = await fetch(`${FLASK_API_URL}/api/minio/image/${bucket}/${objectPath}`, {
      method: 'GET',
      headers: {
        'Accept': 'image/*',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Image not found' }))
      return NextResponse.json(errorData, { status: response.status })
    }

    // Get image data
    const imageBuffer = await response.arrayBuffer()
    const contentType = response.headers.get('content-type') || 'image/jpeg'

    // Return image with proper headers
    return new NextResponse(imageBuffer, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        'Cache-Control': 'public, max-age=3600',
        'Access-Control-Allow-Origin': '*',
      },
    })
  } catch (error) {
    console.error('Error serving MinIO image:', error)
    return NextResponse.json(
      { error: 'Failed to serve image' },
      { status: 500 }
    )
  }
}

