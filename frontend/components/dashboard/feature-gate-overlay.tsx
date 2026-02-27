"use client"

/**
 * FeatureGateOverlay
 * 
 * Wraps any dashboard widget / card. When the user's plan does NOT include the
 * required feature, the children are rendered dimmed with a semi-transparent
 * overlay + a lock icon + upgrade message.
 * 
 * Clicking the locked area opens an upgrade dialog (or navigates to /pricing).
 * 
 * Also exports:
 *  - <UpgradeDialog>   — the modal prompt to switch to Pro
 *  - <UsageTooltip>    — hover tooltip showing "X of Y uploads remaining"
 *  - <PlanBadge>       — small badge showing current plan tier
 */

import React, { useState } from "react"
import { useRouter } from "next/navigation"
import { Lock, Crown, Zap, ArrowRight, X, Sparkles, Shield, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useSubscription, DASHBOARD_GATES, type DashboardFeatureGate, type UsageEntry } from "@/contexts/subscription-context"

// ─── Upgrade Dialog ───────────────────────────────────────────────────────────
// Modal prompt shown when a user clicks on a locked feature.

interface UpgradeDialogProps {
  open: boolean
  onClose: () => void
  gate: DashboardFeatureGate
  currentPlan: string
}

export function UpgradeDialog({ open, onClose, gate, currentPlan }: UpgradeDialogProps) {
  const router = useRouter()

  if (!open) return null

  const proFeatures = [
    { icon: Shield, text: "Behavior Analysis (Fighting, Accident, Wall Climbing)" },
    { icon: Sparkles, text: "NLP Search — find moments with natural language" },
    { icon: TrendingUp, text: "Person Tracking & Re-appearance Detection" },
    { icon: Crown, text: "Image Search — find people by photo" },
    { icon: Zap, text: "Unlimited video uploads (vs 10 on Basic)" },
    { icon: Crown, text: "Custom Advanced Reports" },
  ]

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="relative w-full max-w-md mx-4 bg-card border border-border rounded-2xl shadow-2xl overflow-hidden animate-slide-up">
        {/* Header gradient */}
        <div className="relative bg-gradient-to-br from-purple-600 via-blue-600 to-cyan-500 px-6 pt-8 pb-12 text-white">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-1 rounded-full hover:bg-white/20 transition"
          >
            <X className="w-4 h-4" />
          </button>
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-white/20 rounded-xl">
              <Crown className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold">Upgrade to Pro</h2>
              <p className="text-sm text-white/80">Unlock {gate.label}</p>
            </div>
          </div>
          <p className="text-sm text-white/90 leading-relaxed">
            {gate.description}
          </p>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4 -mt-6">
          {/* Current plan indicator */}
          <div className="bg-muted/50 rounded-xl px-4 py-3 flex items-center justify-between border">
            <div>
              <p className="text-xs text-muted-foreground">Current Plan</p>
              <p className="font-semibold text-sm capitalize">
                {currentPlan === "free" ? "No Plan" : currentPlan.replace("detectifai_", "DetectifAI ")}
              </p>
            </div>
            <ArrowRight className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Recommended</p>
              <p className="font-semibold text-sm bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
                DetectifAI Pro
              </p>
            </div>
          </div>

          {/* Pro features list */}
          <div className="space-y-2">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Everything in Pro:</p>
            {proFeatures.map(({ icon: Icon, text }, i) => (
              <div key={i} className="flex items-center gap-3 text-sm">
                <Icon className="w-4 h-4 text-purple-500 flex-shrink-0" />
                <span>{text}</span>
              </div>
            ))}
          </div>

          {/* CTA */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="outline"
              className="flex-1"
              onClick={onClose}
            >
              Maybe Later
            </Button>
            <Button
              className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white border-0"
              onClick={() => {
                onClose()
                router.push("/pricing")
              }}
            >
              <Crown className="w-4 h-4 mr-2" />
              Upgrade Now
            </Button>
          </div>

          <p className="text-xs text-center text-muted-foreground">
            Starting at $49/mo · Cancel anytime
          </p>
        </div>
      </div>
    </div>
  )
}

// ─── Feature Gate Overlay ─────────────────────────────────────────────────────
// Wraps a dashboard widget. If locked → dims the content + shows overlay.

interface FeatureGateOverlayProps {
  /** The gate key from DASHBOARD_GATES (e.g. "nlp_search", "behavior_analysis") */
  gateId: string
  /** The widget content to render (always rendered, but dimmed if locked) */
  children: React.ReactNode
  /** Optional extra className on the wrapper div */
  className?: string
}

export function FeatureGateOverlay({ gateId, children, className = "" }: FeatureGateOverlayProps) {
  const { isGateUnlocked, planId, loading } = useSubscription()
  const [showUpgradeDialog, setShowUpgradeDialog] = useState(false)

  const gate = DASHBOARD_GATES[gateId]
  if (!gate) return <>{children}</>

  // While loading, render normally (no flash of locked state)
  if (loading) return <div className={className}>{children}</div>

  const unlocked = isGateUnlocked(gateId)

  if (unlocked) {
    return <div className={className}>{children}</div>
  }

  // ── LOCKED STATE ──────────────────────────────────────────────────────────
  return (
    <>
      <div
        className={`relative group cursor-pointer ${className}`}
        onClick={() => setShowUpgradeDialog(true)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && setShowUpgradeDialog(true)}
        aria-label={`${gate.label} — requires upgrade to Pro`}
      >
        {/* Dimmed content */}
        <div className="pointer-events-none select-none opacity-40 grayscale-[60%] blur-[0.5px] transition-all duration-300 group-hover:opacity-50 group-hover:grayscale-[40%]">
          {children}
        </div>

        {/* Lock overlay */}
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-background/30 backdrop-blur-[1px] rounded-xl transition-all duration-300 group-hover:bg-background/40">
          <div className="flex flex-col items-center gap-3 p-4 rounded-xl">
            <div className="p-3 bg-gradient-to-br from-purple-600/20 to-blue-600/20 border border-purple-500/30 rounded-full group-hover:scale-110 transition-transform duration-300">
              <Lock className="w-6 h-6 text-purple-400" />
            </div>
            <div className="text-center">
              <p className="font-semibold text-sm">{gate.label}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Requires <span className="text-purple-400 font-medium">Pro</span> plan
              </p>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-blue-600 text-white text-xs font-medium rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300">
              <Crown className="w-3 h-3" />
              Click to Upgrade
            </div>
          </div>
        </div>
      </div>

      <UpgradeDialog
        open={showUpgradeDialog}
        onClose={() => setShowUpgradeDialog(false)}
        gate={gate}
        currentPlan={planId}
      />
    </>
  )
}

// ─── Usage Tooltip ────────────────────────────────────────────────────────────
// Shows a hover tooltip with "X of Y uploads remaining" style info.

interface UsageTooltipProps {
  /** The limit type key e.g. "video_processing" */
  limitType: string
  /** Content to wrap (the tooltip appears on hover) */
  children: React.ReactNode
  /** Optional className */
  className?: string
}

export function UsageTooltip({ limitType, children, className = "" }: UsageTooltipProps) {
  const { getUsage, hasSubscription, planName, planId, loading } = useSubscription()
  const [showTooltip, setShowTooltip] = useState(false)

  if (loading) return <>{children}</>

  const usage = getUsage(limitType)
  const isUnlimited = planId === "detectifai_pro" && limitType === "video_processing" && usage && usage.limit >= 999999

  const formatLabel = (key: string) =>
    key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())

  return (
    <div
      className={`relative inline-block ${className}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      {children}

      {showTooltip && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-64 animate-fade-in">
          <div className="bg-popover border border-border rounded-lg shadow-xl p-3 text-sm">
            {/* Plan info */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-muted-foreground">Plan</span>
              <span className="text-xs font-semibold">
                {hasSubscription ? planName : "No Plan"}
              </span>
            </div>

            {isUnlimited ? (
              <>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium">{formatLabel(limitType)}</span>
                    <span className="text-xs font-bold text-emerald-500">
                      ♾️ Unlimited
                    </span>
                  </div>
                  <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500" style={{ width: "100%" }} />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {usage?.used || 0} uploads this billing period · No limit
                  </p>
                </div>
              </>
            ) : usage && usage.limit > 0 ? (
              <>
                {/* Usage bar */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium">{formatLabel(limitType)}</span>
                    <span className={`text-xs font-bold ${
                      usage.remaining <= 0 ? "text-red-500" :
                      usage.percentage > 80 ? "text-amber-500" :
                      "text-emerald-500"
                    }`}>
                      {usage.remaining} remaining
                    </span>
                  </div>
                  <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        usage.remaining <= 0 ? "bg-red-500" :
                        usage.percentage > 80 ? "bg-amber-500" :
                        "bg-emerald-500"
                      }`}
                      style={{ width: `${Math.min(100, usage.percentage)}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {usage.used} of {usage.limit} used this billing period
                  </p>
                </div>

                {!isUnlimited && usage.remaining <= 0 && (
                  <p className="text-xs text-red-400 mt-2 font-medium">
                    ⚠ Limit reached — upgrade your plan for more.
                  </p>
                )}
                {!isUnlimited && usage.remaining > 0 && usage.percentage > 80 && (
                  <p className="text-xs text-amber-400 mt-2">
                    ⚡ You&apos;re approaching your limit.
                  </p>
                )}
              </>
            ) : !hasSubscription ? (
              <p className="text-xs text-muted-foreground">
                Subscribe to a plan to start using {formatLabel(limitType).toLowerCase()}.
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">
                {formatLabel(limitType)} is not available on your current plan.
              </p>
            )}

            {/* Arrow */}
            <div className="absolute left-1/2 -translate-x-1/2 -bottom-1.5 w-3 h-3 bg-popover border-r border-b border-border rotate-45" />
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Plan Badge (compact) ─────────────────────────────────────────────────────
// Small badge showing the user's plan.

export function PlanBadgeCompact() {
  const { planId, planName, loading, hasSubscription } = useSubscription()

  if (loading) return <div className="h-5 w-16 bg-muted rounded-full animate-pulse" />

  if (!hasSubscription) {
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 text-[10px] font-semibold rounded-full bg-muted text-muted-foreground border">
        Free
      </span>
    )
  }

  const isPro = planId === "detectifai_pro"

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-[10px] font-semibold rounded-full ${
        isPro
          ? "bg-gradient-to-r from-purple-600 to-blue-600 text-white"
          : "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800"
      }`}
    >
      {isPro && <Crown className="w-3 h-3" />}
      {planName}
    </span>
  )
}

// ─── Upload Limit Indicator ───────────────────────────────────────────────────
// Shows inline "X / Y uploads" near the upload button with color coding.

export function UploadLimitIndicator() {
  const { getUsage, hasSubscription, planId, loading } = useSubscription()

  if (loading) return null

  const usage = getUsage("video_processing")

  if (!hasSubscription || !usage) {
    return (
      <span className="text-[10px] text-muted-foreground">
        No plan active
      </span>
    )
  }

  // Pro plan has unlimited uploads
  if (planId === "detectifai_pro" && usage.limit >= 999999) {
    return (
      <span className="text-[10px] font-medium text-emerald-500">
        ♾️ Unlimited uploads
      </span>
    )
  }

  const color = usage.remaining <= 0 ? "text-red-500" :
    usage.percentage > 80 ? "text-amber-500" :
    "text-emerald-500"

  return (
    <span className={`text-[10px] font-medium ${color}`}>
      {usage.remaining}/{usage.limit} uploads left
    </span>
  )
}
