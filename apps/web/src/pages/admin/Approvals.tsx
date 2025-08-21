import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  DocumentTextIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationCircleIcon,
  FunnelIcon,
  ArrowPathIcon,
  EyeIcon,
  ShieldCheckIcon
} from '@heroicons/react/24/outline'
import { useAuth } from '../../app/providers/AuthProvider'
import { adminClient, ApprovalQueueItem, ApprovalStats } from '../../api/adminClient'
import { FadeInWhenVisible } from '../../components/ui/Animations'

interface ApprovalFilter {
  status: 'all' | 'pending' | 'approved' | 'denied' | 'expired'
  type: 'all' | 'iep_change' | 'level_change' | 'parent_concern' | 'accommodation_request'
  priority: 'all' | 'low' | 'medium' | 'high' | 'urgent'
  role: 'all' | 'guardian' | 'teacher' | 'case_manager' | 'admin'
}

export const Approvals: React.FC = () => {
  const { user } = useAuth()
  const [approvals, setApprovals] = useState<ApprovalQueueItem[]>([])
  const [filteredApprovals, setFilteredApprovals] = useState<ApprovalQueueItem[]>([])
  const [stats, setStats] = useState<ApprovalStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedApproval, setSelectedApproval] = useState<ApprovalQueueItem | null>(null)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<ApprovalFilter>({
    status: 'pending',
    type: 'all',
    priority: 'all',
    role: 'all'
  })

  // Check if user has staff role for admin access
  const hasStaffAccess = user?.roles?.includes('staff') || user?.roles?.includes('system_admin')

  useEffect(() => {
    if (hasStaffAccess) {
      loadApprovalData()
    }
  }, [hasStaffAccess])

  useEffect(() => {
    applyFilters()
  }, [approvals, filters])

  const loadApprovalData = async () => {
    try {
      setLoading(true)
      const [approvalsData, statsData] = await Promise.all([
        adminClient.getApprovalQueue(),
        adminClient.getApprovalStats()
      ])
      
      setApprovals(approvalsData)
      setStats(statsData)
    } catch (err) {
      setError('Failed to load approval queue data')
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

    // Type filter
    if (filters.type !== 'all') {
      filtered = filtered.filter(approval => approval.type === filters.type)
    }

    // Priority filter
    if (filters.priority !== 'all') {
      filtered = filtered.filter(approval => approval.priority === filters.priority)
    }

    // Role filter - check if this role needs to approve
    if (filters.role !== 'all') {
      filtered = filtered.filter(approval => 
        approval.required_roles?.includes(filters.role) || 
        approval.pending_roles?.includes(filters.role)
      )
    }

    // Sort by priority and date
    filtered.sort((a, b) => {
      const priorityOrder = { urgent: 4, high: 3, medium: 2, low: 1 }
      const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority]
      if (priorityDiff !== 0) return priorityDiff

      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    })

    setFilteredApprovals(filtered)
  }

  const refreshData = () => {
    loadApprovalData()
  }

  // If user doesn't have staff access, show access denied
  if (!hasStaffAccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8 text-center">
          <ShieldCheckIcon className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600 mb-4">
            You need staff-level permissions to access the approval queue.
          </p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <ArrowPathIcon className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
          <p>Loading approval queue...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <XCircleIcon className="h-8 w-8 text-red-600 mx-auto mb-4" />
          <p className="text-red-600">{error}</p>
          <button 
            onClick={refreshData}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircleIcon className="h-5 w-5 text-green-600" />
      case 'denied':
        return <XCircleIcon className="h-5 w-5 text-red-600" />
      case 'expired':
        return <ClockIcon className="h-5 w-5 text-gray-600" />
      case 'pending':
      default:
        return <ExclamationCircleIcon className="h-5 w-5 text-yellow-600" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return 'text-green-800 bg-green-100 border-green-200'
      case 'denied': return 'text-red-800 bg-red-100 border-red-200'
      case 'expired': return 'text-gray-800 bg-gray-100 border-gray-200'
      case 'pending':
      default: return 'text-yellow-800 bg-yellow-100 border-yellow-200'
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-red-800 bg-red-100 border-red-200'
      case 'high': return 'text-orange-800 bg-orange-100 border-orange-200'
      case 'medium': return 'text-blue-800 bg-blue-100 border-blue-200'
      case 'low':
      default: return 'text-gray-800 bg-gray-100 border-gray-200'
    }
  }

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffHours / 24)

    if (diffDays > 0) {
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    } else if (diffHours > 0) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    } else {
      return 'Just now'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Approval Queue Monitor</h1>
              <p className="text-gray-600 mt-1">Read-only monitoring of approval requests and workflows</p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                <FunnelIcon className="h-4 w-4 mr-2" />
                Filters
              </button>
              <button
                onClick={refreshData}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700"
              >
                <ArrowPathIcon className="h-4 w-4 mr-2" />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Stats Overview */}
        {stats && (
          <FadeInWhenVisible>
            <div className="mb-8 grid grid-cols-1 md:grid-cols-5 gap-6">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <DocumentTextIcon className="h-8 w-8 text-blue-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Total Requests</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.total_requests}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <ClockIcon className="h-8 w-8 text-yellow-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Pending</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.pending_count}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <CheckCircleIcon className="h-8 w-8 text-green-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Approved</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.approved_count}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <XCircleIcon className="h-8 w-8 text-red-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Denied</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.denied_count}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <ExclamationCircleIcon className="h-8 w-8 text-orange-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Avg. Response</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.avg_response_time}h</p>
                  </div>
                </div>
              </div>
            </div>
          </FadeInWhenVisible>
        )}

        {/* Filters */}
        {showFilters && (
          <FadeInWhenVisible>
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Filter Options</h3>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                  <select
                    value={filters.status}
                    onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as any }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">All Statuses</option>
                    <option value="pending">Pending</option>
                    <option value="approved">Approved</option>
                    <option value="denied">Denied</option>
                    <option value="expired">Expired</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Type</label>
                  <select
                    value={filters.type}
                    onChange={(e) => setFilters(prev => ({ ...prev, type: e.target.value as any }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">All Types</option>
                    <option value="iep_change">IEP Change</option>
                    <option value="level_change">Level Change</option>
                    <option value="parent_concern">Parent Concern</option>
                    <option value="accommodation_request">Accommodation Request</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Priority</label>
                  <select
                    value={filters.priority}
                    onChange={(e) => setFilters(prev => ({ ...prev, priority: e.target.value as any }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">All Priorities</option>
                    <option value="urgent">Urgent</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Required Role</label>
                  <select
                    value={filters.role}
                    onChange={(e) => setFilters(prev => ({ ...prev, role: e.target.value as any }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">All Roles</option>
                    <option value="guardian">Guardian</option>
                    <option value="teacher">Teacher</option>
                    <option value="case_manager">Case Manager</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
              </div>
            </div>
          </FadeInWhenVisible>
        )}

        {/* Approval Queue List */}
        <FadeInWhenVisible>
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                Approval Requests ({filteredApprovals.length})
              </h2>
            </div>
            
            <div className="overflow-hidden">
              {filteredApprovals.length === 0 ? (
                <div className="text-center py-12">
                  <DocumentTextIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500">No approval requests match the current filters.</p>
                </div>
              ) : (
                <div className="space-y-0">
                  {filteredApprovals.map((approval, index) => (
                    <motion.div
                      key={approval.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="border-b border-gray-200 last:border-b-0 hover:bg-gray-50 transition-colors"
                    >
                      <div className="px-6 py-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center space-x-3 mb-2">
                              <h3 className="text-lg font-medium text-gray-900">
                                {approval.title}
                              </h3>
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(approval.status)}`}>
                                {getStatusIcon(approval.status)}
                                <span className="ml-1 capitalize">{approval.status}</span>
                              </span>
                              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getPriorityColor(approval.priority)}`}>
                                <span className="capitalize">{approval.priority}</span>
                              </span>
                            </div>
                            
                            <p className="text-gray-600 mb-3">{approval.description}</p>
                            
                            <div className="flex flex-wrap items-center space-x-6 text-sm text-gray-500">
                              <span>
                                <strong>Type:</strong> {approval.type.replace('_', ' ')}
                              </span>
                              <span>
                                <strong>Requested by:</strong> {approval.requested_by}
                              </span>
                              <span>
                                <strong>Created:</strong> {formatTimeAgo(approval.created_at)}
                              </span>
                              {approval.expires_at && (
                                <span>
                                  <strong>Expires:</strong> {new Date(approval.expires_at).toLocaleDateString()}
                                </span>
                              )}
                            </div>
                            
                            {approval.required_roles && approval.required_roles.length > 0 && (
                              <div className="mt-3">
                                <span className="text-sm text-gray-500 mr-2">Required approvals:</span>
                                {approval.required_roles.map((role) => (
                                  <span
                                    key={role}
                                    className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium mr-2 ${
                                      approval.approved_roles?.includes(role)
                                        ? 'bg-green-100 text-green-800'
                                        : 'bg-gray-100 text-gray-800'
                                    }`}
                                  >
                                    {approval.approved_roles?.includes(role) && (
                                      <CheckCircleIcon className="h-3 w-3 mr-1" />
                                    )}
                                    {role.replace('_', ' ')}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                          
                          <div className="flex-shrink-0 ml-6">
                            <button
                              onClick={() => setSelectedApproval(approval)}
                              className="flex items-center px-3 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200"
                            >
                              <EyeIcon className="h-4 w-4 mr-1" />
                              View Details
                            </button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </FadeInWhenVisible>

        {/* Approval Details Modal */}
        {selectedApproval && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-screen overflow-y-auto">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-900">Approval Request Details</h2>
                  <button
                    onClick={() => setSelectedApproval(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <XCircleIcon className="h-6 w-6" />
                  </button>
                </div>
              </div>
              
              <div className="px-6 py-4 space-y-4">
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">Request Information</h3>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                    <p><strong>ID:</strong> {selectedApproval.id}</p>
                    <p><strong>Title:</strong> {selectedApproval.title}</p>
                    <p><strong>Type:</strong> {selectedApproval.type.replace('_', ' ')}</p>
                    <p><strong>Status:</strong> <span className="capitalize">{selectedApproval.status}</span></p>
                    <p><strong>Priority:</strong> <span className="capitalize">{selectedApproval.priority}</span></p>
                    <p><strong>Requested by:</strong> {selectedApproval.requested_by}</p>
                    <p><strong>Created:</strong> {new Date(selectedApproval.created_at).toLocaleString()}</p>
                    {selectedApproval.expires_at && (
                      <p><strong>Expires:</strong> {new Date(selectedApproval.expires_at).toLocaleString()}</p>
                    )}
                  </div>
                </div>
                
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">Description</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p>{selectedApproval.description}</p>
                  </div>
                </div>
                
                {selectedApproval.context_data && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">Context Data</h3>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap">
                        {JSON.stringify(selectedApproval.context_data, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
                
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">Approval Status</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    {selectedApproval.required_roles?.map((role) => (
                      <div key={role} className="flex items-center justify-between py-2">
                        <span className="font-medium">{role.replace('_', ' ')}</span>
                        {selectedApproval.approved_roles?.includes(role) ? (
                          <span className="flex items-center text-green-600">
                            <CheckCircleIcon className="h-5 w-5 mr-1" />
                            Approved
                          </span>
                        ) : (
                          <span className="flex items-center text-yellow-600">
                            <ClockIcon className="h-5 w-5 mr-1" />
                            Pending
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              
              <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                <p className="text-sm text-gray-600">
                  <strong>Note:</strong> This is a read-only view for monitoring purposes. 
                  Approval decisions must be made by the appropriate stakeholders through their respective interfaces.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Notice */}
        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex">
            <ShieldCheckIcon className="h-5 w-5 text-blue-600 flex-shrink-0" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-blue-800">Read-Only Monitoring</h3>
              <p className="text-sm text-blue-700 mt-1">
                This interface provides read-only access to the approval queue for monitoring purposes. 
                All actions are logged and audited. Staff cannot make approval decisions from this interface.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Approvals
