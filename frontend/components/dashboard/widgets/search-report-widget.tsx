"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, Camera, FileText, Download, Filter, ImageIcon } from "lucide-react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"

export function SearchReportWidget() {
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")
  const [isReportModalOpen, setIsReportModalOpen] = useState(false)

  const handleSearch = () => {
    if (searchQuery.trim()) {
      console.log("Searching for:", searchQuery)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Search Section */}
      <Card className="border-gray-800">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Search className="h-5 w-5 text-primary" />
            <span>Search By Prompt</span>
          </CardTitle>
          <CardDescription>Use natural language to find specific moments in your surveillance footage</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              placeholder="Search incidents, zones, or behaviours..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleSearch()}
              className="pl-10 pr-10"
            />
            <button
              type="button"
              onClick={() => router.push("/search")}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-muted-foreground hover:text-primary transition-colors"
              title="Search by image"
            >
              <ImageIcon className="w-4 h-4" />
            </button>
          </div>
          <div className="flex space-x-2">
            <Button size="icon" variant="outline" onClick={() => router.push("/search")}>
              <Filter className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="secondary">Fire 🔥</Badge>
            <Badge variant="secondary">Zone 3</Badge>
            <Badge variant="secondary">Today</Badge>
          </div>
          <Button onClick={handleSearch} className="w-full" disabled={!searchQuery.trim()}>
            <Search className="mr-2 h-4 w-4" />
            Search
          </Button>
        </CardContent>
      </Card>

      {/* Report Section */}
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <FileText className="h-5 w-5 text-primary" />
            <span>Generate Report</span>
          </CardTitle>
          <CardDescription>Get summary of all suspicious behaviours and alerts</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-muted rounded-lg p-4 border border-border">
            <h4 className="font-medium mb-2">Latest Report Summary</h4>
            <div className="space-y-2 text-sm text-muted-foreground">
              <div className="flex justify-between">
                <span>Total Incidents Today:</span>
                <span className="font-medium text-foreground">12</span>
              </div>
              <div className="flex justify-between">
                <span>High Priority Alerts:</span>
                <span className="font-medium text-red-500">3</span>
              </div>
              <div className="flex justify-between">
                <span>Most Active Zone:</span>
                <span className="font-medium text-foreground">Zone 3</span>
              </div>
            </div>
          </div>

          <Dialog open={isReportModalOpen} onOpenChange={setIsReportModalOpen}>
            <DialogTrigger asChild>
              <Button className="w-full">
                <FileText className="mr-2 h-4 w-4" />
                Generate Report
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Generate Report</DialogTitle>
                <DialogDescription>Select options for your report</DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Date Range</label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select date range" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="today">Today</SelectItem>
                      <SelectItem value="week">This Week</SelectItem>
                      <SelectItem value="month">This Month</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium">Zones</label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select zones" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Zones</SelectItem>
                      <SelectItem value="zone1">Zone 1</SelectItem>
                      <SelectItem value="zone2">Zone 2</SelectItem>
                      <SelectItem value="zone3">Zone 3</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <label className="text-sm font-medium">Format</label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Select format" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="pdf">PDF</SelectItem>
                      <SelectItem value="csv">CSV</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button className="w-full">
                  <Download className="mr-2 h-4 w-4" />
                  Generate & Download
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </CardContent>
      </Card>
    </div>
  )
}
