import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { Learner, teacherClient } from '../../api/teacherClient'

interface LearnerCardProps {
  learner: Learner
  onUpdate?: (updatedLearner: Learner) => void
  compact?: boolean
}

export const LearnerCard: React.FC<LearnerCardProps> = ({
  learner,
  onUpdate,
  compact = false,
}) => {
  const [showQuickActions, setShowQuickActions] = useState(false)
  const [loading, setLoading] = useState(false)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
      case 'inactive':
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
      case 'pending':
        return 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
    }
  }

  const getProgressColor = (progress: number) => {
    if (progress >= 80) return 'bg-green-500'
    if (progress >= 60) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getGradeDisplay = (gradeLevel: string) => {
    const grade = gradeLevel.toLowerCase()
    if (grade === 'k') return 'Kindergarten'
    if (grade === 'pre-k') return 'Pre-K'
    return `Grade ${gradeLevel}`
  }

  const calculateAge = (dateOfBirth: string) => {
    const today = new Date()
    const birthDate = new Date(dateOfBirth)
    let age = today.getFullYear() - birthDate.getFullYear()
    const monthDiff = today.getMonth() - birthDate.getMonth()

    if (
      monthDiff < 0 ||
      (monthDiff === 0 && today.getDate() < birthDate.getDate())
    ) {
      age--
    }

    return age
  }

  const handleStatusChange = async (
    newStatus: 'active' | 'inactive' | 'pending'
  ) => {
    if (loading) return

    setLoading(true)
    try {
      const updatedLearner = await teacherClient.updateLearnerStatus(
        learner.id,
        newStatus
      )
      onUpdate?.(updatedLearner)
    } catch (error) {
      console.error('Failed to update learner status:', error)
    } finally {
      setLoading(false)
      setShowQuickActions(false)
    }
  }

  const handleSendMessage = async () => {
    // This would typically open a message modal
    console.log('Send message to parent for learner:', learner.id)
  }

  const handleGenerateReport = async () => {
    setLoading(true)
    try {
      await teacherClient.generateProgressReport(learner.id, {
        format: 'pdf',
        includeSubjects: learner.subjects.map(s => s.subjectType),
      })
    } catch (error) {
      console.error('Failed to generate report:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatLastActivity = (lastActivity?: string) => {
    if (!lastActivity) return 'No recent activity'

    const date = new Date(lastActivity)
    const now = new Date()
    const diffDays = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    )

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    return date.toLocaleDateString()
  }

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
      >
        <div className="flex items-center space-x-3">
          {learner.profileImage ? (
            <img
              src={learner.profileImage}
              alt={`${learner.firstName} ${learner.lastName}`}
              className="w-10 h-10 rounded-full object-cover"
            />
          ) : (
            <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-medium">
              {learner.firstName[0]}
              {learner.lastName[0]}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {learner.firstName} {learner.lastName}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {getGradeDisplay(learner.gradeLevel)} • {learner.subjects.length}{' '}
              subjects
            </p>
          </div>
          <div className="flex-shrink-0">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(learner.status)}`}
            >
              {learner.status}
            </span>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden hover:shadow-xl transition-shadow"
    >
      {/* Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            {learner.profileImage ? (
              <img
                src={learner.profileImage}
                alt={`${learner.firstName} ${learner.lastName}`}
                className="w-16 h-16 rounded-full object-cover"
              />
            ) : (
              <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center text-white font-semibold text-xl">
                {learner.firstName[0]}
                {learner.lastName[0]}
              </div>
            )}
            <div>
              <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                {learner.firstName} {learner.lastName}
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                {getGradeDisplay(learner.gradeLevel)} • Age{' '}
                {calculateAge(learner.dateOfBirth)}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Student since{' '}
                {new Date(learner.assignedAt).toLocaleDateString()}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(learner.status)}`}
            >
              {learner.status}
            </span>
            <div className="relative">
              <button
                onClick={() => setShowQuickActions(!showQuickActions)}
                className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
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

              {showQuickActions && (
                <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-700 rounded-md shadow-lg border border-gray-200 dark:border-gray-600 z-10">
                  <div className="py-1">
                    <Link
                      to={`/teacher/learners/${learner.id}`}
                      className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
                    >
                      View Details
                    </Link>
                    <button
                      onClick={handleSendMessage}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
                    >
                      Message Parent
                    </button>
                    <button
                      onClick={handleGenerateReport}
                      disabled={loading}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50"
                    >
                      Generate Report
                    </button>
                    <div className="border-t border-gray-200 dark:border-gray-600 my-1"></div>
                    <button
                      onClick={() => handleStatusChange('active')}
                      disabled={loading || learner.status === 'active'}
                      className="w-full text-left px-4 py-2 text-sm text-green-700 dark:text-green-400 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50"
                    >
                      Mark Active
                    </button>
                    <button
                      onClick={() => handleStatusChange('inactive')}
                      disabled={loading || learner.status === 'inactive'}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50"
                    >
                      Mark Inactive
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Progress Overview */}
      <div className="p-6">
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-gray-900 dark:text-white">
              Overall Progress
            </h4>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {learner.academicProgress.overallScore}%
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
            <div
              className={`h-2 rounded-full ${getProgressColor(learner.academicProgress.overallScore)}`}
              style={{ width: `${learner.academicProgress.overallScore}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
            <span>
              Grade Equivalent: {learner.academicProgress.gradeEquivalent}
            </span>
            <span>
              Last Activity: {formatLastActivity(learner.lastActivity)}
            </span>
          </div>
        </div>

        {/* Subjects */}
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
            Subjects ({learner.subjects.length})
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {learner.subjects.slice(0, 4).map(subject => (
              <div
                key={subject.id}
                className="bg-gray-50 dark:bg-gray-700 rounded-lg p-3"
              >
                <div className="flex items-center justify-between mb-1">
                  <h5 className="text-sm font-medium text-gray-900 dark:text-white">
                    {subject.customSubjectName || subject.subjectType}
                  </h5>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {subject.progressPercentage}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1">
                  <div
                    className={`h-1 rounded-full ${getProgressColor(subject.progressPercentage)}`}
                    style={{ width: `${subject.progressPercentage}%` }}
                  />
                </div>
                <div className="flex items-center justify-between mt-1">
                  <span
                    className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${
                      subject.status === 'active'
                        ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
                        : subject.status === 'paused'
                          ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'
                          : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
                    }`}
                  >
                    {subject.status}
                  </span>
                  {subject.currentUnit && (
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {subject.currentUnit}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
          {learner.subjects.length > 4 && (
            <Link
              to={`/teacher/learners/${learner.id}/subjects`}
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline mt-2 inline-block"
            >
              View all {learner.subjects.length} subjects →
            </Link>
          )}
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {learner.academicProgress.totalHoursLogged}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Total Hours
            </p>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {learner.academicProgress.completedAssignments}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Completed
            </p>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {
                learner.approvalHistory.filter(a => a.status === 'pending')
                  .length
              }
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Pending</p>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="px-6 py-4 bg-gray-50 dark:bg-gray-700 border-t border-gray-200 dark:border-gray-600">
        <div className="flex items-center justify-between">
          <div className="flex space-x-2">
            <Link
              to={`/teacher/learners/${learner.id}`}
              className="px-3 py-1.5 text-sm font-medium text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900 rounded-md hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
            >
              View Details
            </Link>
            <Link
              to={`/teacher/learners/${learner.id}/subjects`}
              className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-500 transition-colors"
            >
              Manage Subjects
            </Link>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {learner.parentEmail && <span>Parent: {learner.parentEmail}</span>}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
