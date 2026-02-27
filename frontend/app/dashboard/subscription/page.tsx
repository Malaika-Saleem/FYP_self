'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { CheckCircle2, XCircle, Loader2, CreditCard, Calendar, AlertCircle } from 'lucide-react';

interface SubscriptionData {
  has_subscription: boolean;
  subscription_id?: string;
  plan_name?: string;
  billing_period?: string;
  status?: string;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
  features?: string[];
}

export default function SubscriptionPage() {
  const searchParams = useSearchParams();
  const { data: session } = useSession();
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState<SubscriptionData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const success = searchParams.get('success');
  const sessionId = searchParams.get('session_id');

  useEffect(() => {
    const fetchSubscription = async () => {
      if (!session?.user?.id) {
        setLoading(false);
        return;
      }

      try {
        // If coming from successful checkout, sync from Stripe first
        if (success && sessionId) {
          await fetch(
            `${process.env.NEXT_PUBLIC_API_URL}/api/subscriptions/sync-from-stripe`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                user_id: session.user.id,
                user_email: session.user.email,
                session_id: sessionId,
              }),
            }
          );
        }

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/subscriptions/status?user_id=${session.user.id}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch subscription');
        }

        const data = await response.json();
        
        if (data.success) {
          setSubscription(data);
        } else {
          setError(data.error || 'Failed to load subscription');
        }
      } catch (err) {
        console.error('Error fetching subscription:', err);
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    // Add small delay if coming from success to allow sync to complete
    if (success && sessionId) {
      setTimeout(fetchSubscription, 1000);
    } else {
      fetchSubscription();
    }
  }, [session?.user?.id, success, sessionId]);

  const handleManageSubscription = async () => {
    if (!session?.user?.id || !session?.user?.email) return;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/subscriptions/create-portal-session`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: session.user.id,
            user_email: session.user.email,
          }),
        }
      );

      const data = await response.json();

      if (data.success && data.url) {
        window.location.href = data.url;
      } else {
        alert('Failed to open billing portal');
      }
    } catch (error) {
      console.error('Error opening portal:', error);
      alert('Failed to open billing portal');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">Loading your subscription...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Success Message */}
        {success === 'true' && (
          <div className="mb-8 bg-green-50 dark:bg-green-900/20 border-2 border-green-500 rounded-lg p-6">
            <div className="flex items-start">
              <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400 mt-1 mr-3 flex-shrink-0" />
              <div>
                <h2 className="text-xl font-bold text-green-900 dark:text-green-100 mb-2">
                  🎉 Subscription Activated!
                </h2>
                <p className="text-green-700 dark:text-green-300">
                  Your payment was successful. You now have full access to your plan features.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-8 bg-red-50 dark:bg-red-900/20 border-2 border-red-500 rounded-lg p-6">
            <div className="flex items-start">
              <XCircle className="w-6 h-6 text-red-600 dark:text-red-400 mt-1 mr-3 flex-shrink-0" />
              <div>
                <h2 className="text-xl font-bold text-red-900 dark:text-red-100 mb-2">
                  Error Loading Subscription
                </h2>
                <p className="text-red-700 dark:text-red-300">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Subscription Details */}
        {subscription?.has_subscription ? (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 text-white">
              <h1 className="text-3xl font-bold mb-2">Your Subscription</h1>
              <p className="text-blue-100">Manage your plan and billing</p>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Plan Info */}
              <div className="border-b border-gray-200 dark:border-gray-700 pb-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                      {subscription.plan_name}
                    </h2>
                    <p className="text-gray-600 dark:text-gray-400 capitalize">
                      {subscription.billing_period} billing
                    </p>
                  </div>
                  <div className="text-right">
                    <div className={`inline-block px-4 py-2 rounded-full text-sm font-semibold ${
                      subscription.status === 'active'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                        : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                    }`}>
                      {subscription.status?.toUpperCase()}
                    </div>
                  </div>
                </div>

                {subscription.cancel_at_period_end && (
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded-lg p-4 flex items-start">
                    <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5 mr-3 flex-shrink-0" />
                    <div>
                      <p className="font-semibold text-yellow-900 dark:text-yellow-100">
                        Subscription Ending
                      </p>
                      <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                        Your subscription will end on{' '}
                        {subscription.current_period_end &&
                          new Date(subscription.current_period_end).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Billing Info */}
              <div className="grid md:grid-cols-2 gap-6">
                <div className="flex items-start space-x-3">
                  <Calendar className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-1" />
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-white">Current Period</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {subscription.current_period_start &&
                        new Date(subscription.current_period_start).toLocaleDateString()}{' '}
                      -{' '}
                      {subscription.current_period_end &&
                        new Date(subscription.current_period_end).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-3">
                  <CreditCard className="w-5 h-5 text-blue-600 dark:text-blue-400 mt-1" />
                  <div>
                    <p className="font-semibold text-gray-900 dark:text-white">Next Billing Date</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {subscription.current_period_end &&
                        new Date(subscription.current_period_end).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>

              {/* Features */}
              {subscription.features && subscription.features.length > 0 && (
                <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-3">
                    Included Features
                  </h3>
                  <div className="grid md:grid-cols-2 gap-2">
                    {subscription.features.map((feature, index) => (
                      <div key={index} className="flex items-center text-sm text-gray-700 dark:text-gray-300">
                        <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 mr-2" />
                        {feature.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-6 flex flex-col sm:flex-row gap-4">
                <button
                  onClick={handleManageSubscription}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg transition"
                >
                  Manage Subscription
                </button>
                <Link
                  href="/dashboard"
                  className="flex-1 bg-gray-200 hover:bg-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white font-semibold py-3 px-6 rounded-lg transition text-center"
                >
                  Go to Dashboard
                </Link>
              </div>

              <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
                You can update your payment method, view invoices, or cancel your subscription in the
                billing portal.
              </p>
            </div>
          </div>
        ) : (
          // No Subscription
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8 text-center">
            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-4">
              <CreditCard className="w-8 h-8 text-gray-400" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
              No Active Subscription
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Subscribe to a plan to unlock powerful AI security features.
            </p>
            <Link
              href="/pricing"
              className="inline-block bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold py-3 px-8 rounded-lg hover:from-blue-700 hover:to-purple-700 transition"
            >
              View Plans
            </Link>
          </div>
        )}

        {/* Info Box */}
        <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">
            Need Help?
          </h3>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Questions about your subscription? Contact support or visit our{' '}
            <Link href="/pricing" className="underline hover:text-blue-900 dark:hover:text-blue-100">
              pricing page
            </Link>{' '}
            to compare plans.
          </p>
        </div>
      </div>
    </div>
  );
}
