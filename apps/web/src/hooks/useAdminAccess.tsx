/**
 * Admin RBAC Hook - Role-Based Access Control for Admin Backoffice
 * S4-17 Implementation - Strict staff-only access with audit logging
 */

import React from 'react'
import { useAuth } from '../app/providers/AuthProvider'
import { useEffect, useState } from 'react'
import { adminClient } from '../api/adminClient'

export interface AdminPermissions {
  canViewDashboard: boolean
  canViewApprovals: boolean
  canViewQueues: boolean
  canManageJobs: boolean
  canViewLearners: boolean
  canViewAudit: boolean
  canToggleFlags: boolean
  canExportData: boolean
}

export interface AdminSession {
  sessionId: string
  staffMember: string
  startTime: string
  permissions: AdminPermissions
  auditContext: {
    ipAddress?: string
    userAgent?: string
    location?: string
  }
}

/**
 * Hook for managing admin access and permissions
 */
export function useAdminAccess() {
  const { user } = useAuth()
  const [session, setSession] = useState<AdminSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Check if user has staff-level access
  const hasStaffAccess =
    user?.roles?.includes('staff') ||
    user?.roles?.includes('system_admin') ||
    user?.roles?.includes('tenant_admin')

  // Check specific permissions based on role
  const getPermissions = (userRoles: string[]): AdminPermissions => {
    const isSystemAdmin = userRoles.includes('system_admin')
    const isTenantAdmin = userRoles.includes('tenant_admin')
    const isStaff = userRoles.includes('staff')

    return {
      canViewDashboard: isSystemAdmin || isTenantAdmin || isStaff,
      canViewApprovals: isSystemAdmin || isTenantAdmin || isStaff,
      canViewQueues: isSystemAdmin || isTenantAdmin || isStaff,
      canManageJobs: isSystemAdmin || isTenantAdmin, // Only admins can manage jobs
      canViewLearners: isSystemAdmin || isTenantAdmin || isStaff,
      canViewAudit: isSystemAdmin || isTenantAdmin,
      canToggleFlags: isSystemAdmin, // Only system admins can toggle flags
      canExportData: isSystemAdmin || isTenantAdmin,
    }
  }

  useEffect(() => {
    const initializeAdminSession = async () => {
      if (!hasStaffAccess || !user) {
        setLoading(false)
        return
      }

      try {
        setLoading(true)

        // Create admin session with audit logging
        const permissions = getPermissions(user.roles)

        const adminSession: AdminSession = {
          sessionId: generateSessionId(),
          staffMember: user.email || user.id,
          startTime: new Date().toISOString(),
          permissions,
          auditContext: {
            ipAddress: await getClientIP(),
            userAgent: navigator.userAgent,
            location: await getApproximateLocation(),
          },
        }

        // Log admin session start
        await logAdminAction('admin_session_start', {
          session_id: adminSession.sessionId,
          staff_member: adminSession.staffMember,
          permissions,
          audit_context: adminSession.auditContext,
        })

        setSession(adminSession)

        // Set auth token for admin client
        if (user.token) {
          adminClient.setAuthToken(user.token)
        }
      } catch (err) {
        console.error('Failed to initialize admin session:', err)
        setError('Failed to initialize admin session')
      } finally {
        setLoading(false)
      }
    }

    initializeAdminSession()

    // Cleanup session on unmount
    return () => {
      if (session) {
        logAdminAction('admin_session_end', {
          session_id: session.sessionId,
          duration: Date.now() - new Date(session.startTime).getTime(),
        }).catch(console.error)
      }
    }
  }, [hasStaffAccess, user])

  // Log admin actions for audit trail
  const logAdminAction = async (action: string, details: any) => {
    try {
      const auditEntry = {
        timestamp: new Date().toISOString(),
        action,
        actor: session?.staffMember || user?.email || 'unknown',
        session_id: session?.sessionId,
        details,
        audit_context: session?.auditContext,
      }

      // In development, just log to console
      if (import.meta.env.DEV) {
        console.log('Admin Action Audit:', auditEntry)
        return
      }

      // In production, send to audit service
      await fetch('/api/audit/admin-actions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${user?.token}`,
        },
        body: JSON.stringify(auditEntry),
      })
    } catch (err) {
      console.error('Failed to log admin action:', err)
    }
  }

  // Helper to check specific permission
  const hasPermission = (permission: keyof AdminPermissions): boolean => {
    return session?.permissions[permission] || false
  }

  // Helper to log data access for learner inspection
  const logDataAccess = async (
    learnerId: string,
    purpose: string,
    consentToken?: string
  ) => {
    await logAdminAction('learner_data_access', {
      learner_id: learnerId,
      purpose,
      consent_token: consentToken ? 'present' : 'missing',
      timestamp: new Date().toISOString(),
    })
  }

  // Helper to log job management actions
  const logJobAction = async (
    jobId: string,
    action: 'requeue' | 'cancel' | 'retry',
    reason?: string
  ) => {
    await logAdminAction('job_management', {
      job_id: jobId,
      action,
      reason,
      timestamp: new Date().toISOString(),
    })
  }

  return {
    hasStaffAccess,
    session,
    loading,
    error,
    hasPermission,
    logAdminAction,
    logDataAccess,
    logJobAction,
  }
}

/**
 * Higher-order component for protecting admin routes
 */
export function withAdminAccess<P extends object>(
  Component: React.ComponentType<P>,
  requiredPermission?: keyof AdminPermissions
): React.FC<P> {
  return function AdminProtectedComponent(props: P): JSX.Element {
    const { hasStaffAccess, session, loading, hasPermission } = useAdminAccess()

    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p>Verifying admin access...</p>
          </div>
        </div>
      )
    }

    if (!hasStaffAccess) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8 text-center">
            <div className="h-16 w-16 text-red-500 mx-auto mb-4">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Access Denied
            </h1>
            <p className="text-gray-600 mb-4">
              You need staff-level permissions to access this admin tool.
            </p>
            <p className="text-sm text-gray-500">
              Contact your system administrator if you believe you should have
              access.
            </p>
          </div>
        </div>
      )
    }

    if (requiredPermission && !hasPermission(requiredPermission)) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-8 text-center">
            <div className="h-16 w-16 text-orange-500 mx-auto mb-4">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 15v2m-6 0h12a2 2 0 002-2v-9a2 2 0 00-2-2H6a2 2 0 00-2 2v9a2 2 0 002 2z"
                />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Insufficient Permissions
            </h1>
            <p className="text-gray-600 mb-4">
              You don't have the required permissions to access this feature.
            </p>
            <p className="text-sm text-gray-500">
              Required permission: {requiredPermission}
            </p>
          </div>
        </div>
      )
    }

    return <Component {...props} />
  }
}

// Utility functions
function generateSessionId(): string {
  return crypto.randomUUID()
}

async function getClientIP(): Promise<string> {
  try {
    // In development, return localhost
    if (import.meta.env.DEV) {
      return '127.0.0.1'
    }

    // In production, use IP detection service
    const response = await fetch('https://api.ipify.org?format=json')
    const data = await response.json()
    return data.ip || 'unknown'
  } catch {
    return 'unknown'
  }
}

async function getApproximateLocation(): Promise<string> {
  try {
    // In development, return test location
    if (import.meta.env.DEV) {
      return 'Development Environment'
    }

    // In production, use geolocation API (with user consent)
    if (navigator.geolocation) {
      return new Promise(resolve => {
        navigator.geolocation.getCurrentPosition(
          position => {
            resolve(
              `${position.coords.latitude.toFixed(2)}, ${position.coords.longitude.toFixed(2)}`
            )
          },
          () => {
            resolve('Location not available')
          },
          { timeout: 5000 }
        )
      })
    }

    return 'Location not available'
  } catch {
    return 'Location not available'
  }
}

export default useAdminAccess
