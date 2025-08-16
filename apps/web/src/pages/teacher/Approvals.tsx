import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import { teacherClient, ApprovalRecord, Learner } from '../../api/teacherClient'

interface ApprovalFilter {
  status: 'all' | 'pending' | 'approved' | 'denied' | 'needs_info'
  priority: 'all' | 'low' | 'medium' | 'high' | 'urgent'
  type:
    | 'all'
    | 'activity_request'
    | 'grade_change'
    | 'subject_completion'
    | 'parent_concern'
    | 'accommodation_request'
  learner: 'all' | string
}

export const Approvals: React.FC = () => {
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([])
  const [filteredApprovals, setFilteredApprovals] = useState<ApprovalRecord[]>(
    []
  )
  const [learners, setLearners] = useState<Learner[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<ApprovalFilter>({
    status: 'pending',
    priority: 'all',
    type: 'all',
    learner: 'all',
  })
  const [selectedApproval, setSelectedApproval] =
    useState<ApprovalRecord | null>(null)
  const [reviewDecision, setReviewDecision] = useState({
    status: 'approved' as 'approved' | 'denied' | 'needs_info',
    comments: '',
  })

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    applyFilters()
  }, [approvals, filters])

  const loadData = async () => {
    try {
      setLoading(true)
      const [approvalsData, learnersData] = await Promise.all([
        teacherClient.getPendingApprovals(),
        teacherClient.getAssignedLearners(),
      ])
      setApprovals(approvalsData)
      setLearners(learnersData)
    } catch (err) {
      setError('Failed to load approvals')
      console.error('Error loading approvals:', err)
    } finally {
      setLoading(false)
    }
  }

  const applyFilters = () => {
    let filtered = approvals

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(approval => approval.status === filters.status)
    }

    // Priority filter
    if (filters.priority !== 'all') {
      filtered = filtered.filter(
        approval => approval.priority === filters.priority
      )
    }

    // Type filter
    if (filters.type !== 'all') {
      filtered = filtered.filter(approval => approval.type === filters.type)
    }

    // Learner filter
    if (filters.learner !== 'all') {
      filtered = filtered.filter(
        approval => approval.learnerId === filters.learner
      )
    }

    // Sort by priority and date
    filtered.sort((a, b) => {
      const priorityOrder = { urgent: 4, high: 3, medium: 2, low: 1 }
      const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority]
      if (priorityDiff !== 0) return priorityDiff

      return (
        new Date(b.requestedAt).getTime() - new Date(a.requestedAt).getTime()
      )
    })

    setFilteredApprovals(filtered)
  }

  const handleReviewApproval = async (approvalId: string) => {
    try {
      setLoading(true)
      await teacherClient.reviewApproval(approvalId, reviewDecision)
      setSelectedApproval(null)
      setReviewDecision({ status: 'approved', comments: '' })
      await loadData() // Refresh data
    } catch (err) {
      setError('Failed to review approval')
      console.error('Error reviewing approval:', err)
    } finally {
      setLoading(false)
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border-red-200 dark:border-red-700'
      case 'high':
        return 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 border-orange-200 dark:border-orange-700'
      case 'medium':
        return 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200 border-yellow-200 dark:border-yellow-700'
      case 'low':
        return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border-green-200 dark:border-green-700'
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border-gray-200 dark:border-gray-600'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'
      case 'approved':
        return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
      case 'denied':
        return 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'
      case 'needs_info':
        return 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200'
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'activity_request':
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
      case 'grade_change':
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
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
            />
          </svg>
        )
      case 'subject_completion':
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
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        )
      case 'parent_concern':
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
      case 'accommodation_request':
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
              d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4"
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
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        )
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  const getLearnerName = (learnerId: string) => {
    const learner = learners.find(l => l.id === learnerId)
    return learner
      ? `${learner.firstName} ${learner.lastName}`
      : 'Unknown Learner'
  }

  const getApprovalStats = () => {
    return {
      total: approvals.length,
      pending: approvals.filter(a => a.status === 'pending').length,
      approved: approvals.filter(a => a.status === 'approved').length,
      denied: approvals.filter(a => a.status === 'denied').length,
      urgent: approvals.filter(
        a => a.priority === 'urgent' && a.status === 'pending'
      ).length,
    }
  }

  const stats = getApprovalStats()

  if (loading && approvals.length === 0) {
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
                Approvals Queue
              </h1>
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                Review and manage pending approval requests
              </p>
            </div>
            <div className="flex items-center space-x-4">
              {stats.urgent > 0 && (
                <div className="flex items-center space-x-2 px-3 py-2 bg-red-100 dark:bg-red-900 rounded-lg">
                  <svg
                    className="w-4 h-4 text-red-600 dark:text-red-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z"
                    />
                  </svg>
                  <span className="text-sm font-medium text-red-800 dark:text-red-200">
                    {stats.urgent} Urgent
                  </span>
                </div>
              )}
            </div>
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
                      d="M9 5H7a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2V9a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                    />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Total Requests
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
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Pending
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {stats.pending}
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
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Approved
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {stats.approved}
                  </dd>
                </dl>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 bg-red-100 dark:bg-red-900 rounded-full flex items-center justify-center">
                  <svg
                    className="w-4 h-4 text-red-600 dark:text-red-400"
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
                </div>
              </div>
              <div className="ml-5 w-0 flex-1">
                <dl>
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                    Denied
                  </dt>
                  <dd className="text-lg font-medium text-gray-900 dark:text-white">
                    {stats.denied}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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
                    status: e.target.value as ApprovalFilter['status'],
                  }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="approved">Approved</option>
                <option value="denied">Denied</option>
                <option value="needs_info">Needs Info</option>
              </select>
            </div>

            {/* Priority Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Priority
              </label>
              <select
                value={filters.priority}
                onChange={e =>
                  setFilters(prev => ({
                    ...prev,
                    priority: e.target.value as ApprovalFilter['priority'],
                  }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Priorities</option>
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            {/* Type Filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Type
              </label>
              <select
                value={filters.type}
                onChange={e =>
                  setFilters(prev => ({
                    ...prev,
                    type: e.target.value as ApprovalFilter['type'],
                  }))
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              >
                <option value="all">All Types</option>
                <option value="activity_request">Activity Request</option>
                <option value="grade_change">Grade Change</option>
                <option value="subject_completion">Subject Completion</option>
                <option value="parent_concern">Parent Concern</option>
                <option value="accommodation_request">
                  Accommodation Request
                </option>
              </select>
            </div>

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

        {/* Approvals List */}
        {filteredApprovals.length > 0 ? (
          <div className="space-y-4">
            {filteredApprovals.map(approval => (
              <FadeInWhenVisible key={approval.id}>
                <div
                  className={`bg-white dark:bg-gray-800 rounded-lg shadow-sm border-l-4 ${getPriorityColor(approval.priority)} p-6`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0">
                        <div className="w-10 h-10 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center text-gray-600 dark:text-gray-400">
                          {getTypeIcon(approval.type)}
                        </div>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center space-x-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                            {approval.title}
                          </h3>
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(approval.status)}`}
                          >
                            {approval.status.replace('_', ' ')}
                          </span>
                          <span
                            className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(approval.priority)}`}
                          >
                            {approval.priority}
                          </span>
                        </div>
                        <p className="text-gray-600 dark:text-gray-400 mb-3">
                          {approval.description}
                        </p>
                        <div className="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                          <span>
                            Learner: {getLearnerName(approval.learnerId)}
                          </span>
                          <span>•</span>
                          <span>Requested by: {approval.requestedBy}</span>
                          <span>•</span>
                          <span>{formatDate(approval.requestedAt)}</span>
                          {approval.relatedSubject && (
                            <>
                              <span>•</span>
                              <span>Subject: {approval.relatedSubject}</span>
                            </>
                          )}
                        </div>
                        {approval.attachments &&
                          approval.attachments.length > 0 && (
                            <div className="mt-3 flex items-center space-x-2">
                              <svg
                                className="w-4 h-4 text-gray-400"
                                fill="none"
                                stroke="currentColor"
                                viewBox="0 0 24 24"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                                />
                              </svg>
                              <span className="text-sm text-gray-500 dark:text-gray-400">
                                {approval.attachments.length} attachment
                                {approval.attachments.length > 1 ? 's' : ''}
                              </span>
                            </div>
                          )}
                      </div>
                    </div>
                    {approval.status === 'pending' && (
                      <div className="flex space-x-2">
                        <button
                          onClick={() => setSelectedApproval(approval)}
                          className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
                        >
                          Review
                        </button>
                      </div>
                    )}
                  </div>
                </div>
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
                d="M9 5H7a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2V9a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
              No approvals found
            </h3>
            <p className="mt-2 text-gray-500 dark:text-gray-400">
              No approval requests match your current filters.
            </p>
          </div>
        )}
      </div>

      {/* Review Modal */}
      {selectedApproval && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-lg w-full mx-4 max-h-screen overflow-y-auto"
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Review Approval Request
            </h3>

            <div className="space-y-4 mb-6">
              <div>
                <h4 className="font-medium text-gray-900 dark:text-white">
                  {selectedApproval.title}
                </h4>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  {selectedApproval.description}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    Learner:
                  </span>
                  <p className="text-gray-600 dark:text-gray-400">
                    {getLearnerName(selectedApproval.learnerId)}
                  </p>
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    Priority:
                  </span>
                  <span
                    className={`ml-2 px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(selectedApproval.priority)}`}
                  >
                    {selectedApproval.priority}
                  </span>
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    Requested by:
                  </span>
                  <p className="text-gray-600 dark:text-gray-400">
                    {selectedApproval.requestedBy}
                  </p>
                </div>
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    Date:
                  </span>
                  <p className="text-gray-600 dark:text-gray-400">
                    {formatDate(selectedApproval.requestedAt)}
                  </p>
                </div>
              </div>

              {selectedApproval.relatedSubject && (
                <div>
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    Related Subject:
                  </span>
                  <p className="text-gray-600 dark:text-gray-400">
                    {selectedApproval.relatedSubject}
                  </p>
                </div>
              )}
            </div>

            <div className="space-y-4">
              {/* Decision */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Decision
                </label>
                <select
                  value={reviewDecision.status}
                  onChange={e =>
                    setReviewDecision(prev => ({
                      ...prev,
                      status: e.target.value as typeof prev.status,
                    }))
                  }
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                >
                  <option value="approved">Approve</option>
                  <option value="denied">Deny</option>
                  <option value="needs_info">Needs More Information</option>
                </select>
              </div>

              {/* Comments */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Comments{' '}
                  {reviewDecision.status === 'denied' && (
                    <span className="text-red-500">*</span>
                  )}
                </label>
                <textarea
                  value={reviewDecision.comments}
                  onChange={e =>
                    setReviewDecision(prev => ({
                      ...prev,
                      comments: e.target.value,
                    }))
                  }
                  placeholder="Add your comments..."
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setSelectedApproval(null)
                  setReviewDecision({ status: 'approved', comments: '' })
                }}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={() => handleReviewApproval(selectedApproval.id)}
                disabled={
                  loading ||
                  (reviewDecision.status === 'denied' &&
                    !reviewDecision.comments.trim())
                }
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-md transition-colors"
              >
                {loading ? 'Submitting...' : 'Submit Review'}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
