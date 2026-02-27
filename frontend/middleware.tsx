import { withAuth } from "next-auth/middleware"
import { NextResponse } from "next/server"

export default withAuth(
  function middleware(req) {
    const { pathname } = req.nextUrl
    const token = req.nextauth.token

    // Admin route protection
    if (pathname.startsWith("/admin") && token?.role !== "admin") {
      return NextResponse.redirect(new URL("/signin", req.url))
    }

    return NextResponse.next()
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        const { pathname } = req.nextUrl
        
        // Allow access to auth pages
        if (pathname === "/signin" || pathname === "/signup" || pathname === "/admin/signin") {
          return true
        }

        // Require auth for protected routes
        if (
          pathname.startsWith("/dashboard") ||
          pathname.startsWith("/search") ||
          pathname.startsWith("/admin")
        ) {
          return !!token
        }

        return true
      },
    },
    pages: {
      signIn: "/signin",
    },
  }
)

export const config = {
  matcher: [
    "/admin/:path*",
    "/dashboard/:path*",
    "/search/:path*",
    "/signin",
    "/signup"
  ],
}