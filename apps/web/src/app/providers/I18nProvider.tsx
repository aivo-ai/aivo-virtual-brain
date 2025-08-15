import { ReactNode, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from './AuthProvider'

interface I18nProviderProps {
  children: ReactNode
}

export function I18nProvider({ children }: I18nProviderProps) {
  const { i18n } = useTranslation()
  const { user } = useAuth()

  // Update language when user language preference changes
  useEffect(() => {
    const userLanguage = user?.settings?.language
    if (userLanguage && userLanguage !== i18n.language) {
      i18n.changeLanguage(userLanguage)
    }
  }, [user?.settings?.language, i18n])

  // Set direction for RTL languages
  useEffect(() => {
    const rtlLanguages = ['ar', 'he', 'fa', 'ur']
    const isRTL = rtlLanguages.includes(i18n.language)

    document.documentElement.dir = isRTL ? 'rtl' : 'ltr'
    document.documentElement.lang = i18n.language
  }, [i18n.language])

  return <>{children}</>
}

// Hook for language-specific utilities
export function useI18nUtils() {
  const { i18n, t } = useTranslation()

  const formatDate = (
    date: Date | string,
    options?: Intl.DateTimeFormatOptions
  ) => {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    return new Intl.DateTimeFormat(i18n.language, options).format(dateObj)
  }

  const formatNumber = (number: number, options?: Intl.NumberFormatOptions) => {
    return new Intl.NumberFormat(i18n.language, options).format(number)
  }

  const formatCurrency = (amount: number, currency = 'USD') => {
    return new Intl.NumberFormat(i18n.language, {
      style: 'currency',
      currency,
    }).format(amount)
  }

  const formatRelativeTime = (date: Date | string) => {
    const dateObj = typeof date === 'string' ? new Date(date) : date
    const now = new Date()
    const diffInSeconds = Math.floor((now.getTime() - dateObj.getTime()) / 1000)

    const rtf = new Intl.RelativeTimeFormat(i18n.language, { numeric: 'auto' })

    if (diffInSeconds < 60) {
      return rtf.format(-diffInSeconds, 'second')
    } else if (diffInSeconds < 3600) {
      return rtf.format(-Math.floor(diffInSeconds / 60), 'minute')
    } else if (diffInSeconds < 86400) {
      return rtf.format(-Math.floor(diffInSeconds / 3600), 'hour')
    } else if (diffInSeconds < 2592000) {
      return rtf.format(-Math.floor(diffInSeconds / 86400), 'day')
    } else if (diffInSeconds < 31536000) {
      return rtf.format(-Math.floor(diffInSeconds / 2592000), 'month')
    } else {
      return rtf.format(-Math.floor(diffInSeconds / 31536000), 'year')
    }
  }

  const getLocalizedPath = (path: string) => {
    // For future localized routing support
    if (i18n.language === 'en') {
      return path
    }
    return `/${i18n.language}${path}`
  }

  const isRTL = () => {
    const rtlLanguages = ['ar', 'he', 'fa', 'ur']
    return rtlLanguages.includes(i18n.language)
  }

  return {
    currentLanguage: i18n.language,
    changeLanguage: i18n.changeLanguage,
    formatDate,
    formatNumber,
    formatCurrency,
    formatRelativeTime,
    getLocalizedPath,
    isRTL,
    t,
  }
}
