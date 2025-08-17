import React, { useState } from 'react';
import { usePlans, useBillingInfo, useDunningState, useCreateCheckout, formatPrice } from '../../api/paymentsClient';
import { PlanCard } from '../../components/billing/PlanCard';
import { DunningBanner } from '../../components/billing/DunningBanner';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Switch } from '../../components/ui/Switch';
import { Users, Star, HelpCircle } from '../../components/ui/Icons';

export const Plans: React.FC = () => {
  const [studentCount, setStudentCount] = useState(1);
  const [billingInterval, setBillingInterval] = useState<'monthly' | 'yearly'>('monthly');
  const [showFAQ, setShowFAQ] = useState(false);

  // API hooks
  const { data: plans = [] } = usePlans();
  const { data: billingInfo } = useBillingInfo();
  const { data: dunningState } = useDunningState();
  const createCheckout = useCreateCheckout();

  // Filter plans by interval and add discount pricing
  const filteredPlans = plans.filter(plan => 
    plan.interval === (billingInterval === 'monthly' ? 'month' : 'year')
  );
  const plansWithDiscounts = filteredPlans.map(plan => ({
    ...plan,
    originalPrice: studentCount > 1 ? plan.price : undefined,
    price: studentCount > 1 ? plan.price * 0.85 : plan.price // 15% sibling discount
  }));

  const handlePlanSelect = async (planId: string) => {
    try {
      const checkoutData = await createCheckout.mutateAsync({
        planId,
        studentCount
      });

      // Redirect to Stripe checkout
      window.location.href = checkoutData.url;
    } catch (error) {
      console.error('Failed to create checkout session:', error);
    }
  };

  const handleUpdatePayment = () => {
    // Navigate to billing management
    window.location.href = '/billing/manage';
  };

  const handleContactSupport = () => {
    // Open support chat or email
    window.open('mailto:support@aivo.com', '_blank');
  };

  const yearlyDiscount = 20; // 20% discount for yearly billing

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Choose Your Plan</h1>
            <p className="text-lg text-gray-600 mb-6">
              Unlock the full potential of AI-powered learning for your students
            </p>

            {/* Billing Toggle */}
            <div className="flex items-center justify-center gap-4 mb-6">
              <span className={`text-sm ${billingInterval === 'monthly' ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                Monthly
              </span>
              <Switch
                checked={billingInterval === 'yearly'}
                onCheckedChange={(checked: boolean) => setBillingInterval(checked ? 'yearly' : 'monthly')}
              />
              <span className={`text-sm ${billingInterval === 'yearly' ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                Yearly
              </span>
              {billingInterval === 'yearly' && (
                <Badge className="bg-green-100 text-green-700 text-xs ml-2">
                  Save {yearlyDiscount}%
                </Badge>
              )}
            </div>

            {/* Student Count Selector */}
            <div className="flex items-center justify-center gap-4">
              <Users className="w-5 h-5 text-gray-500" />
              <span className="text-sm text-gray-600">Number of students:</span>
              <select
                value={studentCount}
                onChange={(e) => setStudentCount(Number(e.target.value))}
                className="px-3 py-1 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(num => (
                  <option key={num} value={num}>{num}</option>
                ))}
              </select>
              {studentCount > 1 && (
                <Badge className="bg-blue-100 text-blue-700 text-xs">
                  15% sibling discount applied
                </Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Dunning Banner */}
        {dunningState && (
          <div className="mb-6">
            <DunningBanner
              dunningState={dunningState}
              onUpdatePayment={handleUpdatePayment}
              onRetryPayment={handleUpdatePayment}
              onContactSupport={handleContactSupport}
            />
          </div>
        )}

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {plansWithDiscounts.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              isCurrentPlan={billingInfo?.subscription?.planId === plan.id}
              isLoading={createCheckout.isPending}
              onSelect={handlePlanSelect}
              studentCount={studentCount}
              showDiscount={studentCount > 1}
            />
          ))}
        </div>

        {/* Features Comparison */}
        <Card className="mb-12">
          <CardHeader>
            <CardTitle className="text-center">Feature Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">Features</th>
                    {filteredPlans.map(plan => (
                      <th key={plan.id} className="text-center py-3 px-4 min-w-32">
                        <div className="font-semibold">{plan.name}</div>
                        <div className="text-xs text-gray-500 mt-1">
                          {formatPrice(plan.price, plan.currency)}/{plan.interval}
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">AI Tutoring Sessions</td>
                    <td className="text-center py-3 px-4">5/month</td>
                    <td className="text-center py-3 px-4">Unlimited</td>
                    <td className="text-center py-3 px-4">Unlimited + Priority</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">Progress Analytics</td>
                    <td className="text-center py-3 px-4">Basic</td>
                    <td className="text-center py-3 px-4">Advanced</td>
                    <td className="text-center py-3 px-4">Advanced + Custom Reports</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">Parent Dashboard</td>
                    <td className="text-center py-3 px-4">✓</td>
                    <td className="text-center py-3 px-4">✓</td>
                    <td className="text-center py-3 px-4">✓</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">District Analytics</td>
                    <td className="text-center py-3 px-4">-</td>
                    <td className="text-center py-3 px-4">-</td>
                    <td className="text-center py-3 px-4">✓</td>
                  </tr>
                  <tr className="border-b">
                    <td className="py-3 px-4 font-medium">Priority Support</td>
                    <td className="text-center py-3 px-4">-</td>
                    <td className="text-center py-3 px-4">✓</td>
                    <td className="text-center py-3 px-4">✓ + Dedicated Rep</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Testimonials */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-1 mb-3">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                ))}
              </div>
              <p className="text-gray-700 mb-4">
                "My daughter's math skills improved dramatically in just 3 months. The AI tutor adapts perfectly to her learning style."
              </p>
              <div className="text-sm text-gray-600">
                — Sarah M., Parent
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center gap-1 mb-3">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
                ))}
              </div>
              <p className="text-gray-700 mb-4">
                "The analytics help me track all my students' progress in real-time. It's transformed how I teach."
              </p>
              <div className="text-sm text-gray-600">
                — Jennifer L., Teacher
              </div>
            </CardContent>
          </Card>
        </div>

        {/* FAQ Section */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Frequently Asked Questions</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowFAQ(!showFAQ)}
              >
                <HelpCircle className="w-4 h-4 mr-1" />
                {showFAQ ? 'Hide' : 'Show'} FAQ
              </Button>
            </div>
          </CardHeader>
          {showFAQ && (
            <CardContent>
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Can I change plans anytime?</h4>
                  <p className="text-sm text-gray-600">
                    Yes, you can upgrade or downgrade your plan at any time. Changes take effect immediately, and we'll prorate the billing.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">What happens during the free trial?</h4>
                  <p className="text-sm text-gray-600">
                    You get full access to all features for 14 days. No credit card required. Cancel anytime during the trial period.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">Is there a sibling discount?</h4>
                  <p className="text-sm text-gray-600">
                    Yes! You get 15% off when you have 2 or more students on the same account.
                  </p>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 mb-2">How does billing work?</h4>
                  <p className="text-sm text-gray-600">
                    We charge your payment method automatically each month or year. You can update your payment method anytime in your account settings.
                  </p>
                </div>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  );
};

export default Plans;
