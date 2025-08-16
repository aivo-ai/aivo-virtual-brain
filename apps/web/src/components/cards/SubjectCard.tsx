import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { SubjectAssignment, teacherClient } from '../../api/teacherClient'

interface SubjectCardProps {
  assignment: SubjectAssignment & { learnerName?: string }
  onUpdate?: (updatedAssignment: Partial<SubjectAssignment>) => void
  compact?: boolean
}

export const SubjectCard: React.FC<SubjectCardProps> = ({
  assignment,
  onUpdate,
  compact = false,
}) => {
  const [showDetails, setShowDetails] = useState(false)
  const [loading, setLoading] = useState(false)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
      case 'paused':
        return 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'
      case 'completed':
        return 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200'
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
    }
  }

  const getProgressColor = (progress: number) => {
    if (progress >= 80) return 'bg-green-500'
    if (progress >= 60) return 'bg-yellow-500'
    if (progress >= 40) return 'bg-orange-500'
    return 'bg-red-500'
  }

  const getSubjectIcon = (subjectType: string) => {
    switch (subjectType) {
      case 'ELA':
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
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
            />
          </svg>
        )
      case 'Math':
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
              d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
            />
          </svg>
        )
      case 'Science':
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
              d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
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
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
            />
          </svg>
        )
    }
  }

  const handleStatusChange = async (
    newStatus: 'active' | 'paused' | 'completed'
  ) => {
    try {
      setLoading(true)
      const updatedAssignment = { status: newStatus }
      await teacherClient.updateSubjectAssignment(
        assignment.learnerId,
        assignment.id,
        updatedAssignment
      )
      onUpdate?.(updatedAssignment)
    } catch (err) {
      console.error('Error updating assignment status:', err)
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  const getDaysUntilCompletion = () => {
    if (!assignment.estimatedCompletion) return null
    const completion = new Date(assignment.estimatedCompletion)
    const now = new Date()
    const diffTime = completion.getTime() - now.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays
  }

  const daysUntilCompletion = getDaysUntilCompletion()

  return (
    <motion.div
      layout
      className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow ${
        compact ? 'p-4' : 'p-6'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="flex-shrink-0">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center text-blue-600 dark:text-blue-400">
              {getSubjectIcon(assignment.subjectType)}
            </div>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {assignment.customSubjectName || assignment.subjectType}
            </h3>
            {assignment.learnerName && (
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {assignment.learnerName}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span
            className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(assignment.status)}`}
          >
            {assignment.status}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Progress
          </span>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {assignment.progressPercentage}%
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${getProgressColor(assignment.progressPercentage)}`}
            style={{ width: `${assignment.progressPercentage}%` }}
          />
        </div>
      </div>

      {/* Current Unit & Next Milestone */}
      {!compact && (
        <div className="space-y-2 mb-4">
          {assignment.currentUnit && (
            <div className="flex items-center text-sm">
              <svg
                className="w-4 h-4 text-gray-400 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <span className="text-gray-600 dark:text-gray-400">
                Current: {assignment.currentUnit}
              </span>
            </div>
          )}

          {assignment.nextMilestone && (
            <div className="flex items-center text-sm">
              <svg
                className="w-4 h-4 text-gray-400 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                />
              </svg>
              <span className="text-gray-600 dark:text-gray-400">
                Next: {assignment.nextMilestone}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Timeline Info */}
      <div className="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400 mb-4">
        <span>Started {formatDate(assignment.assignedAt)}</span>
        {daysUntilCompletion !== null && (
          <span
            className={
              daysUntilCompletion < 7
                ? 'text-orange-600 dark:text-orange-400'
                : ''
            }
          >
            {daysUntilCompletion > 0
              ? `${daysUntilCompletion} days left`
              : daysUntilCompletion === 0
                ? 'Due today'
                : `${Math.abs(daysUntilCompletion)} days overdue`}
          </span>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {assignment.status === 'active' && (
            <button
              onClick={() => handleStatusChange('paused')}
              disabled={loading}
              className="px-3 py-1 text-xs bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 rounded hover:bg-yellow-200 dark:hover:bg-yellow-800 transition-colors disabled:opacity-50"
            >
              Pause
            </button>
          )}

          {assignment.status === 'paused' && (
            <button
              onClick={() => handleStatusChange('active')}
              disabled={loading}
              className="px-3 py-1 text-xs bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded hover:bg-green-200 dark:hover:bg-green-800 transition-colors disabled:opacity-50"
            >
              Resume
            </button>
          )}

          {assignment.status !== 'completed' &&
            assignment.progressPercentage >= 100 && (
              <button
                onClick={() => handleStatusChange('completed')}
                disabled={loading}
                className="px-3 py-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors disabled:opacity-50"
              >
                Mark Complete
              </button>
            )}
        </div>

        <button
          onClick={() => setShowDetails(!showDetails)}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
        >
          <svg
            className={`w-4 h-4 transform transition-transform ${showDetails ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
      </div>

      {/* Expandable Details */}
      {showDetails && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700"
        >
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">
                Assignment ID:
              </span>
              <span className="text-gray-900 dark:text-white font-mono text-xs">
                {assignment.id}
              </span>
            </div>

            <div className="flex justify-between">
              <span className="text-gray-600 dark:text-gray-400">
                Subject Type:
              </span>
              <span className="text-gray-900 dark:text-white">
                {assignment.subjectType}
              </span>
            </div>

            {assignment.customSubjectName && (
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Custom Name:
                </span>
                <span className="text-gray-900 dark:text-white">
                  {assignment.customSubjectName}
                </span>
              </div>
            )}

            {assignment.estimatedCompletion && (
              <div className="flex justify-between">
                <span className="text-gray-600 dark:text-gray-400">
                  Est. Completion:
                </span>
                <span className="text-gray-900 dark:text-white">
                  {formatDate(assignment.estimatedCompletion)}
                </span>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </motion.div>
  )
}
