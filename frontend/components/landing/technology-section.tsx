import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Cpu, Zap, Brain, Search, Play } from "lucide-react"

export function TechnologySection() {
  const technologies = [
    {
      name: "OpenCV",
      description: "Computer vision processing",
      icon: <Cpu className="h-6 w-6" />,
    },
    {
      name: "MediaPipe",
      description: "Real-time pose detection",
      icon: <Zap className="h-6 w-6" />,
    },
    {
      name: "CLIP",
      description: "Visual understanding",
      icon: <Brain className="h-6 w-6" />,
    },
    {
      name: "Sentence-BERT",
      description: "Natural language search",
      icon: <Search className="h-6 w-6" />,
    },
  ]

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-card">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-6 text-balance">Powered by AI, Built for Speed</h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-pretty">
            Our advanced AI stack processes video feeds in real-time, delivering instant insights and alerts when they
            matter most.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Technology Stack */}
          <div>
            <h3 className="text-2xl font-bold mb-6">Advanced AI Technologies</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {technologies.map((tech, index) => (
                <Card key={index} className="border-gray-800">
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-primary/10 rounded-lg text-primary">{tech.icon}</div>
                      <div>
                        <h4 className="font-semibold">{tech.name}</h4>
                        <p className="text-sm text-muted-foreground">{tech.description}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            <div className="mt-8 space-y-4">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-primary rounded-full"></div>
                <span className="text-muted-foreground">Real-time video processing at 30+ FPS</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-primary rounded-full"></div>
                <span className="text-muted-foreground">Multi-camera feed analysis simultaneously</span>
              </div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-primary rounded-full"></div>
                <span className="text-muted-foreground">Cloud-based AI inference with edge computing</span>
              </div>
            </div>
          </div>

          {/* Demo Section */}
          <div className="bg-background rounded-lg p-8 border border-gray-800">
            <h3 className="text-xl font-bold mb-4">See DetectifAI in Action</h3>
            <p className="text-muted-foreground mb-6 text-pretty">
              Experience our AI-powered surveillance capabilities with a live demonstration of threat detection and
              video search functionality.
            </p>

            {/* Mock Video Player */}
            <div className="bg-card rounded-lg p-6 mb-6 border border-gray-800">
              <div className="aspect-video bg-muted rounded-lg flex items-center justify-center mb-4">
                <Play className="h-16 w-16 text-muted-foreground" />
              </div>
              <div className="text-sm text-muted-foreground text-center">
                Live Demo: AI Threat Detection in Real-time
              </div>
            </div>

            <Link href="/dashboard">
              <Button className="w-full">
                <Play className="mr-2 h-4 w-4" />
                Try Demo
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}
