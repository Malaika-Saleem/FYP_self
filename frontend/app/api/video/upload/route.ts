import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth-config'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

export async function POST(request: NextRequest) {
  try {
    // Get session server-side to ensure user_id is always available
    const session = await getServerSession(authOptions)
    
    console.log('🔍 [Video Upload] Session:', session ? 'Found' : 'Not found')
    
    if (!session || !session.user) {
      console.error('❌ [Video Upload] No session or user found')
      return NextResponse.json(
        { error: 'Authentication required', message: 'Please sign in to upload videos' },
        { status: 401 }
      )
    }

    const userId = (session.user as any).id
    console.log('🔍 [Video Upload] User ID from session:', userId)
    console.log('🔍 [Video Upload] Full session user:', JSON.stringify(session.user, null, 2))
    
    if (!userId) {
      console.error('❌ [Video Upload] User ID not found in session')
      return NextResponse.json(
        { error: 'User ID not found in session', message: 'Please sign in again' },
        { status: 401 }
      )
    }

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
    flaskFormData.append('user_id', userId) // Always append user_id from session

    console.log('📤 [Video Upload] Sending to Flask:', {
      userId,
      configType,
      videoName: video.name,
      videoSize: video.size
    })

    const response = await fetch(`${FLASK_API_URL}/api/v2/video/upload`, {
      method: 'POST',
      body: flaskFormData,
    })

    // Check if response is JSON
    const contentType = response.headers.get('content-type')
    let data
    if (contentType && contentType.includes('application/json')) {
      data = await response.json()
    } else {
      // If not JSON, read as text to see the error
      const text = await response.text()
      console.error('❌ [Video Upload] Flask returned non-JSON response:', text.substring(0, 200))
      return NextResponse.json(
        { 
          error: 'Server error', 
          message: response.status === 500 ? 'Internal server error occurred' : `Unexpected response (${response.status})`,
          details: text.substring(0, 500)
        },
        { status: response.status || 500 }
      )
    }
    
    console.log('📥 [Video Upload] Flask response:', {
      status: response.status,
      data
    })
    
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('❌ [Video Upload] Error:', error)
    return NextResponse.json(
      { error: 'Failed to upload video', message: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    )
  }
}