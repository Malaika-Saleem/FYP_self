"use client"

/**
 * SubscriptionContext — Single source of truth for user's plan, features & usage.
 * 
 * Provides:
 *  - Plan tier (free / basic / pro)
 *  - Feature access checks
 *  - Usage counters (video uploads remaining, NLP searches, etc.)
 *  - A `refreshSubscription()` helper for on-demand reload
 * 
 * Wrap the app (or dashboard layout) with <SubscriptionProvider> and then
 * call `useSubscription()` from any child component.
 */

import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react"
import { useSession } from "next-auth/react"

// ─── Plan Feature Map ─────────────────────────────────────────────────────────
// Authoritative client-side mirror of the plan tiers stored in MongoDB.
// Used ONLY for instant UI rendering — the backend remains the enforcer.

export type PlanTier = "free" | "detectifai_basic" | "detectifai_pro" | "dev_mode"

export interface PlanFeatureConfig {
  label: string                // Human-readable plan name
  tier: number                 // 0 = free, 1 = basic, 2 = pro
  features: string[]           // Feature keys included
  limits: Record<string, number>
}

export const PLAN_CONFIGS: Record<PlanTier, PlanFeatureConfig> = {
  free: {
    label: "Free",
    tier: 0,
    features: [],
    limits: { video_processing: 0, nlp_searches: 0, image_searches: 0, concurrent_streams: 0, history_retention_days: 0 },
  },
  detectifai_basic: {
    label: "DetectifAI Basic",
    tier: 1,
    features: [
      "single_video", "object_detection", "face_recognition",
      "event_history_7day", "dashboard", "basic_reports", "video_clips",
    ],
    limits: { video_processing: 10, nlp_searches: 0, image_searches: 0, concurrent_streams: 1, history_retention_days: 7 },
  },
  detectifai_pro: {
    label: "DetectifAI Pro",
    tier: 2,
    features: [
      "single_video", "object_detection", "face_recognition",
      "event_history_7day", "dashboard", "basic_reports", "video_clips",
      // Pro-only ↓
      "behavior_analysis", "nlp_search", "person_tracking",
      "image_search", "custom_reports", "priority_queue", "event_history_30day",
    ],
    limits: { video_processing: 999999, nlp_searches: 200, image_searches: 100, concurrent_streams: 1, history_retention_days: 30 },
  },
  dev_mode: {
    label: "Development Mode",
    tier: 99,
    features: ["*"],           // wildcard — everything allowed
    limits: { video_processing: 999, nlp_searches: 999, image_searches: 999, concurrent_streams: 10, history_retention_days: 365 },
  },
}

// ─── Dashboard Feature ↔ Plan mapping ─────────────────────────────────────────
// Each dashboard widget / action is mapped to a required feature key + minimum plan tier.
// Used by <FeatureGateOverlay> to dim and show "Upgrade to Pro" on locked widgets.

export interface DashboardFeatureGate {
  featureKey: string           // e.g. "nlp_search"
  requiredPlan: PlanTier       // minimum plan to unlock
  label: string                // human label shown in upgrade prompt
  description: string          // short explanation of what they're missing
}

export const DASHBOARD_GATES: Record<string, DashboardFeatureGate> = {
  nlp_search: {
    featureKey: "nlp_search",
    requiredPlan: "detectifai_pro",
    label: "NLP Search",
    description: "Search surveillance footage using natural language queries.",
  },
  image_search: {
    featureKey: "image_search",
    requiredPlan: "detectifai_pro",
    label: "Image Search",
    description: "Find people by uploading a reference photo.",
  },
  behavior_analysis: {
    featureKey: "behavior_analysis",
    requiredPlan: "detectifai_pro",
    label: "Behavior Analysis",
    description: "Detect suspicious behaviors like fighting, wall climbing, and accidents.",
  },
  person_tracking: {
    featureKey: "person_tracking",
    requiredPlan: "detectifai_pro",
    label: "Person Tracking",
    description: "Track re-appearances of suspicious persons across cameras.",
  },
  custom_reports: {
    featureKey: "custom_reports",
    requiredPlan: "detectifai_pro",
    label: "Custom Reports",
    description: "Generate advanced, customizable security reports.",
  },
  video_upload: {
    featureKey: "single_video",
    requiredPlan: "detectifai_basic",
    label: "Video Upload & Processing",
    description: "Upload and analyze surveillance videos with AI detection.",
  },
  live_stream: {
    featureKey: "single_video",
    requiredPlan: "detectifai_basic",
    label: "Live Stream",
    description: "Monitor live camera feeds with real-time AI detection.",
  },
  report_generation: {
    featureKey: "basic_reports",
    requiredPlan: "detectifai_basic",
    label: "Report Generation",
    description: "Generate security reports from video analysis.",
  },
}

// ─── Usage entry shape (mirrors Flask /api/usage/summary response) ────────────

export interface UsageEntry {
  used: number
  limit: number
  remaining: number
  percentage: number
}

export interface SubscriptionState {
  /** True while the first fetch is in progress */
  loading: boolean
  /** The plan id — "free" if no subscription */
  planId: PlanTier
  /** Human-readable plan name */
  planName: string
  /** Numeric tier (0 = free, 1 = basic, 2 = pro) */
  tier: number
  /** Whether the user has an active paid subscription */
  hasSubscription: boolean
  /** Subscription status (active / past_due / canceled / trialing) */
  status: string
  /** Feature list from backend (string[]) */
  features: string[]
  /** Usage counters keyed by limit type */
  usage: Record<string, UsageEntry>
  /** Raw limit numbers keyed by limit type */
  limits: Record<string, number>
  /** Period end date (for display) */
  periodEnd: string | null
  /** True if the plan will cancel at period end */
  cancelAtPeriodEnd: boolean
  /** Check if user has access to a specific feature key */
  hasFeature: (featureKey: string) => boolean
  /** Check if a dashboard gate is unlocked */
  isGateUnlocked: (gateId: string) => boolean
  /** Get usage for a limit type (or null if not applicable) */
  getUsage: (limitType: string) => UsageEntry | null
  /** Force-refresh subscription data from backend */
  refreshSubscription: () => Promise<void>
}

const DEFAULT_STATE: SubscriptionState = {
  loading: true,
  planId: "free",
  planName: "Free",
  tier: 0,
  hasSubscription: false,
  status: "none",
  features: [],
  usage: {},
  limits: {},
  periodEnd: null,
  cancelAtPeriodEnd: false,
  hasFeature: () => false,
  isGateUnlocked: () => false,
  getUsage: () => null,
  refreshSubscription: async () => {},
}

const SubscriptionContext = createContext<SubscriptionState>(DEFAULT_STATE)

// ─── Provider ─────────────────────────────────────────────────────────────────

export function SubscriptionProvider({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession()
  const [loading, setLoading] = useState(true)
  const [planId, setPlanId] = useState<PlanTier>("free")
  const [planName, setPlanName] = useState("Free")
  const [hasSubscription, setHasSubscription] = useState(false)
  const [status, setStatus] = useState("none")
  const [features, setFeatures] = useState<string[]>([])
  const [usage, setUsage] = useState<Record<string, UsageEntry>>({})
  const [limits, setLimits] = useState<Record<string, number>>({})
  const [periodEnd, setPeriodEnd] = useState<string | null>(null)
  const [cancelAtPeriodEnd, setCancelAtPeriodEnd] = useState(false)

  const flaskUrl = typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_FLASK_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"
    : process.env.NEXT_PUBLIC_FLASK_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:5000"

  // ── Fetch both subscription status + usage in parallel ──────────────────────
  const fetchSubscription = useCallback(async () => {
    const userId = (session?.user as any)?.id
    if (!userId) {
      setLoading(false)
      return
    }

    try {
      const [statusRes, usageRes] = await Promise.allSettled([
        fetch(`${flaskUrl}/api/subscriptions/status?user_id=${userId}`),
        fetch(`${flaskUrl}/api/usage/summary?user_id=${userId}`),
      ])

      // Process subscription status
      if (statusRes.status === "fulfilled" && statusRes.value.ok) {
        const data = await statusRes.value.json()
        if (data.success && data.has_subscription) {
          const pid = (data.plan_id || "free") as PlanTier
          setPlanId(pid)
          setPlanName(data.plan_name || PLAN_CONFIGS[pid]?.label || "Unknown")
          setHasSubscription(true)
          setStatus(data.status || "active")
          // Ensure features is always an array
          const feats = Array.isArray(data.features) ? data.features
            : typeof data.features === "string" ? data.features.split(",").map((s: string) => s.trim())
            : PLAN_CONFIGS[pid]?.features || []
          setFeatures(feats)
          setPeriodEnd(data.current_period_end || null)
          setCancelAtPeriodEnd(data.cancel_at_period_end || false)
        } else if (data.success && data.current_plan === "dev_mode") {
          // Dev mode — everything open
          setPlanId("dev_mode")
          setPlanName("Development Mode")
          setHasSubscription(true)
          setStatus("active")
          setFeatures(["*"])
        } else {
          // No subscription
          setPlanId("free")
          setPlanName("Free")
          setHasSubscription(false)
          setStatus("none")
          setFeatures([])
        }
      }

      // Process usage summary
      if (usageRes.status === "fulfilled" && usageRes.value.ok) {
        const data = await usageRes.value.json()
        if (data.success && data.usage) {
          const u = data.usage
          if (u.usage) setUsage(u.usage)
          if (u.limits) setLimits(u.limits)
          // If status response failed but usage returned plan info, use it
          if (u.plan && !hasSubscription) {
            const pid = (u.plan || "free") as PlanTier
            setPlanId(pid)
            setPlanName(u.plan_name || PLAN_CONFIGS[pid]?.label || "Unknown")
            setHasSubscription(u.has_subscription || false)
            setStatus(u.status || "none")
          }
        }
      }
    } catch (err) {
      console.error("Failed to fetch subscription data:", err)
    } finally {
      setLoading(false)
    }
  }, [(session?.user as any)?.id, flaskUrl])

  useEffect(() => {
    fetchSubscription()
  }, [fetchSubscription])

  // ── Derived helpers ─────────────────────────────────────────────────────────

  const tier = useMemo(() => PLAN_CONFIGS[planId]?.tier ?? 0, [planId])

  const hasFeature = useCallback(
    (featureKey: string) => {
      if (planId === "dev_mode" || features.includes("*")) return true
      if (!hasSubscription) return false
      // Check features array from backend first, fallback to config
      if (features.includes(featureKey)) return true
      const cfg = PLAN_CONFIGS[planId]
      return cfg?.features.includes(featureKey) ?? false
    },
    [planId, features, hasSubscription],
  )

  const isGateUnlocked = useCallback(
    (gateId: string) => {
      const gate = DASHBOARD_GATES[gateId]
      if (!gate) return true // Unknown gate → don't block
      return hasFeature(gate.featureKey)
    },
    [hasFeature],
  )

  const getUsage = useCallback(
    (limitType: string): UsageEntry | null => {
      if (usage[limitType]) return usage[limitType]
      // Construct from limits map + assume 0 used if not tracked
      const lim = limits[limitType]
      if (lim !== undefined) {
        return { used: 0, limit: lim, remaining: lim, percentage: 0 }
      }
      return null
    },
    [usage, limits],
  )

  const value = useMemo<SubscriptionState>(
    () => ({
      loading,
      planId,
      planName,
      tier,
      hasSubscription,
      status,
      features,
      usage,
      limits,
      periodEnd,
      cancelAtPeriodEnd,
      hasFeature,
      isGateUnlocked,
      getUsage,
      refreshSubscription: fetchSubscription,
    }),
    [loading, planId, planName, tier, hasSubscription, status, features, usage, limits, periodEnd, cancelAtPeriodEnd, hasFeature, isGateUnlocked, getUsage, fetchSubscription],
  )

  return (
    <SubscriptionContext.Provider value={value}>
      {children}
    </SubscriptionContext.Provider>
  )
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useSubscription() {
  return useContext(SubscriptionContext)
}
