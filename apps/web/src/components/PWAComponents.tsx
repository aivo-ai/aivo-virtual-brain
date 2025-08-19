import { useEffect, useState } from 'react'
import { offlineQueue } from '../utils/offlineQueue'

interface OfflineToastProps {
  duration?: number
}

export function OfflineToast({ duration = 5000 }: OfflineToastProps) {
  const [isOffline, setIsOffline] = useState(!navigator.onLine)
  const [queuedCount, setQueuedCount] = useState(0)
  const [showToast, setShowToast] = useState(false)

  useEffect(() => {
    const handleConnectionChange = (event: CustomEvent) => {
      const { isOnline } = event.detail
      setIsOffline(!isOnline)
      
      if (!isOnline) {
        setShowToast(true)
        // Auto hide after duration
        setTimeout(() => setShowToast(false), duration)
      } else {
        setShowToast(false)
      }
    }

    const handleQueueUpdate = async () => {
      const count = await offlineQueue.getQueuedRequestsCount()
      setQueuedCount(count)
    }

    // Initial state
    handleQueueUpdate()

    // Listen for connection changes
    window.addEventListener('connection-change', handleConnectionChange as EventListener)
    window.addEventListener('offline-queue-update', handleQueueUpdate)

    return () => {
      window.removeEventListener('connection-change', handleConnectionChange as EventListener)
      window.removeEventListener('offline-queue-update', handleQueueUpdate)
    }
  }, [duration])

  if (!showToast && !isOffline) return null

  return (
    <div 
      className={`fixed top-4 right-4 z-50 max-w-sm bg-orange-500 text-white px-4 py-3 rounded-lg shadow-lg transition-all duration-300 ${
        showToast || isOffline ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      }`}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-center gap-2">
        <div className="flex-shrink-0">
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="flex-1">
          <p className="font-medium">You're offline</p>
          <p className="text-sm opacity-90">
            {queuedCount > 0 
              ? `${queuedCount} action(s) queued for sync` 
              : 'New actions will be saved for later'
            }
          </p>
        </div>
        <button
          onClick={() => setShowToast(false)}
          className="flex-shrink-0 ml-2 hover:bg-orange-600 rounded p-1"
          aria-label="Dismiss notification"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
  )
}

export function ConnectionStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [queuedCount, setQueuedCount] = useState(0)

  useEffect(() => {
    const handleConnectionChange = (event: CustomEvent) => {
      setIsOnline(event.detail.isOnline)
    }

    const handleQueueUpdate = async () => {
      const count = await offlineQueue.getQueuedRequestsCount()
      setQueuedCount(count)
    }

    // Initial state
    handleQueueUpdate()

    window.addEventListener('connection-change', handleConnectionChange as EventListener)
    window.addEventListener('offline-queue-update', handleQueueUpdate)

    return () => {
      window.removeEventListener('connection-change', handleConnectionChange as EventListener)
      window.removeEventListener('offline-queue-update', handleQueueUpdate)
    }
  }, [])

  return (
    <div className="flex items-center gap-2 text-sm">
      <div 
        className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}
        aria-label={isOnline ? 'Online' : 'Offline'}
      />
      <span className="text-gray-600">
        {isOnline ? 'Online' : 'Offline'}
        {queuedCount > 0 && ` (${queuedCount} queued)`}
      </span>
    </div>
  )
}

export function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null)
  const [showInstallPrompt, setShowInstallPrompt] = useState(false)

  useEffect(() => {
    const handleBeforeInstallPrompt = (e: Event) => {
      // Prevent the mini-infobar from appearing
      e.preventDefault()
      // Save the event for later use
      setDeferredPrompt(e)
      setShowInstallPrompt(true)
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
    }
  }, [])

  const handleInstallClick = async () => {
    if (!deferredPrompt) return

    // Show the install prompt
    deferredPrompt.prompt()

    // Wait for the user to respond
    const { outcome } = await deferredPrompt.userChoice
    
    if (outcome === 'accepted') {
      console.log('User accepted the install prompt')
    } else {
      console.log('User dismissed the install prompt')
    }

    // Clear the prompt
    setDeferredPrompt(null)
    setShowInstallPrompt(false)
  }

  const handleDismiss = () => {
    setShowInstallPrompt(false)
    setDeferredPrompt(null)
  }

  if (!showInstallPrompt) return null

  return (
    <div className="fixed bottom-4 left-4 right-4 bg-blue-600 text-white p-4 rounded-lg shadow-lg z-50 max-w-md mx-auto">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-1">
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-medium mb-1">Install Aivo Virtual Brains</h3>
          <p className="text-sm opacity-90 mb-3">
            Get quick access and offline features by installing our app on your device.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleInstallClick}
              className="bg-white text-blue-600 px-4 py-2 rounded font-medium text-sm hover:bg-gray-100 transition-colors"
            >
              Install
            </button>
            <button
              onClick={handleDismiss}
              className="border border-white/30 px-4 py-2 rounded text-sm hover:bg-white/10 transition-colors"
            >
              Maybe later
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
