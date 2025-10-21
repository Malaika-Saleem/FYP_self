import { Shield, Zap } from "lucide-react"

export function PricingHeader() {
  return (
    <div className="text-center space-y-6">
      

      <h1 className="text-4xl md:text-5xl font-bold text-balance">Choose Your Security Plan</h1>

      <p className="text-xl text-muted-foreground max-w-3xl mx-auto text-pretty">
        Flexible pricing designed for security teams of all sizes. Start with our basic plan and scale as your
        surveillance needs grow.
      </p>

      <div className="flex items-center justify-center space-x-8 text-sm text-muted-foreground">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span>No setup fees</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span>Cancel anytime</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-primary rounded-full"></div>
          <span>24/7 support</span>
        </div>
      </div>
    </div>
  )
}
