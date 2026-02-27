"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { FileText, Download, ExternalLink, Loader2, CheckCircle2 } from "lucide-react"
import { useState, useEffect } from "react"

export function ReportWidget({
  videoId,
  processingComplete = false
}: {
  videoId?: string
  processingComplete?: boolean
}) {
  const [generating, setGenerating] = useState(false)
  const [reportUrls, setReportUrls] = useState<{ pdf: string | null; html: string } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reportGenerated, setReportGenerated] = useState(false)

  // Reset report state when video changes
  useEffect(() => {
    setReportUrls(null)
    setReportGenerated(false)
    setError(null)
    setGenerating(false)
  }, [videoId])

  const canGenerate = Boolean(videoId && processingComplete)
  const isDisabled = !canGenerate || generating

  const handleGenerateReport = async () => {
    if (!videoId) {
      setError("Please upload a video first.")
      return
    }
    if (!processingComplete) {
      setError("Please wait for video analysis to complete before generating a report.")
      return
    }

    setGenerating(true)
    setError(null)
    setReportUrls(null)
    setReportGenerated(false)

    try {
      console.log('🔄 Generating report for video:', videoId)
      const response = await fetch('/api/video/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: videoId })
      })

      const data = await response.json().catch(() => ({}))
      console.log('📊 Report generation response:', data)

      if (response.ok && data.success) {
        setReportUrls({
          pdf: data.pdf_url || null,
          html: data.html_url || ''
        })
        setReportGenerated(true)
        console.log('✅ Report generated successfully:', data)
      } else {
        const errorMsg = data.error || data.message || `Failed to generate report (${response.status})`
        setError(errorMsg)
        console.error('❌ Report generation failed:', errorMsg)
      }
    } catch (err) {
      console.error("❌ Report generation error:", err)
      setError(err instanceof Error ? err.message : "Failed to generate report")
    } finally {
      setGenerating(false)
    }
  }

  const handleDownloadPDF = () => {
    if (reportUrls?.pdf) {
      // Open presigned URL directly - it's already a full MinIO URL
      window.open(reportUrls.pdf, '_blank')
    }
  }

  const handleViewHTML = () => {
    if (reportUrls?.html) {
      // Open presigned URL directly - it's already a full MinIO URL
      window.open(reportUrls.html, '_blank')
    }
  }

  return (
    <Card className="border-border">
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <FileText className="h-5 w-5 text-primary" />
          <span>Generate Report</span>
        </CardTitle>
        <CardDescription>
          {processingComplete
            ? "Create a professional forensic report from this video's analysis results."
            : "Upload a video and wait for analysis to finish, then generate a report."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {reportGenerated && reportUrls && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-4 space-y-3">
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircle2 className="h-5 w-5" />
              <h4 className="font-semibold text-sm">Report Generated Successfully!</h4>
            </div>
            <p className="text-xs text-green-600">
              Your forensic report is ready. You can view it online or download the PDF version.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                variant="default"
                size="sm"
                onClick={handleViewHTML}
                className="gap-2 bg-green-600 hover:bg-green-700"
              >
                <ExternalLink className="h-4 w-4" />
                View HTML Report
              </Button>
              {reportUrls.pdf && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDownloadPDF}
                  className="gap-2 border-green-600 text-green-700 hover:bg-green-50"
                >
                  <Download className="h-4 w-4" />
                  Download PDF
                </Button>
              )}
            </div>
          </div>
        )}

        <Button
          className="w-full"
          onClick={handleGenerateReport}
          disabled={isDisabled}
        >
          {generating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating report…
            </>
          ) : (
            <>
              <FileText className="mr-2 h-4 w-4" />
              Generate Report
            </>
          )}
        </Button>

        {!processingComplete && videoId && (
          <p className="text-xs text-muted-foreground">
            ⏳ Report will be available after video analysis completes.
          </p>
        )}

        {!videoId && (
          <p className="text-xs text-muted-foreground">
            📹 Upload a video to get started.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
