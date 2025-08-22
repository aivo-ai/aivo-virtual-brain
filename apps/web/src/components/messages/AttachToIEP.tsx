import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { chatClient, Message } from '@/api/chatClient'

interface IEPEvidence {
  id: string
  title: string
  type:
    | 'observation'
    | 'assessment'
    | 'goal_progress'
    | 'intervention'
    | 'other'
  created_at: string
}

interface AttachToIEPProps {
  message: Message
  onClose: () => void
  onComplete: () => void
}

export function AttachToIEP({
  message,
  onClose,
  onComplete,
}: AttachToIEPProps) {
  const { t } = useTranslation()
  const [isLoading, setIsLoading] = useState(false)
  const [evidenceType, setEvidenceType] =
    useState<IEPEvidence['type']>('observation')
  const [title, setTitle] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [consentStatus, setConsentStatus] = useState<boolean | null>(null)

  useEffect(() => {
    // Pre-fill title with a summary of the message
    const messagePreview =
      message.content.length > 50
        ? message.content.substring(0, 50) + '...'
        : message.content
    setTitle(`AI Response: ${messagePreview}`)

    // Check consent status
    checkConsentStatus()
  }, [message])

  const checkConsentStatus = async () => {
    try {
      const hasConsent = await chatClient.checkIEPAttachmentConsent()
      setConsentStatus(hasConsent)
    } catch (err) {
      console.error('Failed to check consent status:', err)
      setConsentStatus(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim() || isLoading) return

    setIsLoading(true)
    setError(null)

    try {
      await chatClient.attachMessageToIEP(message.id, {
        title: title.trim(),
        type: evidenceType,
        notes: notes.trim() || undefined,
      })

      onComplete()
      onClose()
    } catch (err) {
      console.error('Failed to attach to IEP:', err)
      setError(t('messages.errors.iep_attachment_failed'))
    } finally {
      setIsLoading(false)
    }
  }

  const evidenceTypeOptions = [
    {
      value: 'observation',
      label: t('messages.iep.evidence_types.observation'),
    },
    { value: 'assessment', label: t('messages.iep.evidence_types.assessment') },
    {
      value: 'goal_progress',
      label: t('messages.iep.evidence_types.goal_progress'),
    },
    {
      value: 'intervention',
      label: t('messages.iep.evidence_types.intervention'),
    },
    { value: 'other', label: t('messages.iep.evidence_types.other') },
  ]

  if (consentStatus === null) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-gray-300 border-t-blue-600 rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-gray-600 dark:text-gray-400">
              {t('messages.iep.checking_consent')}
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (consentStatus === false) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg max-w-md w-full p-6">
          <div className="text-center">
            <div className="mb-4">
              <svg
                className="w-12 h-12 mx-auto text-yellow-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 19.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>

            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              {t('messages.iep.consent_required_title')}
            </h3>

            <p className="text-gray-600 dark:text-gray-400 mb-6">
              {t('messages.iep.consent_required_message')}
            </p>

            <div className="flex justify-center space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition-colors"
              >
                {t('common.close')}
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-lg w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {t('messages.attach_to_iep')}
            </h3>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <svg
                className="w-6 h-6"
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

          {/* Message Preview */}
          <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
            <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
              {t('messages.iep.message_to_attach')}
            </h4>
            <div className="text-sm text-gray-600 dark:text-gray-400 max-h-24 overflow-y-auto">
              {message.content}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {/* Evidence Type */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('messages.iep.evidence_type')}
              </label>
              <select
                value={evidenceType}
                onChange={e =>
                  setEvidenceType(e.target.value as IEPEvidence['type'])
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                required
              >
                {evidenceTypeOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Title */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('messages.iep.evidence_title')}
              </label>
              <input
                type="text"
                value={title}
                onChange={e => setTitle(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                placeholder={t('messages.iep.evidence_title_placeholder')}
                required
                maxLength={200}
              />
            </div>

            {/* Additional Notes */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('messages.iep.additional_notes')} ({t('common.optional')})
              </label>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                placeholder={t('messages.iep.additional_notes_placeholder')}
                rows={3}
                maxLength={500}
              />
            </div>

            {/* Privacy Notice */}
            <div className="mb-6 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
              <div className="flex items-start space-x-2">
                <svg
                  className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <div className="text-sm text-blue-700 dark:text-blue-300">
                  <p className="font-medium mb-1">
                    {t('messages.iep.privacy_notice_title')}
                  </p>
                  <p>{t('messages.iep.privacy_notice_text')}</p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                disabled={isLoading}
              >
                {t('common.cancel')}
              </button>
              <button
                type="submit"
                disabled={isLoading || !title.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white rounded-lg transition-colors disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    <span>{t('messages.iep.attaching')}</span>
                  </div>
                ) : (
                  t('messages.iep.attach_to_iep')
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
