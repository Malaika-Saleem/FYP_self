"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Eye, EyeOff, Loader2, Shield, Users, EyeIcon } from "lucide-react"
import { adminApi } from "@/lib/api"

interface User {
  user_id: string
  username?: string
  name?: string
  email: string
  role: string
  is_active?: boolean
}

interface EditUserModalProps {
  user: User
  isOpen: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function EditUserModal({ user, isOpen, onClose, onSuccess }: EditUserModalProps) {
  const [formData, setFormData] = useState({
    name: user.username || user.name || "",
    email: user.email,
    password: "",
    role: user.role || "user",
    is_active: user.is_active !== false,
  })
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (user) {
      setFormData({
        name: user.username || user.name || "",
        email: user.email,
        password: "",
        role: user.role || "user",
        is_active: user.is_active !== false,
      })
    }
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!formData.name || !formData.email || !formData.role) {
      setError("Please fill in all required fields")
      return
    }

    setIsLoading(true)

    try {
      const updateData: any = {
        username: formData.name,
        name: formData.name,
        email: formData.email,
        role: formData.role,
        is_active: formData.is_active,
      }

      // Only include password if it's provided
      if (formData.password) {
        updateData.password = formData.password
      }

      await adminApi.updateUser(user.user_id, updateData)
      setIsLoading(false)
      handleClose()
      if (onSuccess) onSuccess()
    } catch (err: any) {
      setError(err.message || "Failed to update user")
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    setFormData({ name: "", email: "", password: "", role: "user", is_active: true })
    setShowPassword(false)
    setError("")
    onClose()
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "admin":
        return <Shield className="h-4 w-4" />
      case "contributor":
        return <Users className="h-4 w-4" />
      case "viewer":
        return <EyeIcon className="h-4 w-4" />
      default:
        return null
    }
  }

  const getRoleDescription = (role: string) => {
    switch (role) {
      case "admin":
        return "Full access to all features and user management"
      case "contributor":
        return "Can view, search, and generate reports"
      case "viewer":
        return "Read-only access to dashboard and alerts"
      default:
        return ""
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Edit User</DialogTitle>
          <DialogDescription>Update user information and permissions</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Full Name</Label>
            <Input
              id="name"
              placeholder="Enter full name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              type="email"
              placeholder="Enter email address"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password (leave blank to keep current)</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter new password (optional)"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Select value={formData.role} onValueChange={(value) => setFormData({ ...formData, role: value })}>
              <SelectTrigger>
                <SelectValue placeholder="Select user role" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">
                  <div className="flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-red-500" />
                    <span>Admin</span>
                  </div>
                </SelectItem>
                <SelectItem value="contributor">
                  <div className="flex items-center space-x-2">
                    <Users className="h-4 w-4 text-blue-500" />
                    <span>Contributor</span>
                  </div>
                </SelectItem>
                <SelectItem value="viewer">
                  <div className="flex items-center space-x-2">
                    <EyeIcon className="h-4 w-4 text-green-500" />
                    <span>Viewer</span>
                  </div>
                </SelectItem>
                <SelectItem value="user">
                  <div className="flex items-center space-x-2">
                    <Users className="h-4 w-4 text-gray-500" />
                    <span>User</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            {formData.role && (
              <p className="text-xs text-muted-foreground flex items-center space-x-1">
                {getRoleIcon(formData.role)}
                <span>{getRoleDescription(formData.role)}</span>
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="is_active" className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded"
              />
              <span>Active User</span>
            </Label>
          </div>

          {error && <div className="text-destructive text-sm">{error}</div>}

          <div className="flex space-x-2 pt-4">
            <Button type="button" variant="outline" onClick={handleClose} className="flex-1 bg-transparent">
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading} className="flex-1">
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Updating...
                </>
              ) : (
                "Update User"
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}



