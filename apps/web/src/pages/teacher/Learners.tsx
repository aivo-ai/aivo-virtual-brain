import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import { teacherClient, Learner } from '../../api/teacherClient'
import { LearnerCard } from '../../components/cards/LearnerCard'

interface FilterOptions {
  status: 'all' | 'active' | 'inactive' | 'pending'
  gradeLevel: 'all' | string
  subject: 'all' | string
  search: string
}

export const Learners: React.FC = () => {
  const [learners, setLearners] = useState<Learner[]>([])
  const [filteredLearners, setFilteredLearners] = useState<Learner[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<FilterOptions>({
    status: 'all',
    gradeLevel: 'all',
    subject: 'all',
    search: '',
  })
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [inviteCode, setInviteCode] = useState('')

  useEffect(() => {
    loadLearners()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [learners, filters])

  const loadLearners = async () => {
    try {
      setLoading(true)
      const data = await teacherClient.getAssignedLearners()
      setLearners(data)
    } catch (err) {
      setError('Failed to load learners')
      console.error('Error loading learners:', err)
    } finally {
      setLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = learners

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(learner => learner.status === filters.status)
    }

    // Grade level filter
    if (filters.gradeLevel !== 'all') {
      filtered = filtered.filter(
        learner => learner.gradeLevel === filters.gradeLevel
      )
    }

    // Subject filter
    if (filters.subject !== 'all') {
      filtered = filtered.filter(learner =>
        learner.subjects?.some(
          assignment =>
            assignment.subjectType === filters.subject &&
            assignment.status === 'active'
        )
      )
    }

    // Search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase()
      filtered = filtered.filter(
        learner =>
          learner.firstName.toLowerCase().includes(searchLower) ||
          learner.lastName.toLowerCase().includes(searchLower) ||
          learner.id?.toLowerCase().includes(searchLower)
      )
    }

    setFilteredLearners(filtered)
  }

  const handleInviteAccept = async () => {
    if (!inviteCode.trim()) return

    try {
      setLoading(true)
      await teacherClient.acceptInvite(inviteCode.trim(), {})
      setInviteCode('')
      setShowInviteModal(false)
      await loadLearners() // Refresh the list
    } catch (err) {
      setError('Failed to accept invite')
      console.error('Error accepting invite:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleLearnerUpdate = (updatedLearner: Learner) => {
    setLearners(prev =>
      prev.map(learner =>
        learner.id === updatedLearner.id ? updatedLearner : learner
      )
    )
  }

  const getUniqueGradeLevels = () => {
    const grades = [...new Set(learners.map(l => l.gradeLevel))]
    return grades.sort((a, b) => {
      if (a === 'pre-k') return -1
      if (b === 'pre-k') return 1
      if (a === 'k') return b === 'pre-k' ? 1 : -1
      if (b === 'k') return 1
      return parseInt(a) - parseInt(b)
    })
  }

  const getUniqueSubjects = () => {
    const subjects = new Set<string>()
    learners.forEach(learner => {
      learner.subjects?.forEach(assignment => {
        if (assignment.status === 'active') {
          subjects.add(assignment.subjectType)
        }
      })
    })
    return Array.from(subjects).sort()
  }

  if (loading && learners.length === 0) {
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
                My Learners
              </h1>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Manage your assigned students and track their progress
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => setShowInviteModal(true)}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors flex items-center"
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
                Accept Invite
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Search
              </label>
              <input
                type="text"
                value={filters.search}
                onChange={e =>
                  setFilters(prev => ({ ...prev, search: e.target.value }))
                }
                placeholder="Search by name or ID..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              />
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
                    status: e.target.value as FilterOptions['status'],
                  }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Status</option>
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
                <option value="pending">Pending</option>
              </select>
            </div>

            {/* Grade Level Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Grade Level
              </label>
              <select
                value={filters.gradeLevel}
                onChange={e =>
                  setFilters(prev => ({ ...prev, gradeLevel: e.target.value }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Grades</option>
                {getUniqueGradeLevels().map(grade => (
                  <option key={grade} value={grade}>
                    {grade === 'k'
                      ? 'Kindergarten'
                      : grade === 'pre-k'
                        ? 'Pre-K'
                        : `Grade ${grade}`}
                  </option>
                ))}
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
                {getUniqueSubjects().map(subject => (
                  <option key={subject} value={subject}>
                    {subject}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Results Summary */}
        <div className="mb-6">
          <p className="text-gray-600 dark:text-gray-400">
            Showing {filteredLearners.length} of {learners.length} learners
          </p>
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

        {/* Learners Grid */}
        {filteredLearners.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredLearners.map(learner => (
              <FadeInWhenVisible key={learner.id}>
                <LearnerCard learner={learner} onUpdate={handleLearnerUpdate} />
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
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
              No learners found
            </h3>
            <p className="mt-2 text-gray-500 dark:text-gray-400">
              {learners.length === 0
                ? "You don't have any assigned learners yet. Accept an invite to get started."
                : 'No learners match your current filters. Try adjusting your search criteria.'}
            </p>
          </div>
        )}
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Accept Learner Invite
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Enter the invite code provided by the district administrator to
              add a new learner to your roster.
            </p>
            <input
              type="text"
              value={inviteCode}
              onChange={e => setInviteCode(e.target.value)}
              placeholder="Enter invite code..."
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white mb-4"
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowInviteModal(false)
                  setInviteCode('')
                }}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleInviteAccept}
                disabled={!inviteCode.trim() || loading}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-md transition-colors"
              >
                {loading ? 'Accepting...' : 'Accept Invite'}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
