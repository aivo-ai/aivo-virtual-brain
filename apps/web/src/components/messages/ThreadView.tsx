import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Thread } from '@/api/chatClient'
import { MessageList } from '@/components/messages/MessageList'
import { Composer } from '@/components/messages/Composer'

interface ThreadViewProps {
  thread: Thread
  onBack: () => void
  onThreadUpdate: () => void
}

export function ThreadView({
  thread,
  onBack,
  onThreadUpdate,
}: ThreadViewProps) {
  const { t } = useTranslation()
  const [isGeneratingResponse, setIsGeneratingResponse] = useState(false)

  // Handle keyboard shortcut for going back (Escape)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onBack()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onBack])

  const handleAIResponseStart = () => {
    setIsGeneratingResponse(true)
  }

  const handleAIResponseEnd = () => {
    setIsGeneratingResponse(false)
    onThreadUpdate()
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center space-x-3">
          {/* Back button (mobile only) */}
          <button
            onClick={onBack}
            className="lg:hidden p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg transition-colors"
            title={t('common.back')}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
          </button>

          <div>
            <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
              {thread.title}
            </h1>
            <div className="flex items-center space-x-2 text-sm text-gray-500 dark:text-gray-400">
              <span>
                {t('messages.created')}{' '}
                {new Date(thread.created_at).toLocaleDateString()}
              </span>
              {isGeneratingResponse && (
                <>
                  <span>•</span>
                  <div className="flex items-center space-x-1">
                    <div className="flex space-x-1">
                      <div className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"></div>
                      <div
                        className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"
                        style={{ animationDelay: '0.1s' }}
                      ></div>
                      <div
                        className="w-1 h-1 bg-blue-500 rounded-full animate-bounce"
                        style={{ animationDelay: '0.2s' }}
                      ></div>
                    </div>
                    <span className="text-xs">{t('messages.ai_typing')}</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Thread Actions */}
        <div className="flex items-center space-x-2">
          <button
            className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg transition-colors"
            title={t('messages.thread_settings')}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <MessageList threadId={thread.id} onThreadUpdate={onThreadUpdate} />
      </div>

      {/* Composer */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <Composer
          threadId={thread.id}
          onMessageSent={onThreadUpdate}
          onAIResponseStart={handleAIResponseStart}
          onAIResponseEnd={handleAIResponseEnd}
          disabled={isGeneratingResponse}
        />
      </div>
    </div>
  )
}
