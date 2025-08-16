import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { learnerClient } from '../../api/learnerClient'

interface VoiceSelectProps {
  value: string
  onChange: (voice: string) => void
  onPreview?: (voice: string) => void
  disabled?: boolean
  label?: string
  error?: string
}

export const VoiceSelect: React.FC<VoiceSelectProps> = ({
  value,
  onChange,
  onPreview,
  disabled = false,
  label = 'Voice Type',
  error,
}) => {
  const [availableVoices, setAvailableVoices] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [previewLoading, setPreviewLoading] = useState<string | null>(null)

  useEffect(() => {
    loadAvailableVoices()
  }, [])

  const loadAvailableVoices = async () => {
    try {
      setLoading(true)
      const voices = await learnerClient.getAvailableVoices()
      setAvailableVoices(voices)
    } catch (err) {
      console.error('Error loading voices:', err)
      // Fallback to default voices
      setAvailableVoices(['friendly', 'encouraging', 'professional', 'playful'])
    } finally {
      setLoading(false)
    }
  }

  const handlePreview = async (voice: string) => {
    if (!onPreview) return

    try {
      setPreviewLoading(voice)
      await onPreview(voice)
    } catch (err) {
      console.error('Error previewing voice:', err)
    } finally {
      setPreviewLoading(null)
    }
  }

  const getVoiceDescription = (voice: string) => {
    switch (voice) {
      case 'friendly':
        return 'Warm and approachable, like chatting with a good friend'
      case 'encouraging':
        return 'Supportive and motivating, celebrates your achievements'
      case 'professional':
        return 'Clear and focused, perfect for serious learning'
      case 'playful':
        return 'Fun and energetic, makes learning feel like a game'
      default:
        return 'A unique voice personality for your learning journey'
    }
  }

  const getVoiceIcon = (voice: string) => {
    switch (voice) {
      case 'friendly':
        return (
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
              d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        )
      case 'encouraging':
        return (
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
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
        )
      case 'professional':
        return (
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
              d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2-2v2m8 0V6a2 2 0 012 2v6a2 2 0 01-2 2H8a2 2 0 01-2-2V8a2 2 0 012-2z"
            />
          </svg>
        )
      case 'playful':
        return (
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
              d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.196-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
            />
          </svg>
        )
      default:
        return (
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
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            />
          </svg>
        )
    }
  }

  if (loading) {
    return (
      <div className="space-y-2">
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
        <div className="animate-pulse bg-gray-200 dark:bg-gray-700 rounded-md h-12"></div>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
      </label>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {availableVoices.map(voice => (
          <motion.div
            key={voice}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`relative cursor-pointer rounded-lg border-2 p-4 transition-all ${
              value === voice
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            onClick={() => !disabled && onChange(voice)}
          >
            <div className="flex items-start space-x-3">
              <div
                className={`flex-shrink-0 p-2 rounded-lg ${
                  value === voice
                    ? 'bg-blue-100 dark:bg-blue-800 text-blue-600 dark:text-blue-400'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                }`}
              >
                {getVoiceIcon(voice)}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <h3
                    className={`text-sm font-medium capitalize ${
                      value === voice
                        ? 'text-blue-900 dark:text-blue-100'
                        : 'text-gray-900 dark:text-white'
                    }`}
                  >
                    {voice}
                  </h3>

                  {onPreview && (
                    <button
                      type="button"
                      onClick={e => {
                        e.stopPropagation()
                        handlePreview(voice)
                      }}
                      disabled={disabled || previewLoading === voice}
                      className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 disabled:opacity-50"
                    >
                      {previewLoading === voice ? (
                        <div className="flex items-center space-x-1">
                          <div className="w-3 h-3 border border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                          <span>Playing...</span>
                        </div>
                      ) : (
                        'Preview'
                      )}
                    </button>
                  )}
                </div>

                <p
                  className={`text-xs mt-1 ${
                    value === voice
                      ? 'text-blue-700 dark:text-blue-300'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {getVoiceDescription(voice)}
                </p>
              </div>
            </div>

            {value === voice && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute top-2 right-2 w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center"
              >
                <svg
                  className="w-3 h-3 text-white"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              </motion.div>
            )}
          </motion.div>
        ))}
      </div>

      {error && (
        <p className="text-sm text-red-600 dark:text-red-400 mt-1">{error}</p>
      )}
    </div>
  )
}
