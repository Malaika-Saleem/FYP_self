"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Checkbox } from "@/components/ui/checkbox"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Search, Plus, MoreHorizontal, Edit, Trash2, Shield, Eye, Users } from "lucide-react"

interface User {
  id: string
  name: string
  email: string
  avatar?: string
  role: "admin" | "contributor" | "viewer"
  joinDate: string
  lastActive: string
  status: "active" | "inactive"
}

interface UserTableProps {
  onAddUser: () => void
}

export function UserTable({ onAddUser }: UserTableProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [roleFilter, setRoleFilter] = useState<string>("all")
  const [selectedUsers, setSelectedUsers] = useState<string[]>([])

  // Mock user data
  const users: User[] = [
    {
      id: "1",
      name: "John Smith",
      email: "john.smith@security.com",
      avatar: "/placeholder.svg?height=40&width=40",
      role: "admin",
      joinDate: "2024-01-15",
      lastActive: "2 hours ago",
      status: "active",
    },
    {
      id: "2",
      name: "Sarah Johnson",
      email: "sarah.johnson@security.com",
      avatar: "/placeholder.svg?height=40&width=40",
      role: "contributor",
      joinDate: "2024-02-20",
      lastActive: "1 day ago",
      status: "active",
    },
    {
      id: "3",
      name: "Mike Davis",
      email: "mike.davis@security.com",
      avatar: "/placeholder.svg?height=40&width=40",
      role: "viewer",
      joinDate: "2024-03-10",
      lastActive: "3 days ago",
      status: "active",
    },
    {
      id: "4",
      name: "Emily Chen",
      email: "emily.chen@security.com",
      avatar: "/placeholder.svg?height=40&width=40",
      role: "contributor",
      joinDate: "2024-01-28",
      lastActive: "5 hours ago",
      status: "active",
    },
    {
      id: "5",
      name: "Robert Wilson",
      email: "robert.wilson@security.com",
      avatar: "/placeholder.svg?height=40&width=40",
      role: "viewer",
      joinDate: "2024-03-05",
      lastActive: "1 week ago",
      status: "inactive",
    },
  ]

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "admin":
        return <Shield className="h-4 w-4" />
      case "contributor":
        return <Users className="h-4 w-4" />
      case "viewer":
        return <Eye className="h-4 w-4" />
      default:
        return null
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case "admin":
        return "bg-red-500/10 text-red-500 border-red-500/20"
      case "contributor":
        return "bg-blue-500/10 text-blue-500 border-blue-500/20"
      case "viewer":
        return "bg-green-500/10 text-green-500 border-green-500/20"
      default:
        return "bg-gray-500/10 text-gray-500 border-gray-500/20"
    }
  }

  const filteredUsers = users.filter((user) => {
    const matchesSearch =
      user.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesRole = roleFilter === "all" || user.role === roleFilter
    return matchesSearch && matchesRole
  })

  const handleSelectUser = (userId: string, checked: boolean) => {
    if (checked) {
      setSelectedUsers([...selectedUsers, userId])
    } else {
      setSelectedUsers(selectedUsers.filter((id) => id !== userId))
    }
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedUsers(filteredUsers.map((user) => user.id))
    } else {
      setSelectedUsers([])
    }
  }

  return (
    <Card className="border-border">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Team Members ({filteredUsers.length})</CardTitle>
          <Button onClick={onAddUser}>
            <Plus className="mr-2 h-4 w-4" />
            Add User
          </Button>
        </div>

        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mt-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Filter by role" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Roles</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
              <SelectItem value="contributor">Contributor</SelectItem>
              <SelectItem value="viewer">Viewer</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>

      <CardContent>
        {/* Bulk Actions */}
        {selectedUsers.length > 0 && (
          <div className="mb-4 p-3 bg-muted rounded-lg border border-border">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{selectedUsers.length} users selected</span>
              <div className="flex space-x-2">
                <Button variant="outline" size="sm" className="bg-transparent">
                  Edit Permissions
                </Button>
                <Button variant="outline" size="sm" className="text-destructive bg-transparent">
                  Remove Users
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* User Table */}
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left p-3">
                  <Checkbox
                    checked={selectedUsers.length === filteredUsers.length && filteredUsers.length > 0}
                    onCheckedChange={handleSelectAll}
                  />
                </th>
                <th className="text-left p-3 font-medium">User</th>
                <th className="text-left p-3 font-medium">Role</th>
                <th className="text-left p-3 font-medium">Join Date</th>
                <th className="text-left p-3 font-medium">Last Active</th>
                <th className="text-left p-3 font-medium">Status</th>
                <th className="text-left p-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr key={user.id} className="border-b border-border hover:bg-muted/50">
                  <td className="p-3">
                    <Checkbox
                      checked={selectedUsers.includes(user.id)}
                      onCheckedChange={(checked) => handleSelectUser(user.id, checked as boolean)}
                    />
                  </td>
                  <td className="p-3">
                    <div className="flex items-center space-x-3">
                      <Avatar className="h-10 w-10">
                        <AvatarImage src={user.avatar || "/placeholder.svg"} alt={user.name} />
                        <AvatarFallback>
                          {user.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="font-medium">{user.name}</div>
                        <div className="text-sm text-muted-foreground">{user.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="p-3">
                    <Badge className={`${getRoleColor(user.role)} border`}>
                      <div className="flex items-center space-x-1">
                        {getRoleIcon(user.role)}
                        <span className="capitalize">{user.role}</span>
                      </div>
                    </Badge>
                  </td>
                  <td className="p-3 text-sm text-muted-foreground">{new Date(user.joinDate).toLocaleDateString()}</td>
                  <td className="p-3 text-sm text-muted-foreground">{user.lastActive}</td>
                  <td className="p-3">
                    <Badge variant={user.status === "active" ? "default" : "secondary"} className="text-xs">
                      {user.status}
                    </Badge>
                  </td>
                  <td className="p-3">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>
                          <Edit className="mr-2 h-4 w-4" />
                          Edit User
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                          <Shield className="mr-2 h-4 w-4" />
                          Change Role
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-destructive">
                          <Trash2 className="mr-2 h-4 w-4" />
                          Remove User
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-6">
          <div className="text-sm text-muted-foreground">
            Showing {filteredUsers.length} of {users.length} users
          </div>
          <div className="flex space-x-2">
            <Button variant="outline" size="sm" disabled className="bg-transparent">
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled className="bg-transparent">
              Next
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
