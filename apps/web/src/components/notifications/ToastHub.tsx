/**
 * S3-14 ToastHub Component
 * Real-time toast notifications with accessibility support
 */

import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { useToasts, ToastNotification, NotificationPriority, NotificationCategory } from '../../api/notificationClient'
import { Button } from '../ui/Button'
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  Info, 
  X,
  ExternalLink
} from '../ui/Icons'

interface ToastItemProps {
  toast: ToastNotification
  onClose: (id: string) => void
  onAction?: (url: string) => void
}

function ToastItem({ toast, onClose, onAction }: ToastItemProps) {
  const getIcon = () => {
    switch (toast.category) {
      case NotificationCategory.SUCCESS:
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case NotificationCategory.WARNING:
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      case NotificationCategory.ERROR:
      case NotificationCategory.ALERT:
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <Info className="w-5 h-5 text-blue-500" />
    }
  }

  const getStyles = () => {
    const baseStyles = "relative flex items-start gap-3 p-4 rounded-lg shadow-lg border-l-4 bg-white dark:bg-gray-800 min-w-80 max-w-md"
    
    switch (toast.category) {
      case NotificationCategory.SUCCESS:
        return `${baseStyles} border-l-green-500`
      case NotificationCategory.WARNING:
        return `${baseStyles} border-l-yellow-500`
      case NotificationCategory.ERROR:
      case NotificationCategory.ALERT:
        return `${baseStyles} border-l-red-500`
      default:
        return `${baseStyles} border-l-blue-500`
    }
  }

  const getPriorityStyles = () => {
    switch (toast.priority) {
      case NotificationPriority.URGENT:
        return "animate-pulse ring-2 ring-red-500 ring-opacity-50"
      case NotificationPriority.HIGH:
        return "ring-1 ring-orange-500 ring-opacity-30"
      default:
        return ""
    }
  }

  const handleAction = () => {
    if (toast.actionUrl && onAction) {
      onAction(toast.actionUrl)
    }
  }

  return (
    <div 
      className={`${getStyles()} ${getPriorityStyles()}`}
      role="alert"
      aria-live={toast.priority === NotificationPriority.URGENT ? "assertive" : "polite"}
      aria-labelledby={`toast-title-${toast.id}`}
      aria-describedby={`toast-message-${toast.id}`}
    >
      <div className="flex-shrink-0">
        {getIcon()}
      </div>
      
      <div className="flex-1 min-w-0">
        <h4 
          id={`toast-title-${toast.id}`}
          className="text-sm font-semibold text-gray-900 dark:text-white"
        >
          {toast.title}
        </h4>
        <p 
          id={`toast-message-${toast.id}`}
          className="mt-1 text-sm text-gray-600 dark:text-gray-300"
        >
          {toast.message}
        </p>
        
        {toast.actionLabel && toast.actionUrl && (
          <div className="mt-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleAction}
              className="p-0 h-auto text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-200"
            >
              {toast.actionLabel}
              <ExternalLink className="w-3 h-3 ml-1" />
            </Button>
          </div>
        )}
      </div>
      
      <button
        onClick={() => onClose(toast.id)}
        className="flex-shrink-0 rounded-md p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
        aria-label={`Close ${toast.title} notification`}
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}

export function ToastHub() {
  const { toasts, removeToast } = useToasts()
  const liveRegionRef = useRef<HTMLDivElement>(null)
  const toastContainerRef = useRef<HTMLDivElement>(null)

  // Handle action clicks
  const handleAction = (url: string) => {
    if (url.startsWith('/')) {
      // Internal navigation
      window.location.href = url
    } else {
      // External link
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }

  // Announce new toasts to screen readers
  useEffect(() => {
    if (toasts.length > 0 && liveRegionRef.current) {
      const latestToast = toasts[toasts.length - 1]
      const announcement = `${latestToast.title}. ${latestToast.message}`
      
      // Clear and set announcement for screen readers
      liveRegionRef.current.textContent = ''
      setTimeout(() => {
        if (liveRegionRef.current) {
          liveRegionRef.current.textContent = announcement
        }
      }, 100)
    }
  }, [toasts])

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && toasts.length > 0) {
        // Close the most recent toast
        removeToast(toasts[toasts.length - 1].id)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [toasts, removeToast])

  // Auto-focus management for urgent notifications
  useEffect(() => {
    const urgentToast = toasts.find(toast => toast.priority === NotificationPriority.URGENT)
    if (urgentToast && toastContainerRef.current) {
      const toastElement = toastContainerRef.current.querySelector(`[aria-labelledby="toast-title-${urgentToast.id}"]`) as HTMLElement
      if (toastElement) {
        toastElement.focus()
      }
    }
  }, [toasts])

  if (toasts.length === 0) {
    return null
  }

  return createPortal(
    <>
      {/* Screen reader live region */}
      <div
        ref={liveRegionRef}
        className="sr-only"
        aria-live="polite"
        aria-atomic="true"
        role="status"
      />
      
      {/* Toast container */}
      <div
        ref={toastContainerRef}
        className="fixed top-4 right-4 z-50 space-y-3 pointer-events-none"
        aria-label="Notifications"
        role="region"
      >
        {toasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <ToastItem
              toast={toast}
              onClose={removeToast}
              onAction={handleAction}
            />
          </div>
        ))}
      </div>
    </>,
    document.body
  )
}

export default ToastHub
