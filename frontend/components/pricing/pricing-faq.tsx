"use client"

import { Button } from "@/components/ui/button"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { ChevronDown, ChevronUp } from "lucide-react"

export function PricingFAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  const faqs = [
    {
      question: "What's included in the 7-day free trial?",
      answer:
        "The free trial includes full access to DetectifAI Pro features, including unlimited camera feeds, real-time AI search, and advanced behavioral detection. No credit card required.",
    },
    {
      question: "Can I upgrade or downgrade my plan anytime?",
      answer:
        "Yes, you can change your plan at any time. Upgrades take effect immediately, while downgrades will take effect at the end of your current billing cycle.",
    },
    {
      question: "How does the AI detection work?",
      answer:
        "Our AI uses advanced computer vision and machine learning models to analyze video feeds in real-time, detecting suspicious behaviors, identifying objects, and providing instant alerts based on your configured parameters.",
    },
    {
      question: "Is my surveillance data secure?",
      answer:
        "Absolutely. We use enterprise-grade encryption, secure cloud infrastructure, and comply with industry security standards. Your video data is processed securely and never shared with third parties.",
    },
    {
      question: "What camera systems are supported?",
      answer:
        "DetectifAI supports most modern IP cameras and CCTV systems through standard protocols (RTSP, ONVIF). We also provide integration guides for popular camera brands.",
    },
    {
      question: "Do you offer custom enterprise solutions?",
      answer:
        "Yes, we offer custom enterprise packages for large organizations with specific requirements. Contact our sales team to discuss your needs and get a tailored solution.",
    },
  ]

  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold mb-4">Frequently Asked Questions</h2>
        <p className="text-muted-foreground text-pretty">
          Everything you need to know about DetectifAI pricing and features
        </p>
      </div>

      <div className="space-y-4">
        {faqs.map((faq, index) => (
          <Card key={index} className="border-border">
            <CardContent className="p-0">
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full p-6 text-left flex items-center justify-between hover:bg-muted/50 transition-colors"
              >
                <span className="font-medium text-pretty">{faq.question}</span>
                {openIndex === index ? (
                  <ChevronUp className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-muted-foreground flex-shrink-0" />
                )}
              </button>

              {openIndex === index && (
                <div className="px-6 pb-6">
                  <p className="text-muted-foreground text-pretty">{faq.answer}</p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Contact Section */}
      <div className="mt-12 text-center bg-card rounded-lg p-8 border border-border">
        <h3 className="text-xl font-bold mb-2">Still have questions?</h3>
        <p className="text-muted-foreground mb-4">Our security experts are here to help you choose the right plan</p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button variant="outline" className="bg-transparent">
            Contact Sales
          </Button>
          <Button variant="outline" className="bg-transparent">
            Schedule Demo
          </Button>
        </div>
      </div>
    </div>
  )
}
