import { NextRequest, NextResponse } from 'next/server'
import { findUserByGoogleId, createUser, generateUserId, createSession, generateSessionId, generateToken, updateUserLastLogin } from '@/lib/auth'

export async function POST(request: NextRequest) {
  try {
    const { id, email, name, image } = await request.json()

    if (!id || !email) {
      return NextResponse.json(
        { error: 'Google ID and email are required' },
        { status: 400 }
      )
    }

    // Check if user exists by Google ID
    let user = await findUserByGoogleId(id)

    if (!user) {
      // Create new user
      const userId = generateUserId()
      user = await createUser({
        user_id: userId,
        google_id: id,
        email,
        name,
        image,
        role: 'user',
        is_active: true
      })

      if (!user) {
        return NextResponse.json(
          { error: 'Failed to create user' },
          { status: 500 }
        )
      }
    }

    // Update last login
    await updateUserLastLogin(user.user_id)

    // Generate JWT token
    const token = generateToken({
      userId: user.user_id,
      email: user.email,
      role: user.role
    })

    // Create session
    const sessionId = generateSessionId()
    const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000) // 24 hours

    await createSession({
      session_id: sessionId,
      user_id: user.user_id,
      session_token: token,
      expires_at: expiresAt,
      created_at: new Date()
    })

    // Create response with cookie
    const response = NextResponse.json({
      success: true,
      user: {
        id: user.user_id,
        email: user.email,
        name: user.name,
        role: user.role
      }
    })

    // Set HTTP-only cookie
    response.cookies.set('detectifai-token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 24 * 60 * 60 // 24 hours
    })

    return response

  } catch (error) {
    console.error('Google signin error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
