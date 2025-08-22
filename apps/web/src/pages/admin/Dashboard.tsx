import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  ChartBarIcon,
  ExclamationTriangleIcon,
  UserGroupIcon,
  ClockIcon,
  DocumentTextIcon,
  ShieldCheckIcon,
  ArrowPathIcon,
  EyeIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '../../app/providers/AuthProvider'
import {
  adminClient,
  AdminStats,
  SystemHealth,
  AuditSummary,
} from '../../api/adminClient'
import { FadeInWhenVisible } from '../../components/ui/Animations'

interface QuickAction {
  title: string
  description: string
  icon: React.ReactNode
  href: string
  color: string
  requiresConsent?: boolean
}

interface AlertItem {
  id: string
  type: 'error' | 'warning' | 'info'
  title: string
  description: string
  timestamp: string
  resolved: boolean
}

export const Dashboard: React.FC = () => {
  const { user } = useAuth()
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [auditSummary, setAuditSummary] = useState<AuditSummary | null>(null)
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Check if user has staff role for admin access
  const hasStaffAccess = user?.role === 'staff' || user?.role === 'system_admin'

  useEffect(() => {
    if (hasStaffAccess) {
      loadDashboardData()
    }
  }, [hasStaffAccess])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const [statsData, healthData, auditData, alertsData] = await Promise.all([
        adminClient.getSystemStats(),
        adminClient.getSystemHealth(),
        adminClient.getAuditSummary(),
        adminClient.getSystemAlerts(),
      ])

      setStats(statsData)
      setHealth(healthData)
      setAuditSummary(auditData)
      setAlerts(alertsData)
    } catch (err) {
      setError('Failed to load admin dashboard data')
      console.error('Error loading admin dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  const refreshData = () => {
    loadDashboardData()
  }

  // If user doesn't have staff access, show access denied
  if (!hasStaffAccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8 text-center">
          <ShieldCheckIcon className="h-16 w-16 text-red-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Access Denied
          </h1>
          <p className="text-gray-600 mb-4">
            You need staff-level permissions to access the admin backoffice.
          </p>
          <p className="text-sm text-gray-500">
            Contact your system administrator if you believe you should have
            access.
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
          <p>Loading admin dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <ExclamationTriangleIcon className="h-8 w-8 text-red-600 mx-auto mb-4" />
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

  const quickActions: QuickAction[] = [
    {
      title: 'Approval Queue',
      description: 'Monitor pending approvals and review requests',
      icon: <DocumentTextIcon className="h-6 w-6" />,
      href: '/admin/approvals',
      color: 'orange',
    },
    {
      title: 'Job Queues',
      description: 'View and manage system job queues',
      icon: <ClockIcon className="h-6 w-6" />,
      href: '/admin/queues',
      color: 'blue',
    },
    {
      title: 'Learner Inspector',
      description: 'Read-only learner state inspection (requires consent)',
      icon: <EyeIcon className="h-6 w-6" />,
      href: '/admin/learners',
      color: 'green',
      requiresConsent: true,
    },
    {
      title: 'System Health',
      description: 'Monitor service health and performance metrics',
      icon: <ChartBarIcon className="h-6 w-6" />,
      href: '/admin/health',
      color: 'purple',
    },
    {
      title: 'Audit Logs',
      description: 'View system audit trail and security events',
      icon: <ShieldCheckIcon className="h-6 w-6" />,
      href: '/admin/audit',
      color: 'gray',
    },
    {
      title: 'User Management',
      description: 'View user accounts and access patterns',
      icon: <UserGroupIcon className="h-6 w-6" />,
      href: '/admin/users',
      color: 'indigo',
    },
  ]

  const getColorClasses = (color: string) => {
    const colorMap = {
      orange:
        'bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100',
      blue: 'bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100',
      green: 'bg-green-50 text-green-700 border-green-200 hover:bg-green-100',
      purple:
        'bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100',
      gray: 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100',
      indigo:
        'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100',
    }
    return colorMap[color as keyof typeof colorMap] || colorMap.gray
  }

  const getAlertColor = (type: string) => {
    switch (type) {
      case 'error':
        return 'border-red-300 bg-red-50 text-red-800'
      case 'warning':
        return 'border-yellow-300 bg-yellow-50 text-yellow-800'
      default:
        return 'border-blue-300 bg-blue-50 text-blue-800'
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Admin Backoffice
              </h1>
              <p className="text-gray-600 mt-1">
                Internal support tools and system monitoring
              </p>
            </div>
            <button
              onClick={refreshData}
              className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              <ArrowPathIcon className="h-4 w-4 mr-2" />
              Refresh
            </button>
          </div>
        </div>

        {/* System Health Overview */}
        {health && (
          <FadeInWhenVisible>
            <div className="mb-8 grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div
                      className={`h-8 w-8 rounded-full flex items-center justify-center ${
                        health.overall_status === 'healthy'
                          ? 'bg-green-100'
                          : 'bg-red-100'
                      }`}
                    >
                      <div
                        className={`h-3 w-3 rounded-full ${
                          health.overall_status === 'healthy'
                            ? 'bg-green-600'
                            : 'bg-red-600'
                        }`}
                      />
                    </div>
                  </div>
                  <div className="ml-5">
                    <p className="text-sm font-medium text-gray-500">
                      System Status
                    </p>
                    <p className="text-lg font-semibold text-gray-900 capitalize">
                      {health.overall_status}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <UserGroupIcon className="h-8 w-8 text-blue-600" />
                  <div className="ml-5">
                    <p className="text-sm font-medium text-gray-500">
                      Active Users
                    </p>
                    <p className="text-lg font-semibold text-gray-900">
                      {stats?.active_users || 0}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <ClockIcon className="h-8 w-8 text-orange-600" />
                  <div className="ml-5">
                    <p className="text-sm font-medium text-gray-500">
                      Pending Jobs
                    </p>
                    <p className="text-lg font-semibold text-gray-900">
                      {stats?.pending_jobs || 0}
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <DocumentTextIcon className="h-8 w-8 text-purple-600" />
                  <div className="ml-5">
                    <p className="text-sm font-medium text-gray-500">
                      Pending Approvals
                    </p>
                    <p className="text-lg font-semibold text-gray-900">
                      {stats?.pending_approvals || 0}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </FadeInWhenVisible>
        )}

        {/* System Alerts */}
        {alerts.length > 0 && (
          <FadeInWhenVisible>
            <div className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                System Alerts
              </h2>
              <div className="space-y-3">
                {alerts.slice(0, 3).map(alert => (
                  <div
                    key={alert.id}
                    className={`border-l-4 p-4 rounded-r-md ${getAlertColor(alert.type)}`}
                  >
                    <div className="flex items-start">
                      <div className="flex-shrink-0">
                        <ExclamationTriangleIcon className="h-5 w-5" />
                      </div>
                      <div className="ml-3 flex-1">
                        <p className="font-medium">{alert.title}</p>
                        <p className="text-sm mt-1">{alert.description}</p>
                        <p className="text-xs mt-2 opacity-75">
                          {new Date(alert.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </FadeInWhenVisible>
        )}

        {/* Quick Actions Grid */}
        <FadeInWhenVisible>
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">
              Quick Actions
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {quickActions.map((action, index) => (
                <motion.div
                  key={action.title}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <a
                    href={action.href}
                    className={`block p-6 border-2 rounded-lg transition-all duration-200 transform hover:scale-105 ${getColorClasses(action.color)}`}
                  >
                    <div className="flex items-start">
                      <div className="flex-shrink-0">{action.icon}</div>
                      <div className="ml-4 flex-1">
                        <h3 className="font-semibold text-lg mb-2">
                          {action.title}
                          {action.requiresConsent && (
                            <span className="ml-2 text-xs bg-yellow-200 text-yellow-800 px-2 py-1 rounded">
                              Consent Required
                            </span>
                          )}
                        </h3>
                        <p className="text-sm opacity-80">
                          {action.description}
                        </p>
                      </div>
                    </div>
                  </a>
                </motion.div>
              ))}
            </div>
          </div>
        </FadeInWhenVisible>

        {/* Audit Summary */}
        {auditSummary && (
          <FadeInWhenVisible>
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Recent Activity Summary
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900">
                    {auditSummary.login_events_24h}
                  </p>
                  <p className="text-sm text-gray-600">Login Events (24h)</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900">
                    {auditSummary.data_access_events_24h}
                  </p>
                  <p className="text-sm text-gray-600">Data Access (24h)</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-gray-900">
                    {auditSummary.admin_actions_24h}
                  </p>
                  <p className="text-sm text-gray-600">Admin Actions (24h)</p>
                </div>
              </div>
            </div>
          </FadeInWhenVisible>
        )}

        {/* Disclaimer */}
        <div className="mt-8 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600 flex-shrink-0" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">
                Important Notice
              </h3>
              <p className="text-sm text-yellow-700 mt-1">
                This is an internal support tool. All actions are audited and
                logged. Access to learner data requires proper consent tokens
                and guardian approval. Use only for legitimate support purposes.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
