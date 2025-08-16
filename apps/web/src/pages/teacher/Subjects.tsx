import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import {
  teacherClient,
  Learner,
  SubjectAssignment,
} from '../../api/teacherClient'
import { SubjectCard } from '../../components/cards/SubjectCard'

interface SubjectFilter {
  learner: 'all' | string
  status: 'all' | 'active' | 'paused' | 'completed'
  subject: 'all' | string
}

export const Subjects: React.FC = () => {
  const [learners, setLearners] = useState<Learner[]>([])
  const [assignments, setAssignments] = useState<SubjectAssignment[]>([])
  const [filteredAssignments, setFilteredAssignments] = useState<
    SubjectAssignment[]
  >([])
  const [availableSubjects, setAvailableSubjects] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<SubjectFilter>({
    learner: 'all',
    status: 'all',
    subject: 'all',
  })
  const [showAssignModal, setShowAssignModal] = useState(false)
  const [selectedLearner, setSelectedLearner] = useState<string>('')
  const [newAssignment, setNewAssignment] = useState({
    subjectType: '',
    customSubjectName: '',
    weeklyGoalHours: 5,
  })

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    applyFilters()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assignments, filters])

  const loadData = async () => {
    try {
      setLoading(true)
      const [learnersData, subjectsData] = await Promise.all([
        teacherClient.getAssignedLearners(),
        teacherClient.getAvailableSubjects(),
      ])

      setLearners(learnersData)
      setAvailableSubjects(subjectsData)

      // Flatten all subject assignments
      const allAssignments = learnersData.flatMap(learner =>
        learner.subjects.map(subject => ({
          ...subject,
          learnerName: `${learner.firstName} ${learner.lastName}`,
        }))
      )
      setAssignments(allAssignments)
    } catch (err) {
      setError('Failed to load subject data')
      console.error('Error loading subjects:', err)
    } finally {
      setLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = assignments

    // Learner filter
    if (filters.learner !== 'all') {
      filtered = filtered.filter(
        assignment => assignment.learnerId === filters.learner
      )
    }

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(
        assignment => assignment.status === filters.status
      )
    }

    // Subject filter
    if (filters.subject !== 'all') {
      filtered = filtered.filter(
        assignment => assignment.subjectType === filters.subject
      )
    }

    setFilteredAssignments(filtered)
  }

  const handleAssignSubject = async () => {
    if (!selectedLearner || !newAssignment.subjectType) return

    try {
      setLoading(true)
      await teacherClient.assignSubjectToLearner(selectedLearner, {
        subjectType: newAssignment.subjectType,
        customSubjectName: newAssignment.customSubjectName || undefined,
        weeklyGoalHours: newAssignment.weeklyGoalHours,
      })

      setShowAssignModal(false)
      setSelectedLearner('')
      setNewAssignment({
        subjectType: '',
        customSubjectName: '',
        weeklyGoalHours: 5,
      })
      await loadData() // Refresh data
    } catch (err) {
      setError('Failed to assign subject')
      console.error('Error assigning subject:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateAssignment = async (
    assignmentId: string,
    updates: Partial<SubjectAssignment>
  ) => {
    try {
      const assignment = assignments.find(a => a.id === assignmentId)
      if (!assignment) return

      await teacherClient.updateSubjectAssignment(
        assignment.learnerId,
        assignmentId,
        updates
      )
      await loadData() // Refresh data
    } catch (err) {
      setError('Failed to update assignment')
      console.error('Error updating assignment:', err)
    }
  }

  const getSubjectCounts = () => {
    return availableSubjects.reduce(
      (counts, subject) => {
        counts[subject] = assignments.filter(
          a => a.subjectType === subject && a.status === 'active'
        ).length
        return counts
      },
      {} as Record<string, number>
    )
  }

  const getProgressStats = () => {
    const activeAssignments = assignments.filter(a => a.status === 'active')
    const avgProgress =
      activeAssignments.length > 0
        ? activeAssignments.reduce((sum, a) => sum + a.progressPercentage, 0) /
          activeAssignments.length
        : 0

    return {
      total: assignments.length,
      active: activeAssignments.length,
      completed: assignments.filter(a => a.status === 'completed').length,
      averageProgress: Math.round(avgProgress),
    }
  }

  const stats = getProgressStats()
  const subjectCounts = getSubjectCounts()

  if (loading && assignments.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                Subject Management
              </h1>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Assign subjects to learners and track their progress
              </p>
            </div>
            <button
              onClick={() => setShowAssignModal(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors flex items-center"
            >
              <svg
                className="w-4 h-4 mr-2"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                />
              </svg>
              Assign Subject
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center">
                  <svg
                    className="w-4 h-4 text-blue-600 dark:text-blue-400"
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
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Total Assignments
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {stats.total}
                  </dd>
                </dl>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center">
                  <svg
                    className="w-4 h-4 text-green-600 dark:text-green-400"
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
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Active Subjects
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {stats.active}
                  </dd>
                </dl>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900 rounded-full flex items-center justify-center">
                  <svg
                    className="w-4 h-4 text-purple-600 dark:text-purple-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Completed
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {stats.completed}
                  </dd>
                </dl>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-yellow-100 dark:bg-yellow-900 rounded-full flex items-center justify-center">
                  <svg
                    className="w-4 h-4 text-yellow-600 dark:text-yellow-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                    />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Avg Progress
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {stats.averageProgress}%
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Learner Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Learner
              </label>
              <select
                value={filters.learner}
                onChange={e =>
                  setFilters(prev => ({ ...prev, learner: e.target.value }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Learners</option>
                {learners.map(learner => (
                  <option key={learner.id} value={learner.id}>
                    {learner.firstName} {learner.lastName}
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Status
              </label>
              <select
                value={filters.status}
                onChange={e =>
                  setFilters(prev => ({
                    ...prev,
                    status: e.target.value as SubjectFilter['status'],
                  }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            {/* Subject Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Subject
              </label>
              <select
                value={filters.subject}
                onChange={e =>
                  setFilters(prev => ({ ...prev, subject: e.target.value }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Subjects</option>
                {availableSubjects.map(subject => (
                  <option key={subject} value={subject}>
                    {subject} ({subjectCounts[subject] || 0})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mb-6 bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 rounded-md p-4">
            <div className="text-red-800 dark:text-red-200">{error}</div>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Subject Assignments Grid */}
        {filteredAssignments.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredAssignments.map(assignment => (
              <FadeInWhenVisible key={assignment.id}>
                <SubjectCard
                  assignment={assignment}
                  onUpdate={(updatedAssignment: Partial<SubjectAssignment>) =>
                    handleUpdateAssignment(assignment.id, updatedAssignment)
                  }
                />
              </FadeInWhenVisible>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
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
            <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
              No subject assignments found
            </h3>
            <p className="mt-2 text-gray-500 dark:text-gray-400">
              No assignments match your current filters. Try adjusting your
              search criteria or assign new subjects.
            </p>
          </div>
        )}
      </div>

      {/* Assign Subject Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Assign Subject to Learner
            </h3>

            <div className="space-y-4">
              {/* Learner Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Select Learner
                </label>
                <select
                  value={selectedLearner}
                  onChange={e => setSelectedLearner(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  required
                >
                  <option value="">Choose a learner...</option>
                  {learners.map(learner => (
                    <option key={learner.id} value={learner.id}>
                      {learner.firstName} {learner.lastName} (Grade{' '}
                      {learner.gradeLevel})
                    </option>
                  ))}
                </select>
              </div>

              {/* Subject Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Subject
                </label>
                <select
                  value={newAssignment.subjectType}
                  onChange={e =>
                    setNewAssignment(prev => ({
                      ...prev,
                      subjectType: e.target.value,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  required
                >
                  <option value="">Choose a subject...</option>
                  {availableSubjects.map(subject => (
                    <option key={subject} value={subject}>
                      {subject}
                    </option>
                  ))}
                </select>
              </div>

              {/* Custom Subject Name */}
              {newAssignment.subjectType === 'Other' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Custom Subject Name
                  </label>
                  <input
                    type="text"
                    value={newAssignment.customSubjectName}
                    onChange={e =>
                      setNewAssignment(prev => ({
                        ...prev,
                        customSubjectName: e.target.value,
                      }))
                    }
                    placeholder="Enter custom subject name..."
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                  />
                </div>
              )}

              {/* Weekly Goal Hours */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Weekly Goal Hours
                </label>
                <input
                  type="number"
                  min="1"
                  max="40"
                  value={newAssignment.weeklyGoalHours}
                  onChange={e =>
                    setNewAssignment(prev => ({
                      ...prev,
                      weeklyGoalHours: parseInt(e.target.value),
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setShowAssignModal(false)
                  setSelectedLearner('')
                  setNewAssignment({
                    subjectType: '',
                    customSubjectName: '',
                    weeklyGoalHours: 5,
                  })
                }}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleAssignSubject}
                disabled={
                  !selectedLearner || !newAssignment.subjectType || loading
                }
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-md transition-colors"
              >
                {loading ? 'Assigning...' : 'Assign Subject'}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
