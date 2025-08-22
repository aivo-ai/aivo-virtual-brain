import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ThreadWithLastMessage } from '@/api/chatClient'

interface ThreadsProps {
  threads: ThreadWithLastMessage[]
  selectedThreadId?: string
  onThreadSelect: (thread: ThreadWithLastMessage) => void
  onNewThread: (title: string, initialMessage?: string) => void
  onDeleteThread: (threadId: string) => void
  onRefresh: () => void
  isLoading: boolean
}

export function Threads({
  threads,
  selectedThreadId,
  onThreadSelect,
  onNewThread,
  onDeleteThread,
  onRefresh,
  isLoading,
}: ThreadsProps) {
  const { t } = useTranslation()
  const [showNewThreadDialog, setShowNewThreadDialog] = useState(false)
  const [newThreadTitle, setNewThreadTitle] = useState('')
  const [newThreadMessage, setNewThreadMessage] = useState('')
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  const handleNewThreadSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (newThreadTitle.trim()) {
      onNewThread(newThreadTitle.trim(), newThreadMessage.trim() || undefined)
      setNewThreadTitle('')
      setNewThreadMessage('')
      setShowNewThreadDialog(false)
    }
  }

  const handleDeleteClick = (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation()
    setDeleteConfirmId(threadId)
  }

  const handleDeleteConfirm = () => {
    if (deleteConfirmId) {
      onDeleteThread(deleteConfirmId)
      setDeleteConfirmId(null)
    }
  }

  const formatRelativeTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMins < 1) return t('messages.time.just_now')
    if (diffMins < 60)
      return t('messages.time.minutes_ago', { count: diffMins })
    if (diffHours < 24)
      return t('messages.time.hours_ago', { count: diffHours })
    if (diffDays < 7) return t('messages.time.days_ago', { count: diffDays })

    return date.toLocaleDateString()
  }

  const truncateMessage = (content: string, maxLength: number = 60) => {
    if (content.length <= maxLength) return content
    return content.substring(0, maxLength) + '...'
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('messages.threads')}
          </h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={onRefresh}
              disabled={isLoading}
              className="p-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 disabled:opacity-50"
              title={t('common.refresh')}
            >
              <svg
                className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                />
              </svg>
            </button>
          </div>
        </div>

        <button
          onClick={() => setShowNewThreadDialog(true)}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {t('messages.new_thread')}
        </button>
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-y-auto">
        {threads.length === 0 ? (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400">
            <div className="mb-4">
              <svg
                className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600"
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
            <p className="text-sm">{t('messages.no_threads')}</p>
            <p className="text-xs mt-1">{t('messages.create_first_thread')}</p>
          </div>
        ) : (
          <div className="space-y-1 p-2">
            {threads.map(thread => (
              <div
                key={thread.id}
                onClick={() => onThreadSelect(thread)}
                className={`
                  relative p-3 rounded-lg cursor-pointer transition-colors group
                  ${
                    selectedThreadId === thread.id
                      ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                  }
                `}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                      {thread.title}
                    </h3>
                    {thread.lastMessage && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 truncate">
                        {thread.lastMessage.type === 'user'
                          ? t('messages.you')
                          : t('messages.ai')}
                        : {truncateMessage(thread.lastMessage.content)}
                      </p>
                    )}
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      {formatRelativeTime(
                        thread.lastMessage?.created_at || thread.created_at
                      )}
                    </p>
                  </div>

                  <button
                    onClick={e => handleDeleteClick(e, thread.id)}
                    className="opacity-0 group-hover:opacity-100 ml-2 p-1 text-gray-400 hover:text-red-500 transition-all"
                    title={t('common.delete')}
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
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* New Thread Dialog */}
      {showNewThreadDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {t('messages.new_thread')}
            </h3>

            <form onSubmit={handleNewThreadSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('messages.thread_title')}
                </label>
                <input
                  type="text"
                  value={newThreadTitle}
                  onChange={e => setNewThreadTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                  placeholder={t('messages.thread_title_placeholder')}
                  required
                  autoFocus
                />
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  {t('messages.first_message')} ({t('common.optional')})
                </label>
                <textarea
                  value={newThreadMessage}
                  onChange={e => setNewThreadMessage(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                  placeholder={t('messages.first_message_placeholder')}
                  rows={3}
                />
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setShowNewThreadDialog(false)}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  {t('common.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      {deleteConfirmId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg max-w-sm w-full p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {t('messages.delete_thread_confirm_title')}
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {t('messages.delete_thread_confirm_message')}
            </p>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                {t('common.delete')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
