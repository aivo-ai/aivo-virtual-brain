// apps/web/src/components/navigation/LanguageSelector.tsx
import React from 'react'
import { LanguageSwitcher, languages } from '@aivo/i18n'

interface LanguageSelectorProps {
  variant?: 'dropdown' | 'inline' | 'modal'
  className?: string
  showNativeName?: boolean
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  variant = 'dropdown',
  className = '',
  showNativeName = true,
}) => {
  return (
    <LanguageSwitcher
      languages={languages}
      variant={variant}
      className={className}
      showNativeName={showNativeName}
    />
  )
}

export default LanguageSelector
