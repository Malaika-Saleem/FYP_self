"use client"

import { useState, useEffect } from "react"
import { useAuth } from "@/components/auth-provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Search, Edit, Trash2, Plus, Loader2 } from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import { adminApi } from "@/lib/api"
import { AddUserModal } from "@/components/users/add-user-modal"
import { EditUserModal } from "@/components/users/edit-user-modal"

interface User {
  user_id: string
  username?: string
  name?: string
  email: string
  role: string
  is_active?: boolean
  created_at?: string
  organization?: string
  plan?: string
}

export default function AdminUsers() {
  const { user, logout } = useAuth()
  const [searchTerm, setSearchTerm] = useState("")
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)

  // Fetch users from backend
  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await adminApi.getUsers({
        search: searchTerm || undefined,
        limit: 100,
      })
      setUsers(response.users || [])
    } catch (err: any) {
      console.error("Error fetching users:", err)
      setError(err.message || "Failed to fetch users")
    } finally {
      setLoading(false)
    }
  }

  // Refetch when search term changes (with debounce)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchTerm !== undefined) {
        fetchUsers()
      }
    }, 500)

    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchTerm])

  const handleDeleteUser = async (userId: string) => {
    if (!confirm("Are you sure you want to delete this user?")) {
      return
    }

    try {
      await adminApi.deleteUser(userId)
      // Refresh users list
      fetchUsers()
    } catch (err: any) {
      alert(err.message || "Failed to delete user")
    }
  }

  const handleUserCreated = () => {
    setShowAddModal(false)
    fetchUsers()
  }

  const handleUserUpdated = () => {
    setEditingUser(null)
    fetchUsers()
  }

  const filteredUsers = users.filter(
    (user) =>
      (user.username || user.name || "").toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.email.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card">
        <div className="flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Image src="/logo.png" alt="DetectifAI" width={32} height={32} />
            <span className="text-xl font-bold text-white">DetectifAI Admin</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">Welcome, {user?.name}</span>
            <Button variant="ghost" size="sm" onClick={logout}>
              Logout
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6">
        <div className="max-w-6xl mx-auto">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 mb-6">
            <Link href="/admin/dashboard">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
          </div>

          <div className="flex items-center justify-between mb-6">
            <h1 className="text-3xl font-bold text-white">User Management</h1>
            <Button 
              className="bg-primary hover:bg-primary/90 text-primary-foreground"
              onClick={() => setShowAddModal(true)}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add User
            </Button>
          </div>

          {error && (
            <Card className="bg-destructive/10 border-destructive mb-6">
              <CardContent className="p-4">
                <p className="text-destructive">{error}</p>
              </CardContent>
            </Card>
          )}

          {/* Search */}
          <Card className="bg-card border-border mb-6">
            <CardContent className="p-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                <Input
                  placeholder="Search users by name, email, or organization..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10 bg-input border-border text-white"
                />
              </div>
            </CardContent>
          </Card>

          {/* Users Table */}
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-white">Users ({filteredUsers.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : filteredUsers.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">
                  <p>No users found</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-3 px-4 text-muted-foreground font-medium">Name</th>
                        <th className="text-left py-3 px-4 text-muted-foreground font-medium">Email</th>
                        <th className="text-left py-3 px-4 text-muted-foreground font-medium">Role</th>
                        <th className="text-left py-3 px-4 text-muted-foreground font-medium">Status</th>
                        <th className="text-left py-3 px-4 text-muted-foreground font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredUsers.map((user) => (
                        <tr key={user.user_id} className="border-b border-border/50">
                          <td className="py-3 px-4 text-white">{user.username || user.name || "N/A"}</td>
                          <td className="py-3 px-4 text-muted-foreground">{user.email}</td>
                          <td className="py-3 px-4">
                            <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                              {user.role || "user"}
                            </Badge>
                          </td>
                          <td className="py-3 px-4">
                            <Badge variant={user.is_active !== false ? "default" : "destructive"}>
                              {user.is_active !== false ? "active" : "inactive"}
                            </Badge>
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-2">
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => setEditingUser(user)}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteUser(user.user_id)}
                                className="text-destructive hover:text-destructive"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </main>

      <AddUserModal isOpen={showAddModal} onClose={() => setShowAddModal(false)} onSuccess={handleUserCreated} />
      {editingUser && (
        <EditUserModal 
          user={editingUser} 
          isOpen={!!editingUser} 
          onClose={() => setEditingUser(null)} 
          onSuccess={handleUserUpdated}
        />
      )}
    </div>
  )
}
