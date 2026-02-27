import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth-config'
import http from 'http'
import https from 'https'

const FLASK_API_URL = process.env.FLASK_API_URL || 'http://localhost:5000'

// Configure route for long-running report generation
// Report generation can take 10-20+ minutes for complex videos (LLM loading + processing + MinIO upload)
export const maxDuration = 2700 // 45 minutes (increased for complex videos with many events)
export const dynamic = 'force-dynamic'

// Custom fetch with extended timeout for long-running requests
async function fetchWithLongTimeout(url: string, options: {
  method: string
  headers: Record<string, string>
  body: string
  timeoutMs: number
}): Promise<{ status: number; headers: Headers; json: () => Promise<any>; text: () => Promise<string> }> {
  return new Promise((resolve, reject) => {
    const parsedUrl = new URL(url)
    const isHttps = parsedUrl.protocol === 'https:'
    const httpModule = isHttps ? https : http

    const requestOptions = {
      hostname: parsedUrl.hostname,
      port: parsedUrl.port || (isHttps ? 443 : 80),
      path: parsedUrl.pathname + parsedUrl.search,
      method: options.method,
      headers: options.headers,
      timeout: options.timeoutMs, // Socket timeout
    }

    const req = httpModule.request(requestOptions, (res) => {
      let data = ''
      res.on('data', (chunk) => {
        data += chunk
      })
      res.on('end', () => {
        const headers = new Headers()
        Object.entries(res.headers).forEach(([key, value]) => {
          if (value) headers.set(key, Array.isArray(value) ? value.join(', ') : value)
        })
        resolve({
          status: res.statusCode || 500,
          headers,
          json: async () => JSON.parse(data),
          text: async () => data,
        })
      })
    })

    req.on('error', (err) => {
      reject(err)
    })

    req.on('timeout', () => {
      req.destroy()
      reject(new Error('Request timeout'))
    })

    // Set socket timeout
    req.setTimeout(options.timeoutMs)

    req.write(options.body)
    req.end()
  })
}

export async function POST(request: NextRequest) {
  try {
    // Get session server-side to ensure user_id is always available
    const session = await getServerSession(authOptions)

    if (!session || !session.user) {
      return NextResponse.json(
        { error: 'Authentication required', message: 'Please sign in to generate reports' },
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
    const videoId = body.video_id

    if (!videoId) {
      return NextResponse.json(
        { error: 'video_id is required' },
        { status: 400 }
      )
    }

    console.log('🔄 [Report Generation] Starting for video:', videoId)

    let response
    try {
      // Use custom fetch with 45-minute timeout to bypass undici's headers timeout
      response = await fetchWithLongTimeout(`${FLASK_API_URL}/api/video/reports/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          video_id: videoId,
          user_id: userId
        }),
        timeoutMs: 45 * 60 * 1000, // 45 minutes
      })
      console.log('✅ [Report Generation] Response received:', response.status)
    } catch (fetchError: any) {
      console.error('❌ [Report Generation] Fetch error:', fetchError.message)
      if (fetchError.message === 'Request timeout') {
        return NextResponse.json(
          {
            success: false,
            error: 'Request timeout',
            message: 'Report generation is taking too long. Please try again or check backend logs.'
          },
          { status: 504 }
        )
      }
      throw fetchError
    }

    if (!response) {
      return NextResponse.json(
        { success: false, error: 'No response', message: 'Backend did not respond.' },
        { status: 502 }
      )
    }

    // Check if response is JSON
    const contentType = response.headers.get('content-type')
    let data: { success?: boolean; html_url?: string; pdf_url?: string; error?: string;[k: string]: unknown }
    try {
      if (contentType && contentType.includes('application/json')) {
        data = await response.json()
      } else {
        const text = await response.text()
        console.error('❌ [Report Generation] Flask returned non-JSON response:', text.substring(0, 200))
        return NextResponse.json(
          {
            success: false,
            error: 'Server error',
            message: response.status === 500 ? 'Internal server error occurred' : `Unexpected response (${response.status})`,
            details: text.substring(0, 500)
          },
          { status: response.status || 500 }
        )
      }
    } catch (parseError) {
      console.error('❌ [Report Generation] JSON parse error:', parseError)
      return NextResponse.json(
        { success: false, error: 'Invalid response', message: 'Backend returned invalid JSON.' },
        { status: 502 }
      )
    }

    // Backend now returns presigned URLs directly from MinIO
    // No transformation needed - URLs are ready to use
    console.log('✅ [Report Generation] Success:', data.success)
    return NextResponse.json(data, { status: response.status })
  } catch (error) {
    console.error('❌ [Report Generation] Error:', error)
    return NextResponse.json(
      {
        success: false,
        error: 'Failed to generate report',
        message: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}

