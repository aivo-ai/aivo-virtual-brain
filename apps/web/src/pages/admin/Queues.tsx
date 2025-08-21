import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { 
  QueueListIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon,
  PlayIcon,
  StopIcon,
  ForwardIcon,
  FunnelIcon,
  ShieldCheckIcon,
  CpuChipIcon,
  DocumentArrowUpIcon
} from '@heroicons/react/24/outline'
import { useAuth } from '../../app/providers/AuthProvider'
import { adminClient, JobQueue, QueueStats, JobItem } from '../../api/adminClient'
import { FadeInWhenVisible } from '../../components/ui/Animations'

interface QueueFilter {
  service: 'all' | 'orchestrator' | 'ingest' | 'trainer' | 'analytics'
  status: 'all' | 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  priority: 'all' | 'low' | 'medium' | 'high' | 'urgent'
}

export const Queues: React.FC = () => {
  const { user } = useAuth()
  const [queues, setQueues] = useState<JobQueue[]>([])
  const [stats, setStats] = useState<QueueStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedQueue, setSelectedQueue] = useState<string>('orchestrator')
  const [queueJobs, setQueueJobs] = useState<JobItem[]>([])
  const [jobsLoading, setJobsLoading] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<QueueFilter>({
    service: 'all',
    status: 'all',
    priority: 'all'
  })
  const [selectedJob, setSelectedJob] = useState<JobItem | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Check if user has staff role for admin access
  const hasStaffAccess = user?.roles?.includes('staff') || user?.roles?.includes('system_admin')

  useEffect(() => {
    if (hasStaffAccess) {
      loadQueueData()
    }
  }, [hasStaffAccess])

  useEffect(() => {
    if (selectedQueue) {
      loadQueueJobs(selectedQueue)
    }
  }, [selectedQueue, filters])

  const loadQueueData = async () => {
    try {
      setLoading(true)
      const [queuesData, statsData] = await Promise.all([
        adminClient.getJobQueues(),
        adminClient.getQueueStats()
      ])
      
      setQueues(queuesData)
      setStats(statsData)
    } catch (err) {
      setError('Failed to load queue data')
      console.error('Error loading queues:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadQueueJobs = async (queueName: string) => {
    try {
      setJobsLoading(true)
      const jobs = await adminClient.getQueueJobs(queueName, filters)
      setQueueJobs(jobs)
    } catch (err) {
      console.error('Error loading queue jobs:', err)
    } finally {
      setJobsLoading(false)
    }
  }

  const refreshData = () => {
    loadQueueData()
    if (selectedQueue) {
      loadQueueJobs(selectedQueue)
    }
  }

  const handleJobAction = async (jobId: string, action: 'requeue' | 'cancel' | 'retry') => {
    try {
      setActionLoading(jobId)
      
      switch (action) {
        case 'requeue':
          await adminClient.requeueJob(jobId)
          break
        case 'cancel':
          await adminClient.cancelJob(jobId)
          break
        case 'retry':
          await adminClient.retryJob(jobId)
          break
      }
      
      // Refresh the jobs list
      if (selectedQueue) {
        loadQueueJobs(selectedQueue)
      }
    } catch (err) {
      console.error(`Error performing ${action} on job:`, err)
    } finally {
      setActionLoading(null)
    }
  }

  // If user doesn't have staff access, show access denied
  if (!hasStaffAccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8 text-center">
          <ShieldCheckIcon className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h1>
          <p className="text-gray-600 mb-4">
            You need staff-level permissions to access the job queue management.
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
          <p>Loading job queues...</p>
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
      case 'completed':
        return <CheckCircleIcon className="h-5 w-5 text-green-600" />
      case 'failed':
        return <XCircleIcon className="h-5 w-5 text-red-600" />
      case 'running':
        return <PlayIcon className="h-5 w-5 text-blue-600" />
      case 'cancelled':
        return <StopIcon className="h-5 w-5 text-gray-600" />
      case 'pending':
      default:
        return <ClockIcon className="h-5 w-5 text-yellow-600" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-800 bg-green-100 border-green-200'
      case 'failed': return 'text-red-800 bg-red-100 border-red-200'
      case 'running': return 'text-blue-800 bg-blue-100 border-blue-200'
      case 'cancelled': return 'text-gray-800 bg-gray-100 border-gray-200'
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

  const getServiceIcon = (service: string) => {
    switch (service) {
      case 'orchestrator': return <CpuChipIcon className="h-5 w-5" />
      case 'ingest': return <DocumentArrowUpIcon className="h-5 w-5" />
      case 'trainer': return <CpuChipIcon className="h-5 w-5" />
      case 'analytics': return <ClockIcon className="h-5 w-5" />
      default: return <QueueListIcon className="h-5 w-5" />
    }
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    if (minutes < 60) return `${minutes}m`
    const hours = Math.floor(minutes / 60)
    return `${hours}h ${minutes % 60}m`
  }

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMinutes / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffDays > 0) {
      return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`
    } else if (diffHours > 0) {
      return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`
    } else if (diffMinutes > 0) {
      return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`
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
              <h1 className="text-3xl font-bold text-gray-900">Job Queue Management</h1>
              <p className="text-gray-600 mt-1">Monitor and manage system job queues</p>
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

        {/* Queue Stats Overview */}
        {stats && (
          <FadeInWhenVisible>
            <div className="mb-8 grid grid-cols-1 md:grid-cols-5 gap-6">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <QueueListIcon className="h-8 w-8 text-blue-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Total Jobs</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.total_jobs}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <ClockIcon className="h-8 w-8 text-yellow-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Pending</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.pending_jobs}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <PlayIcon className="h-8 w-8 text-blue-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Running</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.running_jobs}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <XCircleIcon className="h-8 w-8 text-red-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Failed</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.failed_jobs}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <CheckCircleIcon className="h-8 w-8 text-green-600" />
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500">Success Rate</p>
                    <p className="text-lg font-semibold text-gray-900">{stats.success_rate}%</p>
                  </div>
                </div>
              </div>
            </div>
          </FadeInWhenVisible>
        )}

        {/* Queue Selection */}
        <FadeInWhenVisible>
          <div className="mb-8 bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Service Queues</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {queues.map((queue) => (
                <button
                  key={queue.name}
                  onClick={() => setSelectedQueue(queue.name)}
                  className={`p-4 rounded-lg border-2 transition-all duration-200 text-left ${
                    selectedQueue === queue.name
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center mb-2">
                    {getServiceIcon(queue.service)}
                    <h3 className="ml-2 font-medium text-gray-900 capitalize">{queue.name}</h3>
                  </div>
                  <div className="space-y-1 text-sm text-gray-600">
                    <p>Pending: {queue.pending_count}</p>
                    <p>Running: {queue.running_count}</p>
                    <p>Failed: {queue.failed_count}</p>
                  </div>
                  <div className={`mt-2 inline-flex items-center px-2 py-1 rounded text-xs ${
                    queue.status === 'healthy' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {queue.status}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </FadeInWhenVisible>

        {/* Filters */}
        {showFilters && (
          <FadeInWhenVisible>
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Filter Jobs</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Service</label>
                  <select
                    value={filters.service}
                    onChange={(e) => setFilters(prev => ({ ...prev, service: e.target.value as any }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">All Services</option>
                    <option value="orchestrator">Orchestrator</option>
                    <option value="ingest">Content Ingest</option>
                    <option value="trainer">Model Trainer</option>
                    <option value="analytics">Analytics</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Status</label>
                  <select
                    value={filters.status}
                    onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value as any }))}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  >
                    <option value="all">All Statuses</option>
                    <option value="pending">Pending</option>
                    <option value="running">Running</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                    <option value="cancelled">Cancelled</option>
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
              </div>
            </div>
          </FadeInWhenVisible>
        )}

        {/* Job List */}
        {selectedQueue && (
          <FadeInWhenVisible>
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 capitalize">
                  {selectedQueue} Queue Jobs ({queueJobs.length})
                </h2>
              </div>
              
              <div className="overflow-hidden">
                {jobsLoading ? (
                  <div className="text-center py-12">
                    <ArrowPathIcon className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
                    <p>Loading jobs...</p>
                  </div>
                ) : queueJobs.length === 0 ? (
                  <div className="text-center py-12">
                    <QueueListIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-500">No jobs found in this queue.</p>
                  </div>
                ) : (
                  <div className="space-y-0">
                    {queueJobs.map((job, index) => (
                      <motion.div
                        key={job.id}
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
                                  {job.name || job.type}
                                </h3>
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(job.status)}`}>
                                  {getStatusIcon(job.status)}
                                  <span className="ml-1 capitalize">{job.status}</span>
                                </span>
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getPriorityColor(job.priority)}`}>
                                  <span className="capitalize">{job.priority}</span>
                                </span>
                              </div>
                              
                              <div className="flex flex-wrap items-center space-x-6 text-sm text-gray-500 mb-2">
                                <span>
                                  <strong>ID:</strong> {job.id.substring(0, 8)}...
                                </span>
                                <span>
                                  <strong>Created:</strong> {formatTimeAgo(job.created_at)}
                                </span>
                                {job.started_at && (
                                  <span>
                                    <strong>Started:</strong> {formatTimeAgo(job.started_at)}
                                  </span>
                                )}
                                {job.duration && (
                                  <span>
                                    <strong>Duration:</strong> {formatDuration(job.duration)}
                                  </span>
                                )}
                                {job.retry_count > 0 && (
                                  <span>
                                    <strong>Retries:</strong> {job.retry_count}
                                  </span>
                                )}
                              </div>
                              
                              {job.error_message && (
                                <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                                  <strong>Error:</strong> {job.error_message}
                                </div>
                              )}
                              
                              {job.progress !== undefined && job.progress > 0 && (
                                <div className="mt-2">
                                  <div className="flex items-center justify-between text-sm text-gray-600 mb-1">
                                    <span>Progress</span>
                                    <span>{job.progress}%</span>
                                  </div>
                                  <div className="w-full bg-gray-200 rounded-full h-2">
                                    <div
                                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                                      style={{ width: `${job.progress}%` }}
                                    />
                                  </div>
                                </div>
                              )}
                            </div>
                            
                            <div className="flex-shrink-0 ml-6 space-x-2">
                              {job.status === 'failed' && (
                                <button
                                  onClick={() => handleJobAction(job.id, 'retry')}
                                  disabled={actionLoading === job.id}
                                  className="flex items-center px-3 py-2 bg-blue-100 text-blue-700 rounded-md text-sm hover:bg-blue-200 disabled:opacity-50"
                                >
                                  {actionLoading === job.id ? (
                                    <ArrowPathIcon className="h-4 w-4 animate-spin mr-1" />
                                  ) : (
                                    <ForwardIcon className="h-4 w-4 mr-1" />
                                  )}
                                  Retry
                                </button>
                              )}
                              
                              {(job.status === 'pending' || job.status === 'failed') && (
                                <button
                                  onClick={() => handleJobAction(job.id, 'requeue')}
                                  disabled={actionLoading === job.id}
                                  className="flex items-center px-3 py-2 bg-green-100 text-green-700 rounded-md text-sm hover:bg-green-200 disabled:opacity-50"
                                >
                                  {actionLoading === job.id ? (
                                    <ArrowPathIcon className="h-4 w-4 animate-spin mr-1" />
                                  ) : (
                                    <PlayIcon className="h-4 w-4 mr-1" />
                                  )}
                                  Requeue
                                </button>
                              )}
                              
                              {(job.status === 'running' || job.status === 'pending') && (
                                <button
                                  onClick={() => handleJobAction(job.id, 'cancel')}
                                  disabled={actionLoading === job.id}
                                  className="flex items-center px-3 py-2 bg-red-100 text-red-700 rounded-md text-sm hover:bg-red-200 disabled:opacity-50"
                                >
                                  {actionLoading === job.id ? (
                                    <ArrowPathIcon className="h-4 w-4 animate-spin mr-1" />
                                  ) : (
                                    <StopIcon className="h-4 w-4 mr-1" />
                                  )}
                                  Cancel
                                </button>
                              )}
                              
                              <button
                                onClick={() => setSelectedJob(job)}
                                className="flex items-center px-3 py-2 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200"
                              >
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
        )}

        {/* Job Details Modal */}
        {selectedJob && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-screen overflow-y-auto">
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-semibold text-gray-900">Job Details</h2>
                  <button
                    onClick={() => setSelectedJob(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <XCircleIcon className="h-6 w-6" />
                  </button>
                </div>
              </div>
              
              <div className="px-6 py-4 space-y-4">
                <div>
                  <h3 className="font-medium text-gray-900 mb-2">Job Information</h3>
                  <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                    <p><strong>ID:</strong> {selectedJob.id}</p>
                    <p><strong>Name:</strong> {selectedJob.name || selectedJob.type}</p>
                    <p><strong>Type:</strong> {selectedJob.type}</p>
                    <p><strong>Status:</strong> <span className="capitalize">{selectedJob.status}</span></p>
                    <p><strong>Priority:</strong> <span className="capitalize">{selectedJob.priority}</span></p>
                    <p><strong>Queue:</strong> {selectedJob.queue}</p>
                    <p><strong>Created:</strong> {new Date(selectedJob.created_at).toLocaleString()}</p>
                    {selectedJob.started_at && (
                      <p><strong>Started:</strong> {new Date(selectedJob.started_at).toLocaleString()}</p>
                    )}
                    {selectedJob.completed_at && (
                      <p><strong>Completed:</strong> {new Date(selectedJob.completed_at).toLocaleString()}</p>
                    )}
                    {selectedJob.duration && (
                      <p><strong>Duration:</strong> {formatDuration(selectedJob.duration)}</p>
                    )}
                    <p><strong>Retry Count:</strong> {selectedJob.retry_count}</p>
                  </div>
                </div>
                
                {selectedJob.payload && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">Job Payload</h3>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap overflow-x-auto">
                        {JSON.stringify(selectedJob.payload, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
                
                {selectedJob.result && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">Job Result</h3>
                    <div className="bg-gray-50 rounded-lg p-4">
                      <pre className="text-sm text-gray-700 whitespace-pre-wrap overflow-x-auto">
                        {JSON.stringify(selectedJob.result, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
                
                {selectedJob.error_message && (
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">Error Details</h3>
                    <div className="bg-red-50 rounded-lg p-4">
                      <p className="text-red-700">{selectedJob.error_message}</p>
                      {selectedJob.error_stack && (
                        <pre className="text-sm text-red-600 mt-2 whitespace-pre-wrap overflow-x-auto">
                          {selectedJob.error_stack}
                        </pre>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Notice */}
        <div className="mt-8 p-4 bg-orange-50 border border-orange-200 rounded-lg">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-orange-600 flex-shrink-0" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-orange-800">Queue Management Notice</h3>
              <p className="text-sm text-orange-700 mt-1">
                Job queue actions (requeue, cancel, retry) are incident tools for support purposes. 
                All actions are logged and audited. Use only when necessary for system operations.
                Do not directly modify data - only manage job execution state.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Queues
