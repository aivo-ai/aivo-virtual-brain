// apps/web/src/components/i18n/LanguageSwitcher.tsx
import React from 'react'
import { LanguageSwitcher as BaseLanguageSwitcher, languages } from '@aivo/i18n'

interface LanguageSwitcherProps {
  className?: string
  variant?: 'dropdown' | 'modal' | 'inline'
  showNativeName?: boolean
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  className = '',
  variant = 'dropdown',
  showNativeName = true,
}) => {
  return (
    <BaseLanguageSwitcher
      languages={languages}
      className={className}
      variant={variant}
      showNativeName={showNativeName}
    />
  )
}

export default LanguageSwitcher
