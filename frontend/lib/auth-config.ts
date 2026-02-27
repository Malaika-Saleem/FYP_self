import type { NextAuthOptions } from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import CredentialsProvider from "next-auth/providers/credentials"
import { MongoClient } from "mongodb"
import bcrypt from "bcryptjs"

const client = new MongoClient(process.env.MONGO_URI!)
const db = client.db()

export const authOptions: NextAuthOptions = {
  providers: [
    // Google login
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    }),

    // Email / password login
    CredentialsProvider({
      name: "Credentials",
      credentials: {
        email: { label: "Email", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        try {
          // Validate email format
          const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
          if (!emailRegex.test(credentials!.email)) return null

          await client.connect()
          const users = db.collection("users")
          const user = await users.findOne({ email: credentials!.email })

          if (!user || !user.password_hash) return null
          const valid = await bcrypt.compare(credentials!.password, user.password_hash)
          if (!valid) return null

          return {
            id: user.user_id,
            email: user.email,
            name: user.username,
            role: user.role || "user",
          }
        } catch (error) {
          console.error("Auth error:", error)
          return null
        }
      },
    }),
  ],

  pages: {
    signIn: "/signin",
    error: "/signin",
  },

  callbacks: {
    // Add user to DB on first Google login
    async signIn({ user, account }) {
      if (account?.provider === "google") {
        await client.connect()
        const users = db.collection("users")
        const existing = await users.findOne({ email: user.email })

        if (!existing) {
          await users.insertOne({
            user_id: crypto.randomUUID(),
            email: user.email,
            username: user.name,
            password_hash: "",
            role: "user",
            profile_data: {},
            is_active: true,
            created_at: new Date(),
            updated_at: new Date(),
          })
        }
      }
      return true
    },

    async jwt({ token, user, account }) {
      // When user first signs in, get their database user_id
      if (user) {
        try {
          await client.connect()
          const users = db.collection("users")
          const dbUser = await users.findOne({ 
            $or: [
              { email: user.email },
              { user_id: (user as any).id } // For credentials login
            ]
          })
          
          if (dbUser) {
            // Store database user_id in token (not Google ID)
            token.userId = dbUser.user_id
            token.role = dbUser.role || (user as any).role || "user"
          } else if ((user as any).id) {
            // Fallback to user.id if database lookup fails (shouldn't happen)
            token.userId = (user as any).id
            token.role = (user as any).role || "user"
          }
        } catch (error) {
          console.error("Error in JWT callback:", error)
          // Fallback to user.id if database lookup fails
          if ((user as any).id) {
            token.userId = (user as any).id
            token.role = (user as any).role || "user"
          }
        }
      }
      // On token refresh, preserve existing userId and role
      // (user is undefined on refresh, so we keep the existing token values)
      return token
    },

    async session({ session, token }) {
      // Use userId from token (database user_id) instead of token.sub (which might be Google ID)
      if (token?.userId) {
        (session.user as any).id = token.userId
      } else if (token?.sub) {
        // Fallback to token.sub if userId not available
        (session.user as any).id = token.sub
      }
      if (token?.role) {
        (session.user as any).role = token.role
      }
      return session
    },
  },

  session: { strategy: "jwt" },
  secret: process.env.NEXTAUTH_SECRET || process.env.AUTH_SECRET,
}

// Validate that secret is set
if (!process.env.NEXTAUTH_SECRET && !process.env.AUTH_SECRET) {
  console.error("⚠️ WARNING: NEXTAUTH_SECRET is not set in environment variables!")
  console.error("Please add NEXTAUTH_SECRET to your .env.local file")
  console.error("Current working directory:", process.cwd())
  console.error("NODE_ENV:", process.env.NODE_ENV)
} else {
  console.log("✅ NEXTAUTH_SECRET is loaded successfully")
}
