import React, { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { BrainPersona } from './BrainPersona.tsx'
import {
  learnerClient,
  type LearnerProfile,
  type TeacherAssignment,
  type GradeBandPreview,
} from '../../api/learnerClient'

interface ProfileProps {
  learnerId: string
  userRole: 'guardian' | 'teacher' | 'learner'
}

export const Profile: React.FC<ProfileProps> = ({ learnerId, userRole }) => {
  const [profile, setProfile] = useState<LearnerProfile | null>(null)
  const [teachers, setTeachers] = useState<TeacherAssignment[]>([])
  const [gradeBandPreview, setGradeBandPreview] =
    useState<GradeBandPreview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<
    'overview' | 'persona' | 'preferences'
  >('overview')

  const loadProfileData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const [profileData, teachersData, gradePreview] = await Promise.all([
        learnerClient.getLearnerProfile(learnerId),
        learnerClient.getTeacherAssignments(learnerId),
        learnerClient.getGradeBandPreview(learnerId),
      ])

      setProfile(profileData)
      setTeachers(teachersData)
      setGradeBandPreview(gradePreview)
    } catch (err) {
      console.error('Error loading profile data:', err)
      setError('Failed to load profile data')
    } finally {
      setLoading(false)
    }
  }, [learnerId])

  useEffect(() => {
    loadProfileData()
  }, [loadProfileData])

  const handlePersonaUpdate = async () => {
    // Reload profile to get updated persona data
    await loadProfileData()
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6" data-testid="learner-profile">
        <div className="animate-pulse space-y-6">
          <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded"></div>
          <div className="h-32 bg-gray-200 dark:bg-gray-700 rounded"></div>
          <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6" data-testid="learner-profile">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
          <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">
            Error Loading Profile
          </h3>
          <p
            className="text-red-700 dark:text-red-300 mb-4"
            data-testid="network-error"
          >
            {error}
          </p>
          <button
            onClick={loadProfileData}
            data-testid="retry-btn"
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="max-w-4xl mx-auto p-6" data-testid="learner-profile">
        <div className="text-center text-gray-500 dark:text-gray-400">
          No profile data available
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto p-6" data-testid="learner-profile">
      {/* Profile Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1
              className="text-2xl font-bold text-gray-900 dark:text-white"
              data-testid="learner-name"
            >
              {profile.firstName} {profile.lastName}
            </h1>
            <p
              className="text-gray-600 dark:text-gray-400"
              data-testid="learner-grade"
            >
              Grade {profile.gradeLevel} • {profile.school}
            </p>
            <p
              className="text-sm text-gray-500 dark:text-gray-500"
              data-testid="enrollment-date"
            >
              Enrolled: {new Date(profile.enrollmentDate).toLocaleDateString()}
            </p>
          </div>

          {/* Grade Band Preview */}
          {gradeBandPreview && (
            <div className="text-right" data-testid="grade-band-preview">
              <div className="flex items-center space-x-2 mb-2">
                <button
                  onClick={() => learnerClient.getGradeBandPreview(learnerId)}
                  disabled={gradeBandPreview.currentGrade <= 1}
                  data-testid="prev-grade-btn"
                  className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                >
                  ←
                </button>
                <span
                  className="text-sm font-medium"
                  data-testid="preview-grade-level"
                >
                  Grade {gradeBandPreview.previewGrade}
                  {gradeBandPreview.previewGrade ===
                    gradeBandPreview.currentGrade && (
                    <span
                      className="ml-1 text-blue-600"
                      data-testid="current-grade-indicator"
                    >
                      (Current)
                    </span>
                  )}
                </span>
                <button
                  onClick={() => learnerClient.getGradeBandPreview(learnerId)}
                  disabled={gradeBandPreview.currentGrade >= 12}
                  data-testid="next-grade-btn"
                  className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-50"
                >
                  →
                </button>
              </div>
              <button
                onClick={() => learnerClient.getGradeBandPreview(learnerId)}
                data-testid="current-grade-btn"
                className="text-xs text-blue-600 hover:text-blue-800"
              >
                Return to Current
              </button>
            </div>
          )}
        </div>

        {/* Navigation Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'overview'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Overview
            </button>
            <button
              onClick={() => setActiveTab('persona')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'persona'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Brain Persona
            </button>
            <button
              onClick={() => setActiveTab('preferences')}
              data-testid="preferences-tab"
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'preferences'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Preferences
            </button>
          </nav>
        </div>
      </motion.div>

      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3 }}
      >
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Teacher Assignments */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Teacher Assignments
                </h2>
                {(userRole === 'teacher' || userRole === 'guardian') && (
                  <button
                    data-testid="manage-teachers-btn"
                    className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    Manage Teachers
                  </button>
                )}
              </div>

              <div
                className="grid grid-cols-1 md:grid-cols-2 gap-4"
                data-testid="teacher-assignments"
              >
                {teachers.map(teacher => (
                  <div
                    key={teacher.teacherId}
                    data-testid="teacher-card"
                    className="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h3
                          className="font-medium text-gray-900 dark:text-white"
                          data-testid="teacher-name"
                        >
                          {teacher.teacherName}
                        </h3>
                        <p
                          className="text-sm text-gray-600 dark:text-gray-400"
                          data-testid="teacher-subject"
                        >
                          {teacher.subject}
                        </p>
                        <p
                          className="text-xs text-gray-500"
                          data-testid="teacher-email"
                        >
                          {teacher.email}
                        </p>
                        <p
                          className="text-xs text-gray-500"
                          data-testid="assignment-date"
                        >
                          Assigned:{' '}
                          {new Date(teacher.assignedDate).toLocaleDateString()}
                        </p>
                      </div>
                      {teacher.status === 'active' && (
                        <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
                          Active
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'persona' && (
          <BrainPersona
            learnerId={learnerId}
            userRole={userRole}
            onUpdate={handlePersonaUpdate}
          />
        )}

        {activeTab === 'preferences' && (
          <div className="space-y-6">
            {/* Accessibility Settings */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2
                className="text-lg font-semibold text-gray-900 dark:text-white mb-4"
                data-testid="accessibility-section"
              >
                Accessibility Options
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Font Size
                  </label>
                  <select
                    data-testid="font-size-select"
                    defaultValue={
                      profile.preferences?.accessibilityOptions?.fontSize ||
                      'medium'
                    }
                    className="border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 bg-white dark:bg-gray-700"
                  >
                    <option value="small">Small</option>
                    <option value="medium">Medium</option>
                    <option value="large">Large</option>
                    <option value="extra-large">Extra Large</option>
                  </select>
                </div>

                <div className="space-y-3">
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      data-testid="high-contrast-toggle"
                      defaultChecked={
                        profile.preferences?.accessibilityOptions?.highContrast
                      }
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      High Contrast Mode
                    </span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      data-testid="screen-reader-toggle"
                      defaultChecked={
                        profile.preferences?.accessibilityOptions?.screenReader
                      }
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Screen Reader Support
                    </span>
                  </label>

                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      data-testid="reduced-motion-toggle"
                      defaultChecked={
                        profile.preferences?.accessibilityOptions?.reducedMotion
                      }
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                      Reduced Motion
                    </span>
                  </label>
                </div>
              </div>
            </div>

            {/* Notification Settings */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
              <h2
                className="text-lg font-semibold text-gray-900 dark:text-white mb-4"
                data-testid="notification-section"
              >
                Notification Preferences
              </h2>

              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    data-testid="email-notifications-toggle"
                    defaultChecked={
                      profile.preferences?.notificationSettings?.email
                    }
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                    Email Notifications
                  </span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    data-testid="push-notifications-toggle"
                    defaultChecked={
                      profile.preferences?.notificationSettings?.push
                    }
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                    Push Notifications
                  </span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    data-testid="assignment-reminders-toggle"
                    defaultChecked={
                      profile.preferences?.notificationSettings
                        ?.assignmentReminders
                    }
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                    Assignment Reminders
                  </span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    data-testid="progress-updates-toggle"
                    defaultChecked={
                      profile.preferences?.notificationSettings?.progressUpdates
                    }
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                    Progress Updates
                  </span>
                </label>
              </div>

              <div className="mt-6">
                <button
                  data-testid="save-preferences-btn"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors"
                >
                  Save Preferences
                </button>
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}
