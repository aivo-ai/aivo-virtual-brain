import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { learnerClient } from '../../api/learnerClient'

interface ToneSelectProps {
  value: string
  onChange: (tone: string) => void
  onPreview?: (tone: string) => void
  disabled?: boolean
  label?: string
  error?: string
}

export const ToneSelect: React.FC<ToneSelectProps> = ({
  value,
  onChange,
  onPreview,
  disabled = false,
  label = 'Communication Tone',
  error,
}) => {
  const [availableTones, setAvailableTones] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [previewLoading, setPreviewLoading] = useState<string | null>(null)

  useEffect(() => {
    loadAvailableTones()
  }, [])

  const loadAvailableTones = async () => {
    try {
      setLoading(true)
      const tones = await learnerClient.getAvailableTones()
      setAvailableTones(tones)
    } catch (err) {
      console.error('Error loading tones:', err)
      // Fallback to default tones
      setAvailableTones(['formal', 'casual', 'nurturing', 'direct'])
    } finally {
      setLoading(false)
    }
  }

  const handlePreview = async (tone: string) => {
    if (!onPreview) return

    try {
      setPreviewLoading(tone)
      await onPreview(tone)
    } catch (err) {
      console.error('Error previewing tone:', err)
    } finally {
      setPreviewLoading(null)
    }
  }

  const getToneDescription = (tone: string) => {
    switch (tone) {
      case 'formal':
        return 'Structured and academic, perfect for focused learning sessions'
      case 'casual':
        return 'Relaxed and conversational, like learning with a study buddy'
      case 'nurturing':
        return 'Gentle and patient, provides extra emotional support'
      case 'direct':
        return 'Clear and to-the-point, efficient learning without fluff'
      default:
        return 'A unique communication style tailored to your preferences'
    }
  }

  const getToneIcon = (tone: string) => {
    switch (tone) {
      case 'formal':
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
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
            />
          </svg>
        )
      case 'casual':
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
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        )
      case 'nurturing':
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
              d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
            />
          </svg>
        )
      case 'direct':
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
              d="M13 7l5 5m0 0l-5 5m5-5H6"
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
              d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z"
            />
          </svg>
        )
    }
  }

  const getToneExample = (tone: string) => {
    switch (tone) {
      case 'formal':
        return '"Let us proceed with the analysis of this mathematical concept."'
      case 'casual':
        return '"Alright, let\'s dive into this math problem together!"'
      case 'nurturing':
        return "\"Don't worry, we'll work through this step by step. You're doing great!\""
      case 'direct':
        return '"Here\'s the formula. Apply it to solve the problem."'
      default:
        return '"Your personalized learning experience awaits."'
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {availableTones.map(tone => (
          <motion.div
            key={tone}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className={`relative cursor-pointer rounded-lg border-2 p-4 transition-all ${
              value === tone
                ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20'
                : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            onClick={() => !disabled && onChange(tone)}
          >
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div
                    className={`flex-shrink-0 p-2 rounded-lg ${
                      value === tone
                        ? 'bg-purple-100 dark:bg-purple-800 text-purple-600 dark:text-purple-400'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                    }`}
                  >
                    {getToneIcon(tone)}
                  </div>

                  <h3
                    className={`text-sm font-medium capitalize ${
                      value === tone
                        ? 'text-purple-900 dark:text-purple-100'
                        : 'text-gray-900 dark:text-white'
                    }`}
                  >
                    {tone}
                  </h3>
                </div>

                {onPreview && (
                  <button
                    type="button"
                    onClick={e => {
                      e.stopPropagation()
                      handlePreview(tone)
                    }}
                    disabled={disabled || previewLoading === tone}
                    className="text-xs text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-200 disabled:opacity-50"
                  >
                    {previewLoading === tone ? (
                      <div className="flex items-center space-x-1">
                        <div className="w-3 h-3 border border-purple-600 border-t-transparent rounded-full animate-spin"></div>
                        <span>Playing...</span>
                      </div>
                    ) : (
                      'Preview'
                    )}
                  </button>
                )}
              </div>

              <p
                className={`text-xs ${
                  value === tone
                    ? 'text-purple-700 dark:text-purple-300'
                    : 'text-gray-500 dark:text-gray-400'
                }`}
              >
                {getToneDescription(tone)}
              </p>

              <div
                className={`text-xs italic border-l-2 pl-3 ${
                  value === tone
                    ? 'border-purple-300 text-purple-600 dark:border-purple-600 dark:text-purple-400'
                    : 'border-gray-300 text-gray-500 dark:border-gray-600 dark:text-gray-400'
                }`}
              >
                {getToneExample(tone)}
              </div>
            </div>

            {value === tone && (
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute top-2 right-2 w-5 h-5 bg-purple-500 rounded-full flex items-center justify-center"
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
