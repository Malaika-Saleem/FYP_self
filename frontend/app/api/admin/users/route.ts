import { NextRequest, NextResponse } from "next/server"
import { getServerSession } from "next-auth"
import { authOptions } from "@/lib/auth-config"
import { getDb } from "@/lib/auth"
import bcrypt from "bcryptjs"
import { v4 as uuidv4 } from "uuid"

// Helper to check admin role
async function checkAdmin(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session || (session.user as any)?.role !== "admin") {
      return null
    }
    return session
  } catch (error) {
    console.error("Error checking admin:", error)
    return null
  }
}

// Handle CORS preflight
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  })
}

// GET /api/admin/users - Get all users with pagination and search
export async function GET(request: NextRequest) {
  try {
    const admin = await checkAdmin(request)
    if (!admin) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const page = parseInt(searchParams.get("page") || "1")
    const limit = parseInt(searchParams.get("limit") || "50")
    const search = searchParams.get("search") || ""
    const role = searchParams.get("role") || ""
    const status = searchParams.get("status") || ""

    const db = await getDb()
    const users = db.collection("users")

    // Build search query
    const query: any = {}
    
    if (search) {
      query.$or = [
        { username: { $regex: search, $options: "i" } },
        { email: { $regex: search, $options: "i" } },
        { name: { $regex: search, $options: "i" } },
        { organization: { $regex: search, $options: "i" } }
      ]
    }

    if (role) {
      query.role = role
    }

    if (status === "active") {
      query.is_active = true
    } else if (status === "inactive") {
      query.is_active = false
    }

    // Get total count
    const total = await users.countDocuments(query)

    // Get paginated results
    const skip = (page - 1) * limit
    const userDocs = await users
      .find(query)
      .sort({ created_at: -1 })
      .skip(skip)
      .limit(limit)
      .toArray()

    // Remove sensitive data
    const cleanUsers = userDocs.map(({ _id, password_hash, ...user }) => user)

    const pages = Math.ceil(total / limit)

    return NextResponse.json({
      users: cleanUsers,
      total,
      page,
      limit,
      pages,
    })
  } catch (error) {
    console.error("Error fetching users:", error)
    return NextResponse.json(
      { error: "Failed to fetch users" },
      { status: 500 }
    )
  }
}

// POST /api/admin/users - Create a new user
export async function POST(request: NextRequest) {
  try {
    const admin = await checkAdmin(request)
    if (!admin) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
    }

    const body = await request.json()
    const { email, password, username, name, role = "user" } = body

    if (!email || !password) {
      return NextResponse.json(
        { error: "Email and password are required" },
        { status: 400 }
      )
    }

    const db = await getDb()
    const users = db.collection("users")

    // Check if user already exists
    const existingUser = await users.findOne({ email })
    if (existingUser) {
      return NextResponse.json(
        { error: "User with this email already exists" },
        { status: 400 }
      )
    }

    // Check if username is taken (if provided)
    if (username) {
      const existingUsername = await users.findOne({ username })
      if (existingUsername) {
        return NextResponse.json(
          { error: "Username is already taken" },
          { status: 400 }
        )
      }
    }

    // Hash password
    const password_hash = await bcrypt.hash(password, 12)

    // Create new user
    const newUser = {
      user_id: uuidv4(),
      email,
      password_hash,
      username: username || null,
      name: name || null,
      role: role as "admin" | "user",
      is_active: true,
      created_at: new Date(),
      updated_at: new Date(),
      profile_data: {},
    }

    const result = await users.insertOne(newUser)

    // Return user without sensitive data
    const { password_hash: _, ...userResponse } = newUser

    return NextResponse.json({
      message: "User created successfully",
      user: userResponse,
    })
  } catch (error) {
    console.error("Error creating user:", error)
    return NextResponse.json(
      { error: "Failed to create user" },
      { status: 500 }
    )
  }
}