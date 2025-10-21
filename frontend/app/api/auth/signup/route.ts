import { NextResponse } from "next/server"
import { MongoClient } from "mongodb"
import bcrypt from "bcryptjs"

const client = new MongoClient(process.env.MONGO_URI!)
const db = client.db()

export async function POST(req: Request) {
  const { email, password, name, organization } = await req.json()

  if (!email || !password)
    return NextResponse.json({ error: "Missing fields" }, { status: 400 })

  // Validate email format
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email))
    return NextResponse.json({ error: "Invalid email format" }, { status: 400 })

  await client.connect()
  const users = db.collection("users")

  const existing = await users.findOne({ email })
  if (existing)
    return NextResponse.json({ error: "Email already registered" }, { status: 409 })

  const password_hash = await bcrypt.hash(password, 10)

  await users.insertOne({
    user_id: crypto.randomUUID(),
    email,
    username: name,
    organization,
    password_hash,
    role: "user",
    profile_data: {},
    is_active: true,
    created_at: new Date(),
    updated_at: new Date(),
  })

  return NextResponse.json({ message: "Account created" }, { status: 201 })
}
