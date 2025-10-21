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

    async jwt({ token, user }) {
      if (user) {
        token.role = (user as any).role
      }
      return token
    },

    async session({ session, token }) {
      if (token?.sub) (session.user as any).id = token.sub
      if (token?.role) (session.user as any).role = token.role
      return session
    },
  },

  session: { strategy: "jwt" },
  secret: process.env.NEXTAUTH_SECRET,
}
