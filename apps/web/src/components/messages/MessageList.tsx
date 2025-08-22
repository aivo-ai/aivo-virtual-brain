import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { chatClient, Message } from '@/api/chatClient'
import { AttachToIEP } from '@/components/messages/AttachToIEP'

interface MessageListProps {
  threadId: string
  onThreadUpdate: () => void
}

export function MessageList({ threadId, onThreadUpdate }: MessageListProps) {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attachToIEPMessage, setAttachToIEPMessage] = useState<Message | null>(
    null
  )
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadMessages()
  }, [threadId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const loadMessages = async () => {
    try {
      setIsLoading(true)
      const result = await chatClient.getMessages(threadId)
      // Map message types for UI compatibility
      const mappedMessages = result.messages.map(msg => ({
        ...msg,
        type:
          msg.sender_type === 'assistant'
            ? ('assistant' as const)
            : msg.sender_type === 'system'
              ? ('system' as const)
              : ('user' as const),
      }))
      setMessages(mappedMessages)
      setError(null)
    } catch (err) {
      console.error('Failed to load messages:', err)
      setError(t('messages.errors.load_messages_failed'))
    } finally {
      setIsLoading(false)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const handleAttachToIEP = (message: Message) => {
    setAttachToIEPMessage(message)
  }

  const handleIEPAttachmentComplete = () => {
    setAttachToIEPMessage(null)
    onThreadUpdate()
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const isToday = date.toDateString() === now.toDateString()

    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } else {
      return date.toLocaleDateString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    }
  }

  const renderMessage = (message: Message) => {
    const isUser = message.type === 'user'
    const isSystem = message.type === 'system'

    return (
      <div
        key={message.id}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div
          className={`
          max-w-[80%] lg:max-w-[70%] 
          ${
            isUser
              ? 'bg-blue-600 text-white'
              : isSystem
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 border-l-4 border-yellow-400'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
          }
          rounded-lg px-4 py-3 shadow-sm
        `}
        >
          {/* Message Content */}
          <div className="whitespace-pre-wrap break-words">
            {message.content}
          </div>

          {/* Message Metadata */}
          <div
            className={`
            flex items-center justify-between mt-2 pt-2 border-t
            ${
              isUser
                ? 'border-blue-500'
                : 'border-gray-200 dark:border-gray-600'
            }
          `}
          >
            <span
              className={`
              text-xs 
              ${isUser ? 'text-blue-100' : 'text-gray-500 dark:text-gray-400'}
            `}
            >
              {formatTimestamp(message.created_at)}
            </span>

            {/* Actions for AI messages */}
            {!isUser && !isSystem && (
              <div className="flex items-center space-x-2 ml-3">
                <button
                  onClick={() => handleAttachToIEP(message)}
                  className="text-xs px-2 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 rounded hover:bg-green-200 dark:hover:bg-green-800 transition-colors"
                  title={t('messages.attach_to_iep')}
                >
                  {t('messages.attach_to_iep')}
                </button>

                <button
                  className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                  title={t('messages.copy_message')}
                  onClick={() => {
                    navigator.clipboard.writeText(message.content)
                  }}
                >
                  <svg
                    className="w-3 h-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                    />
                  </svg>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500 dark:text-gray-400 text-center">
          <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-2"></div>
          {t('messages.loading_messages')}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-red-500 dark:text-red-400 mb-2">
            <svg
              className="w-12 h-12 mx-auto"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
          <button
            onClick={loadMessages}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            {t('common.retry')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <>
      <div
        ref={messagesContainerRef}
        className="h-full overflow-y-auto p-4 scroll-smooth"
      >
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500 dark:text-gray-400">
              <div className="mb-4">
                <svg
                  className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium mb-2">
                {t('messages.no_messages')}
              </h3>
              <p className="text-sm">{t('messages.start_conversation')}</p>
            </div>
          </div>
        ) : (
          <>
            {messages.map(renderMessage)}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Attach to IEP Modal */}
      {attachToIEPMessage && (
        <AttachToIEP
          message={attachToIEPMessage}
          onClose={() => setAttachToIEPMessage(null)}
          onComplete={handleIEPAttachmentComplete}
        />
      )}
    </>
  )
}
