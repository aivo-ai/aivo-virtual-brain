import React from 'react'
import { Plan, formatPrice } from '../../api/paymentsClient'
import { Card, CardContent } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { CheckCircle, Star, Users, Clock } from '../ui/Icons'

export interface PlanCardProps {
  plan: Plan
  isCurrentPlan?: boolean
  isLoading?: boolean
  onSelect: (planId: string) => void
  studentCount?: number
  showDiscount?: boolean
  className?: string
}

export const PlanCard: React.FC<PlanCardProps> = ({
  plan,
  isCurrentPlan = false,
  isLoading = false,
  onSelect,
  studentCount = 1,
  showDiscount = false,
  className = '',
}) => {
  const hasDiscount = plan.originalPrice && plan.originalPrice > plan.price
  const discountPercent = hasDiscount
    ? Math.round(
        ((plan.originalPrice! - plan.price) / plan.originalPrice!) * 100
      )
    : 0

  const handleSelect = () => {
    if (!isCurrentPlan && !isLoading) {
      onSelect(plan.id)
    }
  }

  return (
    <Card
      className={`relative transition-all duration-200 hover:shadow-lg ${
        plan.popular ? 'ring-2 ring-blue-500 scale-105' : ''
      } ${isCurrentPlan ? 'ring-2 ring-green-500' : ''} ${className}`}
      data-testid="plan-card"
    >
      {/* Popular Badge */}
      {plan.popular && (
        <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
          <Badge className="bg-blue-500 text-white px-3 py-1 text-sm font-medium flex items-center gap-1">
            <Star className="w-3 h-3" />
            Most Popular
          </Badge>
        </div>
      )}

      {/* Current Plan Badge */}
      {isCurrentPlan && (
        <div className="absolute -top-3 right-4">
          <Badge className="bg-green-500 text-white px-3 py-1 text-sm font-medium flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Current Plan
          </Badge>
        </div>
      )}

      <CardContent className="p-6">
        {/* Plan Header */}
        <div className="text-center mb-6">
          <h3 className="text-xl font-bold text-gray-900 mb-2">{plan.name}</h3>
          <p className="text-gray-600 text-sm mb-4">{plan.description}</p>

          {/* Pricing */}
          <div className="mb-4">
            <div className="flex items-center justify-center gap-2 mb-1">
              {hasDiscount && (
                <span className="text-lg text-gray-400 line-through">
                  {formatPrice(plan.originalPrice!, plan.currency)}
                </span>
              )}
              <span className="text-3xl font-bold text-gray-900">
                {formatPrice(plan.price, plan.currency)}
              </span>
              <span className="text-gray-600">/{plan.interval}</span>
            </div>

            {hasDiscount && (
              <div className="flex items-center justify-center gap-2">
                <Badge className="bg-green-100 text-green-700 text-xs">
                  {discountPercent}% OFF
                </Badge>
                {showDiscount && studentCount > 1 && (
                  <span className="text-xs text-gray-500">
                    Sibling discount applied
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Trial Info */}
          {plan.trialDays && !isCurrentPlan && (
            <div className="flex items-center justify-center gap-1 text-sm text-blue-600 mb-4">
              <Clock className="w-4 h-4" />
              {plan.trialDays}-day free trial
            </div>
          )}

          {/* Student Count Info */}
          {studentCount > 1 && showDiscount && (
            <div className="flex items-center justify-center gap-1 text-sm text-gray-600 mb-4">
              <Users className="w-4 h-4" />
              Pricing for {studentCount} students
            </div>
          )}
        </div>

        {/* Features List */}
        <div className="space-y-3 mb-6">
          {plan.features.map((feature, index) => (
            <div key={index} className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 text-green-500 mt-0.5 flex-shrink-0" />
              <span className="text-sm text-gray-700">{feature}</span>
            </div>
          ))}
        </div>

        {/* Action Button */}
        <Button
          onClick={handleSelect}
          disabled={isCurrentPlan || isLoading}
          variant={plan.popular ? 'primary' : 'outline'}
          className="w-full"
          size="lg"
        >
          {isLoading ? (
            <div className="flex items-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Processing...
            </div>
          ) : isCurrentPlan ? (
            'Current Plan'
          ) : plan.trialDays ? (
            `Start ${plan.trialDays}-Day Free Trial`
          ) : (
            'Select Plan'
          )}
        </Button>

        {/* Additional Info */}
        {!isCurrentPlan && (
          <div className="mt-4 text-center">
            <p className="text-xs text-gray-500">
              {plan.trialDays
                ? 'No credit card required for trial'
                : 'Billed monthly, cancel anytime'}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default PlanCard
