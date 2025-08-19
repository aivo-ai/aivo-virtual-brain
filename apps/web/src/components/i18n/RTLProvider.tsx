// apps/web/src/components/i18n/RTLProvider.tsx
import React from 'react'
import { RTLProvider as BaseRTLProvider, languages } from '@aivo/i18n'

interface RTLProviderProps {
  children: JSX.Element | JSX.Element[] | string | null
}

export const RTLProvider: React.FC<RTLProviderProps> = ({ children }) => {
  return <BaseRTLProvider languages={languages}>{children}</BaseRTLProvider>
}

export default RTLProvider
