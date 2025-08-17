// apps/web/src/hooks/useI18nHelpers.ts
import { useTranslation } from 'react-i18next'
import {
  useRTL,
  formatNumber,
  formatCurrency,
  formatDate,
  formatTime,
  formatDateTime,
  getRelativeTime,
} from '@aivo/i18n'

export const useI18nHelpers = () => {
  const { t, i18n } = useTranslation()
  const { isRTL, direction, language } = useRTL()

  return {
    // Translation function
    t,

    // Language info
    currentLanguage: language,
    isRTL,
    direction,

    // Formatting functions
    formatNumber: (value: number) => formatNumber(value, i18n.language),
    formatCurrency: (value: number) => formatCurrency(value, i18n.language),
    formatDate: (date: Date | string) => formatDate(date, i18n.language),
    formatTime: (date: Date | string) => formatTime(date, i18n.language),
    formatDateTime: (date: Date | string) =>
      formatDateTime(date, i18n.language),
    getRelativeTime: (date: Date | string) =>
      getRelativeTime(date, i18n.language),

    // Style helpers for RTL
    getDirectionalStyles: () => ({
      direction,
      textAlign: isRTL ? 'right' : 'left',
      fontFamily: language?.fontStack,
    }),

    // Class name helpers
    getDirectionalClasses: (baseClasses: string) => {
      const rtlClasses = isRTL ? 'dir-rtl' : 'dir-ltr'
      return `${baseClasses} ${rtlClasses}`
    },
  }
}

export default useI18nHelpers
