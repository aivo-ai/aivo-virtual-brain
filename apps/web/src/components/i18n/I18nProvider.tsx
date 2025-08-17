// apps/web/src/components/i18n/I18nProvider.tsx
import React from 'react'
import { RTLProvider, languages } from '@aivo/i18n'
import '@aivo/i18n/rtl.css'

interface I18nProviderProps {
  children: JSX.Element | JSX.Element[] | string | null
}

export const I18nProvider: React.FC<I18nProviderProps> = ({ children }) => {
  return <RTLProvider languages={languages}>{children}</RTLProvider>
}

export default I18nProvider
