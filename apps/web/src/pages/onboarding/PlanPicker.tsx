import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Button } from '../../components/ui/Button'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import { PlanSelection, UseOnboardingReturn } from '../../hooks/useOnboarding'

interface PlanPickerStepProps {
  onboardingData: UseOnboardingReturn
  onNext: () => void
  onBack: () => void
}

interface PlanOption {
  type: PlanSelection['planType']
  name: string
  description: string
  monthlyPrice: number
  discountPercent: number
  popular?: boolean
  trialDays?: number
}

export const PlanPickerStep: React.FC<PlanPickerStepProps> = ({
  onboardingData,
  onNext,
  onBack,
}) => {
  const { state, updatePlan } = onboardingData
  const learnerCount = state.learners.length
  const [selectedPlan, setSelectedPlan] =
    useState<PlanSelection['planType']>('trial')

  useEffect(() => {
    if (state.plan) {
      setSelectedPlan(state.plan.planType)
    }
  }, [state.plan])

  const planOptions: PlanOption[] = [
    {
      type: 'trial',
      name: '14-Day Free Trial',
      description: 'Full access to all features',
      monthlyPrice: 0,
      discountPercent: 0,
      trialDays: 14,
    },
    {
      type: 'monthly',
      name: 'Monthly Plan',
      description: 'Pay month by month',
      monthlyPrice: 29.99,
      discountPercent: 0,
    },
    {
      type: 'quarterly',
      name: 'Quarterly Plan',
      description: 'Save 20% with 3-month plan',
      monthlyPrice: 23.99,
      discountPercent: 20,
      popular: true,
    },
    {
      type: 'half-year',
      name: '6-Month Plan',
      description: 'Save 30% with 6-month plan',
      monthlyPrice: 20.99,
      discountPercent: 30,
    },
    {
      type: 'yearly',
      name: 'Annual Plan',
      description: 'Save 50% with yearly plan',
      monthlyPrice: 14.99,
      discountPercent: 50,
    },
  ]

  const calculatePrice = (plan: PlanOption) => {
    const basePrice = plan.monthlyPrice * learnerCount
    const siblingDiscount = learnerCount >= 2 ? 0.1 : 0
    const finalPrice = basePrice * (1 - siblingDiscount)

    return {
      original: 29.99 * learnerCount,
      final: finalPrice,
      savings: 29.99 * learnerCount - finalPrice,
      hasSiblingDiscount: learnerCount >= 2,
    }
  }

  const handlePlanSelect = (planType: PlanSelection['planType']) => {
    setSelectedPlan(planType)
  }

  const handleContinue = () => {
    const selectedPlanOption = planOptions.find(p => p.type === selectedPlan)!
    const pricing = calculatePrice(selectedPlanOption)

    const planSelection: PlanSelection = {
      planType: selectedPlan,
      siblingDiscount: learnerCount >= 2,
      totalPrice: pricing.final,
      originalPrice: pricing.original,
    }

    updatePlan(planSelection)
    onNext()
  }

  const PlanCard: React.FC<{ plan: PlanOption; isSelected: boolean }> = ({
    plan,
    isSelected,
  }) => {
    const pricing = calculatePrice(plan)
    const isTrial = plan.type === 'trial'

    return (
      <motion.div
        whileHover={{ y: -4 }}
        whileTap={{ scale: 0.98 }}
        className={`relative bg-white dark:bg-gray-800 rounded-xl border-2 p-6 cursor-pointer transition-all duration-300 ${
          isSelected
            ? 'border-blue-500 shadow-lg ring-2 ring-blue-200 dark:ring-blue-800'
            : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-600'
        }`}
        onClick={() => handlePlanSelect(plan.type)}
      >
        {plan.popular && (
          <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-1 rounded-full text-sm font-medium">
              Most Popular
            </span>
          </div>
        )}

        <div className="text-center">
          <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">
            {plan.name}
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            {plan.description}
          </p>

          {isTrial ? (
            <div className="mb-6">
              <div className="text-4xl font-bold text-green-600 dark:text-green-400">
                FREE
              </div>
              <div className="text-sm text-gray-600 dark:text-gray-400">
                for {plan.trialDays} days
              </div>
            </div>
          ) : (
            <div className="mb-6">
              <div className="flex items-baseline justify-center space-x-1">
                <span className="text-4xl font-bold text-gray-900 dark:text-white">
                  ${pricing.final.toFixed(2)}
                </span>
                <span className="text-gray-600 dark:text-gray-400">/month</span>
              </div>

              {plan.discountPercent > 0 && (
                <div className="text-sm text-gray-500 dark:text-gray-400 line-through">
                  ${(29.99 * learnerCount).toFixed(2)}/month
                </div>
              )}

              {pricing.hasSiblingDiscount && (
                <div className="text-sm text-green-600 dark:text-green-400 mt-1">
                  10% sibling discount applied!
                </div>
              )}
            </div>
          )}

          <div className="space-y-3 text-sm text-gray-600 dark:text-gray-400">
            <div className="flex items-center justify-center">
              <svg
                className="w-4 h-4 text-green-500 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              AI-powered personalized learning
            </div>
            <div className="flex items-center justify-center">
              <svg
                className="w-4 h-4 text-green-500 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              Real-time progress tracking
            </div>
            <div className="flex items-center justify-center">
              <svg
                className="w-4 h-4 text-green-500 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              Parent-teacher communication
            </div>
            <div className="flex items-center justify-center">
              <svg
                className="w-4 h-4 text-green-500 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              {learnerCount} learner{learnerCount > 1 ? 's' : ''} included
            </div>
            {!isTrial && (
              <div className="flex items-center justify-center">
                <svg
                  className="w-4 h-4 text-green-500 mr-2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Cancel anytime
              </div>
            )}
          </div>

          {plan.discountPercent > 0 && (
            <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
              <div className="text-sm font-medium text-green-800 dark:text-green-200">
                Save {plan.discountPercent}% vs monthly
              </div>
              <div className="text-xs text-green-600 dark:text-green-400">
                $
                {(
                  (29.99 - plan.monthlyPrice) *
                  learnerCount *
                  (plan.type === 'yearly'
                    ? 12
                    : plan.type === 'half-year'
                      ? 6
                      : 3)
                ).toFixed(2)}{' '}
                total savings
              </div>
            </div>
          )}
        </div>

        {isSelected && (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            className="absolute top-4 right-4 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center"
          >
            <svg
              className="w-4 h-4 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </motion.div>
        )}
      </motion.div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      <FadeInWhenVisible>
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="inline-flex items-center justify-center w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full mb-4"
          >
            <svg
              className="w-8 h-8 text-green-600 dark:text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
              />
            </svg>
          </motion.div>

          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Choose Your Plan
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Select the perfect plan for {learnerCount} learner
            {learnerCount > 1 ? 's' : ''}
          </p>

          {learnerCount >= 2 && (
            <div className="mt-4 inline-flex items-center px-4 py-2 bg-green-100 dark:bg-green-900 rounded-full">
              <svg
                className="w-5 h-5 text-green-600 dark:text-green-400 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7"
                />
              </svg>
              <span className="text-green-800 dark:text-green-200 font-medium">
                🎉 You qualify for a 10% sibling discount!
              </span>
            </div>
          )}
        </div>
      </FadeInWhenVisible>

      <FadeInWhenVisible delay={0.2}>
        <div className="mb-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-start space-x-3">
            <svg
              className="w-6 h-6 text-blue-600 dark:text-blue-400 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                Start with a Free Trial
              </h3>
              <p className="text-blue-800 dark:text-blue-200 text-sm">
                Try AIVO risk-free for 14 days with full access to all features.
                No credit card required during trial. Cancel anytime.
              </p>
            </div>
          </div>
        </div>
      </FadeInWhenVisible>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-6 mb-8">
        {planOptions.map((plan, index) => (
          <FadeInWhenVisible key={plan.type} delay={index * 0.1}>
            <PlanCard plan={plan} isSelected={selectedPlan === plan.type} />
          </FadeInWhenVisible>
        ))}
      </div>

      {/* Summary */}
      {selectedPlan !== 'trial' && (
        <FadeInWhenVisible>
          <div className="mb-8 p-6 bg-gray-50 dark:bg-gray-900 rounded-lg border">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
              Plan Summary
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-gray-600 dark:text-gray-400">Plan</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {planOptions.find(p => p.type === selectedPlan)?.name}
                </div>
              </div>
              <div>
                <div className="text-gray-600 dark:text-gray-400">Learners</div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {learnerCount} learner{learnerCount > 1 ? 's' : ''}
                </div>
              </div>
              <div>
                <div className="text-gray-600 dark:text-gray-400">
                  Monthly Cost
                </div>
                <div className="font-medium text-gray-900 dark:text-white">
                  $
                  {calculatePrice(
                    planOptions.find(p => p.type === selectedPlan)!
                  ).final.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        </FadeInWhenVisible>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-8">
        <Button variant="outline" onClick={onBack}>
          ← Previous: Consent
        </Button>

        <Button onClick={handleContinue}>
          {selectedPlan === 'trial'
            ? 'Start Free Trial'
            : 'Continue to Schedule'}{' '}
          →
        </Button>
      </div>

      {/* Money Back Guarantee */}
      <FadeInWhenVisible delay={0.6}>
        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700 text-center">
          <div className="flex items-center justify-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
            <svg
              className="w-5 h-5 text-green-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>
              30-day money-back guarantee • Cancel anytime • No long-term
              commitment
            </span>
          </div>
        </div>
      </FadeInWhenVisible>
    </div>
  )
}
