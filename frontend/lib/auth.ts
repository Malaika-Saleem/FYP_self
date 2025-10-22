import { MongoClient, ObjectId } from 'mongodb'
import bcrypt from 'bcryptjs'
import jwt from 'jsonwebtoken'

const MONGODB_URI = process.env.MONGO_URI || 'mongodb://localhost:27017/detectifai'
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key'

let client: MongoClient
let clientPromise: Promise<MongoClient>

if (process.env.NODE_ENV === 'development') {
  // In development mode, use a global variable so that the value
  // is preserved across module reloads caused by HMR (Hot Module Replacement).
  const globalWithMongo = global as typeof globalThis & {
    _mongoClientPromise?: Promise<MongoClient>
  }

  if (!globalWithMongo._mongoClientPromise) {
    client = new MongoClient(MONGODB_URI)
    globalWithMongo._mongoClientPromise = client.connect()
  }
  clientPromise = globalWithMongo._mongoClientPromise!
} else {
  // In production mode, it's best to not use a global variable.
  client = new MongoClient(MONGODB_URI)
  clientPromise = client.connect()
}

export async function getDb() {
  const client = await clientPromise
  return client.db()
}

export interface User {
  _id?: ObjectId
  user_id: string
  username?: string
  email: string
  password_hash?: string
  role: 'admin' | 'user'
  profile_data?: any
  is_active: boolean
  created_at: Date
  updated_at: Date
  last_login?: Date
  google_id?: string
  name?: string
  image?: string
  organization?: string
}

export interface UserSession {
  _id?: ObjectId
  session_id: string
  user_id: string
  session_token: string
  expires_at: Date
  ip_address?: string
  user_agent?: string
  created_at: Date
}

export async function createUser(userData: Omit<User, '_id' | 'created_at' | 'updated_at'>): Promise<User | null> {
  try {
    const db = await getDb()
    const now = new Date()

    const user: User = {
      ...userData,
      created_at: now,
      updated_at: now,
      is_active: true,
    }

    const result = await db.collection('users').insertOne(user)
    return { ...user, _id: result.insertedId }
  } catch (error) {
    console.error('Error creating user:', error)
    return null
  }
}

export async function findUserByEmail(email: string): Promise<User | null> {
  try {
    const db = await getDb()
    const user = await db.collection('users').findOne({ email })
    return user as User | null
  } catch (error) {
    console.error('Error finding user by email:', error)
    return null
  }
}

export async function findUserByGoogleId(googleId: string): Promise<User | null> {
  try {
    const db = await getDb()
    const user = await db.collection('users').findOne({ google_id: googleId })
    return user as User | null
  } catch (error) {
    console.error('Error finding user by Google ID:', error)
    return null
  }
}

export async function updateUserLastLogin(userId: string): Promise<void> {
  try {
    const db = await getDb()
    await db.collection('users').updateOne(
      { user_id: userId },
      { $set: { last_login: new Date(), updated_at: new Date() } }
    )
  } catch (error) {
    console.error('Error updating user last login:', error)
  }
}

export async function createSession(sessionData: Omit<UserSession, '_id'>): Promise<UserSession | null> {
  try {
    const db = await getDb()
    const result = await db.collection('user_sessions').insertOne(sessionData)
    return { ...sessionData, _id: result.insertedId }
  } catch (error) {
    console.error('Error creating session:', error)
    return null
  }
}

export async function findSessionByToken(token: string): Promise<UserSession | null> {
  try {
    const db = await getDb()
    const session = await db.collection('user_sessions').findOne({ session_token: token })
    return session as UserSession | null
  } catch (error) {
    console.error('Error finding session by token:', error)
    return null
  }
}

export async function deleteSession(token: string): Promise<void> {
  try {
    const db = await getDb()
    await db.collection('user_sessions').deleteOne({ session_token: token })
  } catch (error) {
    console.error('Error deleting session:', error)
  }
}

export async function hashPassword(password: string): Promise<string> {
  return await bcrypt.hash(password, 12)
}

export async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return await bcrypt.compare(password, hash)
}

export function generateToken(payload: any): string {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '24h' })
}

export function verifyToken(token: string): any {
  try {
    return jwt.verify(token, JWT_SECRET)
  } catch (error) {
    return null
  }
}

export function generateUserId(): string {
  return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

export function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}
