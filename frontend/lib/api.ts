const FLASK_API_URL = process.env.NEXT_PUBLIC_FLASK_API_URL || 'http://localhost:5000'

export interface ApiError {
  error: string
  message?: string
}

/**
 * Get authentication token from localStorage or session
 * Note: For admin access, users need to login through the Flask backend
 * which will return a JWT token that should be stored here
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null
  // Try multiple possible token storage locations
  return (
    localStorage.getItem('auth_token') || 
    localStorage.getItem('detectifai-token') ||
    localStorage.getItem('flask_token') ||
    null
  )
}

/**
 * Set authentication token
 */
export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') return
  localStorage.setItem('auth_token', token)
}

/**
 * Remove authentication token
 */
export function removeAuthToken(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem('auth_token')
  localStorage.removeItem('detectifai-token')
}

/**
 * Make authenticated API request to Flask backend
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken()
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const response = await fetch(`${FLASK_API_URL}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      error: `HTTP ${response.status}: ${response.statusText}`,
    }))
    throw new Error(error.error || error.message || 'Request failed')
  }

  return response.json()
}

/**
 * Make authenticated API request to Next.js API routes
 */
async function nextApiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
    credentials: 'include', // Include cookies for NextAuth session
  })

  if (!response.ok) {
    const error: ApiError = await response.json().catch(() => ({
      error: `HTTP ${response.status}: ${response.statusText}`,
    }))
    throw new Error(error.error || error.message || 'Request failed')
  }

  return response.json()
}

/**
 * Admin API functions - Now using Next.js API routes
 */
export const adminApi = {
  /**
   * Get all users
   */
  async getUsers(params?: {
    page?: number
    limit?: number
    search?: string
    role?: string
    status?: string
  }): Promise<{
    users: any[]
    total: number
    page: number
    limit: number
    pages: number
  }> {
    const queryParams = new URLSearchParams()
    if (params?.page) queryParams.set('page', params.page.toString())
    if (params?.limit) queryParams.set('limit', params.limit.toString())
    if (params?.search) queryParams.set('search', params.search)
    if (params?.role) queryParams.set('role', params.role)
    if (params?.status) queryParams.set('status', params.status)

    const query = queryParams.toString()
    return nextApiRequest(`/api/admin/users${query ? `?${query}` : ''}`)
  },

  /**
   * Get a single user by ID
   */
  async getUser(userId: string): Promise<{ user: any }> {
    return nextApiRequest(`/api/admin/users/${userId}`)
  },

  /**
   * Create a new user
   */
  async createUser(userData: {
    email: string
    password: string
    username?: string
    name?: string
    role?: string
  }): Promise<{ message: string; user: any }> {
    return nextApiRequest('/api/admin/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    })
  },

  /**
   * Update a user
   */
  async updateUser(
    userId: string,
    userData: {
      username?: string
      name?: string
      email?: string
      role?: string
      is_active?: boolean
      password?: string
    }
  ): Promise<{ message: string; user: any }> {
    return nextApiRequest(`/api/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(userData),
    })
  },

  /**
   * Delete a user
   */
  async deleteUser(userId: string): Promise<{ message: string }> {
    return nextApiRequest(`/api/admin/users/${userId}`, {
      method: 'DELETE',
    })
  },
}

