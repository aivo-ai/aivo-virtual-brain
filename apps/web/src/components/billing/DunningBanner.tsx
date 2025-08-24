import React from 'react'
import { DunningState } from '../../api/paymentsClient'
import { Button } from '../ui/Button'
import {
  AlertTriangle,
  CreditCard,
  XCircle,
  Clock,
  ExternalLink,
} from '../ui/Icons'

export interface DunningBannerProps {
  dunningState: DunningState
  onUpdatePayment?: () => void
  onRetryPayment?: () => void
  onContactSupport?: () => void
  className?: string
}

export const DunningBanner: React.FC<DunningBannerProps> = ({
  dunningState,
  onUpdatePayment,
  onRetryPayment,
  onContactSupport,
  className = '',
}) => {
  const getBannerConfig = () => {
    switch (dunningState.status) {
      case 'payment_failed':
        return {
          icon: <CreditCard className="w-5 h-5" />,
          bgColor: 'bg-yellow-50',
          borderColor: 'border-yellow-200',
          iconColor: 'text-yellow-600',
          titleColor: 'text-yellow-800',
          textColor: 'text-yellow-700',
          buttonVariant: 'primary' as const,
          urgent: false,
        }

      case 'past_due':
        return {
          icon: <AlertTriangle className="w-5 h-5" />,
          bgColor: 'bg-orange-50',
          borderColor: 'border-orange-200',
          iconColor: 'text-orange-600',
          titleColor: 'text-orange-800',
          textColor: 'text-orange-700',
          buttonVariant: 'primary' as const,
          urgent: true,
        }

      case 'subscription_canceled':
        return {
          icon: <XCircle className="w-5 h-5" />,
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          iconColor: 'text-red-600',
          titleColor: 'text-red-800',
          textColor: 'text-red-700',
          buttonVariant: 'primary' as const,
          urgent: true,
        }

      case 'grace_period':
        return {
          icon: <Clock className="w-5 h-5" />,
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          iconColor: 'text-blue-600',
          titleColor: 'text-blue-800',
          textColor: 'text-blue-700',
          buttonVariant: 'outline' as const,
          urgent: false,
        }

      default:
        return null
    }
  }

  const config = getBannerConfig()
  if (!config) return null

  const getTitle = () => {
    switch (dunningState.status) {
      case 'payment_failed':
        return 'Payment Failed'
      case 'past_due':
        return 'Account Past Due'
      case 'subscription_canceled':
        return 'Subscription Canceled'
      case 'grace_period':
        return 'Grace Period Active'
      default:
        return 'Payment Issue'
    }
  }

  const getMessage = () => {
    const daysUntil = dunningState.gracePeriodEnds
      ? Math.ceil(
          (new Date(dunningState.gracePeriodEnds).getTime() - Date.now()) /
            (1000 * 60 * 60 * 24)
        )
      : 0

    switch (dunningState.status) {
      case 'payment_failed':
        return `Your last payment failed on ${new Date(dunningState.lastFailedAt!).toLocaleDateString()}. Please update your payment method to continue using the service.`

      case 'past_due':
        return `Your account is past due. ${
          daysUntil > 0
            ? `You have ${daysUntil} days remaining before your account is suspended.`
            : 'Please update your payment immediately to avoid service interruption.'
        }`

      case 'subscription_canceled':
        return `Your subscription was canceled due to failed payments. You can reactivate your subscription at any time.`

      case 'grace_period':
        return `Your payment failed, but you're in a grace period. ${
          daysUntil > 0
            ? `Your access will continue for ${daysUntil} more days.`
            : 'Please update your payment method soon.'
        }`

      default:
        return 'There was an issue with your payment. Please update your payment method.'
    }
  }

  const getPrimaryAction = () => {
    switch (dunningState.status) {
      case 'payment_failed':
      case 'grace_period':
        return {
          label: 'Update Payment Method',
          action: onUpdatePayment,
        }

      case 'past_due':
        return {
          label: 'Retry Payment',
          action: onRetryPayment,
        }

      case 'subscription_canceled':
        return {
          label: 'Reactivate Subscription',
          action: onUpdatePayment,
        }

      default:
        return null
    }
  }

  const primaryAction = getPrimaryAction()

  return (
    <div
      className={`${config.bgColor} ${config.borderColor} border rounded-lg p-4 ${className}`}
      data-testid="dunning-banner"
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className={`${config.iconColor} mt-0.5`}>{config.icon}</div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h3 className={`font-medium ${config.titleColor} mb-1`}>
                {getTitle()}
                {config.urgent && (
                  <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                    Urgent
                  </span>
                )}
              </h3>
              <p className={`text-sm ${config.textColor} mb-3`}>
                {getMessage()}
              </p>

              {/* Failed attempts info */}
              {dunningState.attemptCount > 0 && (
                <p className={`text-xs ${config.textColor} mb-3`}>
                  Failed payment attempts: {dunningState.attemptCount}
                  {dunningState.nextRetryAt && (
                    <>
                      {' '}
                      • Next retry:{' '}
                      {new Date(dunningState.nextRetryAt).toLocaleDateString()}
                    </>
                  )}
                </p>
              )}
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-2">
              {primaryAction && (
                <Button
                  onClick={primaryAction.action}
                  variant={config.buttonVariant}
                  size="sm"
                  className="whitespace-nowrap"
                >
                  {primaryAction.label}
                </Button>
              )}

              {onContactSupport && (
                <Button
                  onClick={onContactSupport}
                  variant="ghost"
                  size="sm"
                  className="whitespace-nowrap"
                >
                  <ExternalLink className="w-4 h-4 mr-1" />
                  Contact Support
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Additional Details */}
      {(dunningState.status === 'past_due' ||
        dunningState.status === 'grace_period') &&
        dunningState.gracePeriodEnds && (
          <div className={`mt-3 pt-3 border-t ${config.borderColor}`}>
            <div className="flex items-center justify-between text-xs">
              <span className={config.textColor}>
                {dunningState.status === 'grace_period'
                  ? 'Grace period ends:'
                  : 'Final due date:'}
              </span>
              <span className={`font-medium ${config.titleColor}`}>
                {new Date(dunningState.gracePeriodEnds).toLocaleDateString()}
              </span>
            </div>
          </div>
        )}
    </div>
  )
}

export default DunningBanner
