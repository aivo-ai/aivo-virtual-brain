/**
 * Simple toast hook for notifications
 */
import { useState } from 'react'

interface ToastProps {
  title: string
  description: string
  variant?: 'default' | 'destructive'
}

export function useToast() {
  const [toasts, setToasts] = useState<ToastProps[]>([])

  const toast = ({ title, description, variant = 'default' }: ToastProps) => {
    console.log(`[${variant.toUpperCase()}] ${title}: ${description}`)

    // In a real implementation, this would trigger a toast UI component
    // For now, we'll just log and simulate a toast
    const newToast = { title, description, variant }
    setToasts(prev => [...prev, newToast])

    // Auto-remove after 3 seconds
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t !== newToast))
    }, 3000)
  }

  return { toast, toasts }
}
