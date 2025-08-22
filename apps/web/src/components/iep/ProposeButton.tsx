import { useTranslation } from 'react-i18next'
import { Bot, Sparkles, RefreshCw, FileText } from 'lucide-react'

import { Button } from '@/components/ui/Button'

interface ProposeButtonProps {
  onPropose: () => void
  isLoading: boolean
  disabled?: boolean
  hasExistingIEP?: boolean
  className?: string
}

export function ProposeButton({
  onPropose,
  isLoading,
  disabled = false,
  hasExistingIEP = false,
  className = '',
}: ProposeButtonProps) {
  const { t } = useTranslation()

  const getButtonText = () => {
    if (isLoading) {
      return t('iep.assistant.generating')
    }

    if (hasExistingIEP) {
      return t('iep.assistant.propose_revision')
    }

    return t('iep.assistant.propose_draft')
  }

  const getButtonIcon = () => {
    if (isLoading) {
      return <RefreshCw className="h-4 w-4 animate-spin" />
    }

    if (hasExistingIEP) {
      return <FileText className="h-4 w-4" />
    }

    return <Bot className="h-4 w-4" />
  }

  return (
    <Button
      onClick={onPropose}
      disabled={disabled || isLoading}
      className={`relative overflow-hidden bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white border-0 ${className}`}
      size="lg"
    >
      {/* Animated background for loading */}
      {isLoading && (
        <div className="absolute inset-0 bg-gradient-to-r from-blue-400 via-purple-400 to-blue-400 animate-pulse" />
      )}

      {/* Sparkle effect */}
      {!isLoading && (
        <Sparkles className="absolute top-1 right-1 h-3 w-3 text-white/60 animate-pulse" />
      )}

      <div className="relative flex items-center space-x-2">
        {getButtonIcon()}
        <span className="font-medium">{getButtonText()}</span>
      </div>
    </Button>
  )
}
