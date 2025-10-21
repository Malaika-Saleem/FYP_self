import { NextRequest, NextResponse } from 'next/server'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const video = formData.get('video') as File
    const configType = formData.get('configType') as string || 'robbery'

    if (!video) {
      return NextResponse.json(
        { error: 'No video file provided' },
        { status: 400 }
      )
    }

    const flaskFormData = new FormData()
    flaskFormData.append('video', video)
    flaskFormData.append('config_type', configType)

    const response = await fetch(`${FLASK_API_URL}/api/upload`, {
      method: 'POST',
      body: flaskFormData,
    })

    const data = await response.json()
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to upload video' },
      { status: 500 }
    )
  }
}