import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowRight, RefreshCw, FolderOpen, Tag } from "lucide-react"

export function FeatureCards() {
  const features = [
    {
      icon: <RefreshCw className="h-8 w-8 text-primary" />,
      title: "Search Videos",
      description:
        "Search through long videos to get your desired clip and retrieve the video timestamps based on prompt",
      cta: "Enter Prompt",
      href: "/search",
      disabled: false,
    },
    {
      icon: <FolderOpen className="h-8 w-8 text-primary" />,
      title: "Dashboard",
      description:
        "We have all your video analysis under a single dashboard. Let's get started with your own surveillance dashboard",
      cta: "Get Summary",
      href: "/dashboard",
      disabled: false,
    },
    {
      icon: <Tag className="h-8 w-8 text-primary" />,
      title: "Get Pricing",
      description: "Choose from our flexible pricing packages designed for security teams of all sizes",
      cta: "Check Packages",
      href: "/pricing",
      disabled: false,
    },
  ]

  return (
    <section className="py-20 px-4 sm:px-6 lg:px-8 bg-card">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4 text-balance">Powerful Features for Modern Security</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto text-pretty">
            Everything you need to transform your surveillance system into an intelligent security platform
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <Card key={index} className="group hover:shadow-lg transition-all duration-300 border-gray-800">
              <CardHeader className="text-center pb-4">
                <div className="mx-auto mb-4 p-3 bg-primary/10 rounded-full w-fit">{feature.icon}</div>
                <CardTitle className="text-xl mb-2">{feature.title}</CardTitle>
                <CardDescription className="text-muted-foreground text-pretty">{feature.description}</CardDescription>
              </CardHeader>
              <CardContent className="text-center">
                <Link href={feature.href}>
                  <Button
                    variant="outline"
                    className="group-hover:bg-primary group-hover:text-primary-foreground transition-colors bg-transparent"
                    disabled={feature.disabled}
                  >
                    {feature.cta}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
