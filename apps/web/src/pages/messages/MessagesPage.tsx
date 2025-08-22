import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ROUTES } from '@/types/routes'
import { chatClient } from '@/api/chatClient'
import { Thread, ThreadWithLastMessage } from '@/api/chatClient'
import { Threads } from '@/components/messages/Threads'
import { ThreadView } from '@/components/messages/ThreadView'

export default function MessagesPage() {
  const { t } = useTranslation()
  const { threadId } = useParams<{ threadId: string }>()
  const navigate = useNavigate()

  const [threads, setThreads] = useState<ThreadWithLastMessage[]>([])
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isMobileThreadListVisible, setIsMobileThreadListVisible] =
    useState(!threadId)

  // Load threads on mount
  useEffect(() => {
    loadThreads()
  }, [])

  // Load selected thread when threadId changes
  useEffect(() => {
    if (threadId) {
      loadThread(threadId)
      setIsMobileThreadListVisible(false)
    } else {
      setSelectedThread(null)
      setIsMobileThreadListVisible(true)
    }
  }, [threadId])

  const loadThreads = async () => {
    try {
      setIsLoading(true)
      const result = await chatClient.getThreads()
      setThreads(result.threads)
      setError(null)
    } catch (err) {
      console.error('Failed to load threads:', err)
      setError(t('messages.errors.load_threads_failed'))
    } finally {
      setIsLoading(false)
    }
  }

  const loadThread = async (id: string) => {
    try {
      const thread = await chatClient.getThread(id)
      setSelectedThread(thread)
      setError(null)
    } catch (err) {
      console.error('Failed to load thread:', err)
      setError(t('messages.errors.load_thread_failed'))
      // Navigate back to messages list if thread not found
      navigate(ROUTES.MESSAGES)
    }
  }

  const handleThreadSelect = (thread: ThreadWithLastMessage) => {
    navigate(ROUTES.MESSAGES_THREAD.replace(':threadId', thread.id))
  }

  const handleNewThread = async (title: string, initialMessage?: string) => {
    try {
      const thread = await chatClient.createThread({
        title,
        learner_id: 'current-user', // TODO: Get from user context
      })
      await loadThreads() // Refresh thread list
      navigate(ROUTES.MESSAGES_THREAD.replace(':threadId', thread.id))

      // Send initial message if provided
      if (initialMessage) {
        await chatClient.createMessage(thread.id, {
          content: initialMessage,
          sender_type: 'teacher', // TODO: Get from user context
          message_type: 'text',
          type: 'user',
        })
      }
    } catch (err) {
      console.error('Failed to create thread:', err)
      setError(t('messages.errors.create_thread_failed'))
    }
  }

  const handleDeleteThread = async (threadId: string) => {
    try {
      await chatClient.deleteThread(threadId)
      await loadThreads() // Refresh thread list

      // Navigate away if we're viewing the deleted thread
      if (selectedThread?.id === threadId) {
        navigate(ROUTES.MESSAGES)
      }
    } catch (err) {
      console.error('Failed to delete thread:', err)
      setError(t('messages.errors.delete_thread_failed'))
    }
  }

  const handleBackToThreads = () => {
    setIsMobileThreadListVisible(true)
    navigate(ROUTES.MESSAGES)
  }

  if (isLoading && threads.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-gray-500 dark:text-gray-400">
          {t('common.loading')}
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Error Toast */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-500 text-white px-4 py-2 rounded-lg shadow-lg z-50">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 text-white hover:text-gray-200"
          >
            ×
          </button>
        </div>
      )}

      {/* Thread List Panel */}
      <div
        className={`
        ${isMobileThreadListVisible ? 'block' : 'hidden'} 
        lg:block lg:w-1/3 xl:w-1/4 
        bg-white dark:bg-gray-800 
        border-r border-gray-200 dark:border-gray-700
        flex flex-col
      `}
      >
        <Threads
          threads={threads}
          selectedThreadId={selectedThread?.id}
          onThreadSelect={handleThreadSelect}
          onNewThread={handleNewThread}
          onDeleteThread={handleDeleteThread}
          onRefresh={loadThreads}
          isLoading={isLoading}
        />
      </div>

      {/* Conversation Panel */}
      <div
        className={`
        ${isMobileThreadListVisible ? 'hidden' : 'block'} 
        lg:block flex-1 
        bg-white dark:bg-gray-800
        flex flex-col
      `}
      >
        {selectedThread ? (
          <ThreadView
            thread={selectedThread}
            onBack={handleBackToThreads}
            onThreadUpdate={() => {
              loadThread(selectedThread.id)
              loadThreads() // Refresh thread list to update last message
            }}
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500 dark:text-gray-400">
              <h3 className="text-lg font-medium mb-2">
                {t('messages.no_thread_selected')}
              </h3>
              <p className="text-sm">
                {t('messages.select_thread_or_create_new')}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
