import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function GET(
  request: NextRequest,
  { params }: { params: { videoId: string; filename: string } }
) {
  try {
    const { videoId, filename } = params

    // Forward request to Flask backend
    const response = await fetch(
      `${FLASK_API_URL}/api/video/reports/download/${videoId}/${filename}`,
      {
        method: 'GET',
      }
    )

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Report file not found' },
        { status: response.status }
      )
    }

    // Get the file content
    const blob = await response.blob()
    const contentType = response.headers.get('content-type') || 'application/octet-stream'

    // Return the file
    return new NextResponse(blob, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    })
  } catch (error) {
    console.error('❌ [Report Download] Error:', error)
    return NextResponse.json(
      { error: 'Failed to download report' },
      { status: 500 }
    )
  }
}
