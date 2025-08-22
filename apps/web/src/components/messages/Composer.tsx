import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { chatClient } from '@/api/chatClient'

interface ComposerProps {
  threadId: string
  onMessageSent: () => void
  onAIResponseStart: () => void
  onAIResponseEnd: () => void
  disabled?: boolean
}

export function Composer({
  threadId,
  onMessageSent,
  onAIResponseStart,
  onAIResponseEnd,
  disabled = false,
}: ComposerProps) {
  const { t } = useTranslation()
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isAIEnabled, setIsAIEnabled] = useState(true)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`
    }
  }, [message])

  // Focus textarea on mount
  useEffect(() => {
    if (textareaRef.current && !disabled) {
      textareaRef.current.focus()
    }
  }, [disabled])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!message.trim() || isSending || disabled) return

    const userMessage = message.trim()
    setMessage('')
    setIsSending(true)
    setError(null)

    try {
      // Send user message
      await chatClient.createMessage(threadId, {
        content: userMessage,
        sender_type: 'teacher', // TODO: Get from user context
        message_type: 'text',
      })

      onMessageSent()

      // Generate AI response if enabled
      if (isAIEnabled) {
        onAIResponseStart()

        try {
          await chatClient.generateAIResponse(threadId, {
            onProgress: _chunk => {
              // Progress is handled internally by the API client
              // Just update the UI if needed
            },
            onComplete: () => {
              onAIResponseEnd()
              onMessageSent()
            },
            onError: error => {
              console.error('AI response error:', error)
              onAIResponseEnd()
              setError(t('messages.errors.ai_response_failed'))
            },
          })
        } catch (aiError) {
          console.error('AI response error:', aiError)
          onAIResponseEnd()
          setError(t('messages.errors.ai_response_failed'))
        }
      }
    } catch (err) {
      console.error('Failed to send message:', err)
      setError(t('messages.errors.send_message_failed'))
      // Restore the message if sending failed
      setMessage(userMessage)
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const isDisabled = disabled || isSending

  return (
    <div className="p-4">
      {/* Error message */}
      {error && (
        <div className="mb-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <div className="flex items-center justify-between">
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-200"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
      )}

      {/* AI toggle */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <label className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
            <input
              type="checkbox"
              checked={isAIEnabled}
              onChange={e => setIsAIEnabled(e.target.checked)}
              className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500 dark:bg-gray-700"
            />
            <span>{t('messages.enable_ai_responses')}</span>
          </label>
        </div>

        {isAIEnabled && (
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {t('messages.ai_powered_by_inference_gateway')}
          </div>
        )}
      </div>

      {/* Message composer */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative border border-gray-300 dark:border-gray-600 rounded-lg focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isDisabled
                ? t('messages.composer_disabled')
                : t('messages.type_message')
            }
            disabled={isDisabled}
            className="w-full px-4 py-3 pr-12 resize-none border-0 focus:ring-0 focus:outline-none bg-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 disabled:opacity-50"
            rows={1}
            style={{ minHeight: '48px', maxHeight: '120px' }}
          />

          {/* Send button */}
          <div className="absolute right-2 bottom-2">
            <button
              type="submit"
              disabled={isDisabled || !message.trim()}
              className="p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white rounded-lg transition-colors disabled:cursor-not-allowed"
              title={t('messages.send_message')}
            >
              {isSending ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Helper text */}
        <div className="flex items-center justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
          <span>
            {t('messages.enter_to_send')} • {t('messages.shift_enter_new_line')}
          </span>
          <span>{message.length}/2000</span>
        </div>
      </form>
    </div>
  )
}
