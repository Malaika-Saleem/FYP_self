"use client"

import { useAuth } from "@/components/auth-provider"
import { Navigation } from "@/components/navigation"
import { UserTable } from "@/components/users/user-table"
import { AddUserModal } from "@/components/users/add-user-modal"
import { redirect } from "next/navigation"
import { useEffect, useState } from "react"

export default function UsersPage() {
  const { user, isLoading } = useAuth()
  const [showAddModal, setShowAddModal] = useState(false)

  useEffect(() => {
    if (!isLoading && !user) {
      redirect("/signin")
    }
  }, [user, isLoading])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Loading users...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  return (
    <div className="min-h-screen bg-background">
      <Navigation />
      <main className="p-6">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold">User Management</h1>
              <p className="text-muted-foreground">Manage team members and their access permissions</p>
            </div>
          </div>

          <UserTable onAddUser={() => setShowAddModal(true)} />

          <AddUserModal isOpen={showAddModal} onClose={() => setShowAddModal(false)} />
        </div>
      </main>
    </div>
  )
}
