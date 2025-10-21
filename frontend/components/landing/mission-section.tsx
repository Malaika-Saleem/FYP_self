import { Shield, Eye, Users, Zap, Target, Heart } from "lucide-react"

export function MissionSection() {
  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-6 text-balance">
            {"We're on a Mission to Rethink Surveillance"}
          </h2>
          <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-pretty">
            DetectifAI transforms traditional security systems into intelligent, proactive defense networks that protect
            what matters most.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
          {/* What We Do */}
          <div className="text-center">
            <div className="mx-auto mb-6 p-4 bg-primary/10 rounded-full w-fit">
              <Eye className="h-12 w-12 text-primary" />
            </div>
            <h3 className="text-2xl font-bold mb-4">What We Do</h3>
            <p className="text-muted-foreground text-pretty">
              We develop AI-powered behavior analysis systems that detect suspicious activities, identify threats, and
              provide instant alerts to security teams before incidents escalate.
            </p>
          </div>

          {/* Our Mission */}
          <div className="text-center">
            <div className="mx-auto mb-6 p-4 bg-primary/10 rounded-full w-fit">
              <Target className="h-12 w-12 text-primary" />
            </div>
            <h3 className="text-2xl font-bold mb-4">Our Mission</h3>
            <p className="text-muted-foreground text-pretty">
              To create intelligent, ethical, and responsive surveillance solutions that enhance security while
              respecting privacy and human dignity in every implementation.
            </p>
          </div>

          {/* Who We Serve */}
          <div className="text-center">
            <div className="mx-auto mb-6 p-4 bg-primary/10 rounded-full w-fit">
              <Users className="h-12 w-12 text-primary" />
            </div>
            <h3 className="text-2xl font-bold mb-4">Who We Serve</h3>
            <p className="text-muted-foreground text-pretty">
              Law enforcement agencies, security firms, educational institutions, and businesses that require advanced
              threat detection and comprehensive security monitoring.
            </p>
          </div>
        </div>

        {/* Values */}
        <div className="mt-20 bg-card rounded-lg p-8">
          <h3 className="text-2xl font-bold text-center mb-8">Our Core Values</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="flex items-center space-x-3">
              <Shield className="h-6 w-6 text-primary flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Security First</h4>
                <p className="text-sm text-muted-foreground">Uncompromising protection standards</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Zap className="h-6 w-6 text-primary flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Innovation</h4>
                <p className="text-sm text-muted-foreground">Cutting-edge AI technology</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Heart className="h-6 w-6 text-primary flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Ethical AI</h4>
                <p className="text-sm text-muted-foreground">Responsible surveillance practices</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
