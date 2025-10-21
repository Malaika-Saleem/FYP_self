import { Card, CardContent } from "@/components/ui/card"
import { Shield, Eye, Zap, Users, Award, Globe } from "lucide-react"

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-background">
      <main className="py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
          {/* Hero Section */}
          <div className="text-center space-y-6">
            <div className="flex items-center justify-center space-x-2 mb-4">
              <Shield className="h-12 w-12 text-primary" />
            </div>
            <h1 className="text-4xl md:text-5xl font-bold text-balance">About DetectifAI</h1>
            <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-pretty">
              We're revolutionizing surveillance technology with AI-powered intelligence that keeps communities and
              businesses safe.
            </p>
          </div>

          {/* Mission Statement */}
          <div className="bg-card rounded-lg p-8 border border-border">
            <div className="max-w-4xl mx-auto text-center">
              <h2 className="text-2xl font-bold mb-4">Our Mission</h2>
              <p className="text-lg text-muted-foreground text-pretty">
                To create intelligent, ethical, and responsive surveillance solutions that enhance security while
                respecting privacy and human dignity. We believe that advanced AI technology should serve humanity by
                making our world safer and more secure.
              </p>
            </div>
          </div>

          {/* Key Features */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card className="border-border text-center">
              <CardContent className="p-6">
                <Eye className="h-12 w-12 text-primary mx-auto mb-4" />
                <h3 className="text-xl font-bold mb-2">AI-Powered Detection</h3>
                <p className="text-muted-foreground text-pretty">
                  Advanced computer vision and machine learning algorithms that detect threats in real-time with 99.9%
                  accuracy.
                </p>
              </CardContent>
            </Card>

            <Card className="border-border text-center">
              <CardContent className="p-6">
                <Zap className="h-12 w-12 text-primary mx-auto mb-4" />
                <h3 className="text-xl font-bold mb-2">Instant Alerts</h3>
                <p className="text-muted-foreground text-pretty">
                  Receive immediate notifications when suspicious activities are detected, enabling rapid response to
                  potential threats.
                </p>
              </CardContent>
            </Card>

            <Card className="border-border text-center">
              <CardContent className="p-6">
                <Users className="h-12 w-12 text-primary mx-auto mb-4" />
                <h3 className="text-xl font-bold mb-2">Team Collaboration</h3>
                <p className="text-muted-foreground text-pretty">
                  Comprehensive user management and role-based access controls for seamless security team coordination.
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Stats */}
          <div className="bg-card rounded-lg p-8 border border-border">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-8 text-center">
              <div>
                <div className="text-3xl font-bold text-primary mb-2">10,000+</div>
                <div className="text-muted-foreground">Cameras Monitored</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-primary mb-2">99.9%</div>
                <div className="text-muted-foreground">Detection Accuracy</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-primary mb-2">24/7</div>
                <div className="text-muted-foreground">Monitoring</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-primary mb-2">500+</div>
                <div className="text-muted-foreground">Security Teams</div>
              </div>
            </div>
          </div>

          {/* Values */}
          <div className="space-y-8">
            <div className="text-center">
              <h2 className="text-3xl font-bold mb-4">Our Values</h2>
              <p className="text-muted-foreground max-w-2xl mx-auto text-pretty">
                The principles that guide everything we do at DetectifAI
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <div className="flex items-start space-x-4">
                <Shield className="h-8 w-8 text-primary mt-1 flex-shrink-0" />
                <div>
                  <h3 className="font-bold mb-2">Security First</h3>
                  <p className="text-sm text-muted-foreground text-pretty">
                    Uncompromising commitment to protecting your data and maintaining the highest security standards.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <Award className="h-8 w-8 text-primary mt-1 flex-shrink-0" />
                <div>
                  <h3 className="font-bold mb-2">Innovation</h3>
                  <p className="text-sm text-muted-foreground text-pretty">
                    Continuously pushing the boundaries of AI technology to deliver cutting-edge surveillance solutions.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <Globe className="h-8 w-8 text-primary mt-1 flex-shrink-0" />
                <div>
                  <h3 className="font-bold mb-2">Ethical AI</h3>
                  <p className="text-sm text-muted-foreground text-pretty">
                    Responsible development and deployment of AI that respects privacy and human rights.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
