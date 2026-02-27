/**
 * useFeatureAccess Hook
 * 
 * Frontend hook to check feature access and usage limits
 */

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';

interface FeatureAccess {
  hasAccess: boolean;
  loading: boolean;
  currentPlan: string;
  error?: string;
}

interface UsageSummary {
  has_subscription: boolean;
  plan: string;
  plan_name: string;
  status: string;
  usage: {
    [key: string]: {
      used: number;
      limit: number;
      remaining: number;
      percentage: number;
    };
  };
  limits: {
    [key: string]: number;
  };
}

/**
 * Check if user has access to a specific feature
 */
export function useFeatureAccess(featureName: string): FeatureAccess {
  const { data: session } = useSession();
  const [featureAccess, setFeatureAccess] = useState<FeatureAccess>({
    hasAccess: false,
    loading: true,
    currentPlan: 'free',
  });

  useEffect(() => {
    const checkFeatureAccess = async () => {
      if (!session?.user?.id) {
        setFeatureAccess({
          hasAccess: false,
          loading: false,
          currentPlan: 'free',
          error: 'Not authenticated',
        });
        return;
      }

      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/feature/check?user_id=${session.user.id}&feature=${featureName}`
        );

        if (!response.ok) {
          throw new Error('Failed to check feature access');
        }

        const data = await response.json();

        setFeatureAccess({
          hasAccess: data.has_access,
          loading: false,
          currentPlan: data.current_plan,
        });
      } catch (error) {
        setFeatureAccess({
          hasAccess: false,
          loading: false,
          currentPlan: 'free',
          error: error instanceof Error ? error.message : 'Unknown error',
        });
      }
    };

    checkFeatureAccess();
  }, [session?.user?.id, featureName]);

  return featureAccess;
}

/**
 * Get complete usage summary
 */
export function useUsageSummary() {
  const { data: session } = useSession();
  const [usageSummary, setUsageSummary] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUsageSummary = async () => {
      if (!session?.user?.id) {
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/usage/summary?user_id=${session.user.id}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch usage summary');
        }

        const data = await response.json();
        setUsageSummary(data.usage);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchUsageSummary();
  }, [session?.user?.id]);

  return { usageSummary, loading, error };
}

/**
 * Feature Gate Component
 * 
 * Wraps content that should only be visible with specific feature access
 * 
 * @example
 * <FeatureGate feature="nlp_search" fallback={<UpgradePrompt />}>
 *   <NLPSearchInterface />
 * </FeatureGate>
 */
export function FeatureGate({
  feature,
  children,
  fallback,
}: {
  feature: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { hasAccess, loading, currentPlan } = useFeatureAccess(feature);

  if (loading) {
    return <div className="animate-pulse">Loading...</div>;
  }

  if (!hasAccess) {
    return (
      fallback || (
        <div className="p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold mb-2">Upgrade Required</h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            This feature is not available in your {currentPlan} plan.
          </p>
          <a
            href="/pricing"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition"
          >
            View Plans
          </a>
        </div>
      )
    );
  }

  return <>{children}</>;
}

/**
 * Usage Meter Component
 * 
 * Display usage for a specific limit type
 * 
 * @example
 * <UsageMeter limitType="video_processing" />
 */
export function UsageMeter({ limitType }: { limitType: string }) {
  const { usageSummary, loading } = useUsageSummary();

  if (loading) {
    return <div className="h-4 bg-gray-200 rounded animate-pulse" />;
  }

  if (!usageSummary?.usage?.[limitType]) {
    return null;
  }

  const usage = usageSummary.usage[limitType];
  const percentage = Math.min(100, usage.percentage);
  const isNearLimit = percentage > 80;
  const isAtLimit = percentage >= 100;

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="font-medium">
          {limitType.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
        </span>
        <span className={isAtLimit ? 'text-red-600' : isNearLimit ? 'text-yellow-600' : 'text-gray-600'}>
          {usage.used} / {usage.limit}
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`h-2 rounded-full transition-all ${
            isAtLimit ? 'bg-red-600' : isNearLimit ? 'bg-yellow-500' : 'bg-blue-600'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-xs text-gray-500">
        {usage.remaining} remaining this billing period
      </div>
    </div>
  );
}

/**
 * Plan Badge Component
 * 
 * Display user's current plan
 */
export function PlanBadge() {
  const { usageSummary, loading } = useUsageSummary();

  if (loading) {
    return <div className="h-6 w-20 bg-gray-200 rounded animate-pulse" />;
  }

  if (!usageSummary?.has_subscription) {
    return (
      <span className="px-3 py-1 text-xs font-semibold rounded-full bg-gray-200 text-gray-700">
        Free
      </span>
    );
  }

  const isPro = usageSummary.plan === 'detectifai_pro';

  return (
    <span
      className={`px-3 py-1 text-xs font-semibold rounded-full ${
        isPro
          ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
          : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
      }`}
    >
      {usageSummary.plan_name}
    </span>
  );
}

/**
 * Upgrade Prompt Component
 * 
 * Show upgrade CTA for feature access
 */
export function UpgradePrompt({ feature }: { feature: string }) {
  return (
    <div className="p-8 bg-gradient-to-br from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-900 rounded-lg border-2 border-blue-200 dark:border-blue-800 text-center">
      <div className="text-4xl mb-4">🚀</div>
      <h3 className="text-xl font-bold mb-2">Unlock {feature.replace(/_/g, ' ')}</h3>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        Upgrade to Pro to access advanced features and enhanced capabilities.
      </p>
      <a
        href="/pricing"
        className="inline-block px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-700 hover:to-purple-700 transition shadow-lg"
      >
        Upgrade to Pro
      </a>
    </div>
  );
}
