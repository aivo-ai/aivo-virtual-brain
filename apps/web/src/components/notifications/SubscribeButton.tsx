/**
 * S3-14 SubscribeButton Component
 * Push notification subscription management
 */

import { useState } from 'react'
import { usePushSubscription } from '../../api/notificationClient'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Alert, AlertDescription } from '../ui/Alert'
import { 
  Bell, 
  BellOff, 
  CheckCircle, 
  AlertTriangle,
  Loader2,
  Info
} from '../ui/Icons'

interface SubscribeButtonProps {
  className?: string
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive'
  size?: 'sm' | 'md' | 'lg'
  showStatus?: boolean
  showDescription?: boolean
}

export function SubscribeButton({ 
  className = '',
  variant = 'primary',
  size = 'md',
  showStatus = true,
  showDescription = false
}: SubscribeButtonProps) {
  const { subscription, loading, error, isSupported, subscribe, unsubscribe } = usePushSubscription()
  const [localLoading, setLocalLoading] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const isSubscribed = !!subscription

  const handleToggleSubscription = async () => {
    setLocalLoading(true)
    setLocalError(null)
    setSuccessMessage(null)

    try {
      if (isSubscribed) {
        const success = await unsubscribe()
        if (success) {
          setSuccessMessage('Push notifications disabled successfully')
        }
      } else {
        const success = await subscribe()
        if (success) {
          setSuccessMessage('Push notifications enabled successfully')
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update notification settings'
      setLocalError(errorMessage)
    } finally {
      setLocalLoading(false)
    }
  }

  const getButtonText = () => {
    if (loading || localLoading) {
      return isSubscribed ? 'Unsubscribing...' : 'Subscribing...'
    }
    return isSubscribed ? 'Disable Push Notifications' : 'Enable Push Notifications'
  }

  const getIcon = () => {
    if (loading || localLoading) {
      return <Loader2 className="w-4 h-4 animate-spin" />
    }
    return isSubscribed ? <BellOff className="w-4 h-4" /> : <Bell className="w-4 h-4" />
  }

  const getStatusBadge = () => {
    if (!showStatus) return null

    if (isSubscribed) {
      return (
        <Badge variant="success" className="ml-2">
          <CheckCircle className="w-3 h-3 mr-1" />
          Active
        </Badge>
      )
    }

    return (
      <Badge variant="secondary" className="ml-2">
        <BellOff className="w-3 h-3 mr-1" />
        Disabled
      </Badge>
    )
  }

  if (!isSupported) {
    return (
      <div className={className}>
        <Alert variant="warning">
          <AlertTriangle className="w-4 h-4" />
          <AlertDescription>
            Push notifications are not supported in this browser.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className={className}>
      <div className="flex items-center">
        <Button
          variant={variant}
          size={size}
          onClick={handleToggleSubscription}
          disabled={loading || localLoading}
          className="flex items-center gap-2"
        >
          {getIcon()}
          {getButtonText()}
        </Button>
        {getStatusBadge()}
      </div>

      {showDescription && (
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {isSubscribed 
            ? 'You will receive push notifications for important updates.'
            : 'Enable push notifications to stay updated even when the app is closed.'
          }
        </p>
      )}

      {/* Success Message */}
      {successMessage && (
        <Alert variant="success" className="mt-3">
          <CheckCircle className="w-4 h-4" />
          <AlertDescription>{successMessage}</AlertDescription>
        </Alert>
      )}

      {/* Error Message */}
      {(error || localError) && (
        <Alert variant="destructive" className="mt-3">
          <AlertTriangle className="w-4 h-4" />
          <AlertDescription>
            {localError || error}
          </AlertDescription>
        </Alert>
      )}

      {/* Information about push notifications */}
      {!isSubscribed && showDescription && (
        <Alert className="mt-3">
          <Info className="w-4 h-4" />
          <AlertDescription>
            <strong>About Push Notifications:</strong>
            <ul className="mt-1 list-disc list-inside text-sm space-y-1">
              <li>Receive important alerts even when the app is closed</li>
              <li>Get notified about academic progress and SEL updates</li>
              <li>Stay informed about system announcements</li>
              <li>You can disable notifications at any time</li>
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* Subscription Details */}
      {isSubscribed && subscription && showDescription && (
        <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            Subscription Details
          </h4>
          <dl className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
            <div>
              <dt className="inline font-medium">Status:</dt>
              <dd className="inline ml-1">
                {subscription.isActive ? 'Active' : 'Inactive'}
              </dd>
            </div>
            <div>
              <dt className="inline font-medium">Created:</dt>
              <dd className="inline ml-1">
                {new Date(subscription.createdAt).toLocaleDateString()}
              </dd>
            </div>
            {subscription.lastUsed && (
              <div>
                <dt className="inline font-medium">Last Used:</dt>
                <dd className="inline ml-1">
                  {new Date(subscription.lastUsed).toLocaleDateString()}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </div>
  )
}

export default SubscribeButton
