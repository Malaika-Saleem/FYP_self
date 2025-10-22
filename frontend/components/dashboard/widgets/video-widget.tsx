"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Play, Pause, SkipBack, SkipForward, Volume2, Maximize, Grid3X3, Circle } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export function VideoWidget() {
  const [isPlaying, setIsPlaying] = useState(true)
  const [volume, setVolume] = useState(50)

  return (
    <Card className="border-gray-800">
      <CardContent className="p-0">
        {/* Video Player Container */}
        <div className="relative aspect-video bg-black rounded-lg overflow-hidden">
          {/* Mock Video Content */}
          <div className="w-full h-full bg-muted flex items-center justify-center">
            <div className="text-center text-white">
              <Play className="h-16 w-16 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Live Surveillance Feed</p>
            </div>
          </div>

          {/* Overlays */}
          <div className="absolute top-4 left-4 space-y-2">
            <Badge variant="destructive" className="bg-red-600">
              LIVE
            </Badge>
            <div className="text-white text-sm font-medium">
              Zone 3 - Main Entrance
            </div>
            <div className="text-white text-xs">
              Camera 1
            </div>
          </div>

          {/* Recording Status */}
          <div className="absolute top-4 right-4 flex items-center space-x-2">
            <Circle className="h-3 w-3 fill-red-500 text-red-500 animate-pulse" />
            <span className="text-white text-xs">Recording</span>
          </div>

          {/* Multi-Camera Toggle */}
          <div className="absolute top-4 right-20">
            <Select defaultValue="1">
              <SelectTrigger className="w-32 bg-black/50 border-white/20 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">1 Camera</SelectItem>
                <SelectItem value="2">2 Cameras</SelectItem>
                <SelectItem value="4">4 Cameras</SelectItem>
                <SelectItem value="6">6 Cameras</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Controls Overlay */}
          <div className="absolute bottom-0 left-0 right-0 bg-black/70 p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-white hover:bg-white/20"
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </Button>
                <Button size="sm" variant="ghost" className="text-white hover:bg-white/20">
                  <SkipBack className="h-4 w-4" />
                </Button>
                <Button size="sm" variant="ghost" className="text-white hover:bg-white/20">
                  <SkipForward className="h-4 w-4" />
                </Button>
              </div>

              <div className="flex items-center space-x-2">
                <Volume2 className="h-4 w-4 text-white" />
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={volume}
                  onChange={(e) => setVolume(Number(e.target.value))}
                  className="w-20"
                />
              </div>

              <Button size="sm" variant="ghost" className="text-white hover:bg-white/20">
                <Maximize className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
