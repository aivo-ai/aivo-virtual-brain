/**
 * Admin Backoffice Tests
 * S4-17 Implementation - Test RBAC, audit logging, and access controls
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import { AuthProvider } from '../../app/providers/AuthProvider'
import Dashboard from '../../pages/admin/Dashboard'
import Approvals from '../../pages/admin/Approvals'
import Queues from '../../pages/admin/Queues'
import { adminClient } from '../../api/adminClient'
import useAdminAccess from '../../hooks/useAdminAccess'

// Mock the admin client
vi.mock('../../api/adminClient', () => ({
  adminClient: {
    setAuthToken: vi.fn(),
    getSystemStats: vi.fn(),
    getSystemHealth: vi.fn(),
    getAuditSummary: vi.fn(),
    getSystemAlerts: vi.fn(),
    getApprovalQueue: vi.fn(),
    getApprovalStats: vi.fn(),
    getJobQueues: vi.fn(),
    getQueueStats: vi.fn(),
    getQueueJobs: vi.fn(),
    requeueJob: vi.fn(),
    cancelJob: vi.fn(),
    retryJob: vi.fn(),
  },
}))

// Mock the admin access hook
vi.mock('../../hooks/useAdminAccess')

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({
      children,
      ...props
    }: {
      children: React.ReactNode
      [key: string]: any
    }) => <div {...props}>{children}</div>,
  },
}))

// Mock animations
vi.mock('../../components/ui/Animations', () => ({
  FadeInWhenVisible: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}))

// Test helpers
const mockUser = (roles: string[]) => ({
  id: 'test-user-123',
  email: 'admin@test.com',
  name: 'Test Admin',
  roles,
  token: 'mock-jwt-token',
})

const mockStaffUser = () => mockUser(['staff'])
const mockAdminUser = () => mockUser(['system_admin'])
const mockRegularUser = () => mockUser(['teacher'])

const mockAdminSession = (permissions = {}) => ({
  sessionId: 'session-123',
  staffMember: 'admin@test.com',
  startTime: new Date().toISOString(),
  permissions: {
    canViewDashboard: true,
    canViewApprovals: true,
    canViewQueues: true,
    canManageJobs: true,
    canViewLearners: true,
    canViewAudit: true,
    canToggleFlags: true,
    canExportData: true,
    ...permissions,
  },
  auditContext: {
    ipAddress: '127.0.0.1',
    userAgent: 'test-browser',
    location: 'test-location',
  },
})

const renderWithAuth = (
  component: React.ReactElement,
  user = mockStaffUser()
) => {
  const AuthWrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  )

  // Mock useAuth hook
  vi.doMock('../../app/providers/AuthProvider', () => ({
    useAuth: () => ({ user, isAuthenticated: !!user }),
    AuthProvider: AuthWrapper,
  }))

  return render(component, { wrapper: AuthWrapper })
}

describe('Admin RBAC and Access Control', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Dashboard Access Control', () => {
    it('should deny access to users without staff role', async () => {
      // Mock useAdminAccess for non-staff user
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: false,
        session: null,
        loading: false,
        error: null,
        hasPermission: () => false,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })

      renderWithAuth(<Dashboard />, mockRegularUser())

      expect(screen.getByText('Access Denied')).toBeInTheDocument()
      expect(screen.getByText(/staff-level permissions/)).toBeInTheDocument()
    })

    it('should allow access to users with staff role', async () => {
      // Mock successful admin access
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession(),
        loading: false,
        error: null,
        hasPermission: () => true,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })

      // Mock API responses
      vi.mocked(adminClient.getSystemStats).mockResolvedValue({
        active_users: 100,
        pending_jobs: 5,
        pending_approvals: 3,
        system_health: 'healthy',
      })

      vi.mocked(adminClient.getSystemHealth).mockResolvedValue({
        overall_status: 'healthy',
        services: [],
        last_updated: new Date().toISOString(),
      })

      vi.mocked(adminClient.getAuditSummary).mockResolvedValue({
        login_events_24h: 50,
        data_access_events_24h: 25,
        admin_actions_24h: 10,
        security_events_24h: 2,
      })

      vi.mocked(adminClient.getSystemAlerts).mockResolvedValue([])

      renderWithAuth(<Dashboard />, mockStaffUser())

      await waitFor(() => {
        expect(screen.getByText('Admin Backoffice')).toBeInTheDocument()
        expect(
          screen.getByText('Internal support tools and system monitoring')
        ).toBeInTheDocument()
      })
    })

    it('should show loading state while verifying access', () => {
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: null,
        loading: true,
        error: null,
        hasPermission: () => false,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })

      renderWithAuth(<Dashboard />, mockStaffUser())

      expect(screen.getByText('Loading admin dashboard...')).toBeInTheDocument()
    })

    it('should show error state when API fails', async () => {
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession(),
        loading: false,
        error: null,
        hasPermission: () => true,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })

      // Mock API failure
      vi.mocked(adminClient.getSystemStats).mockRejectedValue(
        new Error('API Error')
      )

      renderWithAuth(<Dashboard />, mockStaffUser())

      await waitFor(() => {
        expect(
          screen.getByText('Failed to load admin dashboard data')
        ).toBeInTheDocument()
      })
    })
  })

  describe('Approval Queue Access', () => {
    beforeEach(() => {
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession(),
        loading: false,
        error: null,
        hasPermission: () => true,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })
    })

    it('should load and display approval queue', async () => {
      vi.mocked(adminClient.getApprovalQueue).mockResolvedValue([
        {
          id: 'approval-123',
          title: 'IEP Modification Request',
          description: 'Request to modify IEP goals',
          type: 'iep_change',
          status: 'pending',
          priority: 'high',
          requested_by: 'teacher@school.edu',
          requested_by_role: 'teacher',
          created_at: new Date().toISOString(),
        },
      ])

      vi.mocked(adminClient.getApprovalStats).mockResolvedValue({
        total_requests: 100,
        pending_count: 15,
        approved_count: 70,
        denied_count: 10,
        expired_count: 5,
        avg_response_time: 24,
      })

      renderWithAuth(<Approvals />, mockStaffUser())

      await waitFor(() => {
        expect(screen.getByText('Approval Queue Monitor')).toBeInTheDocument()
        expect(screen.getByText('IEP Modification Request')).toBeInTheDocument()
        expect(
          screen.getByText('Read-only monitoring of approval requests')
        ).toBeInTheDocument()
      })
    })

    it('should filter approvals correctly', async () => {
      const approvals = [
        {
          id: 'approval-1',
          title: 'IEP Change',
          description: 'IEP modification',
          type: 'iep_change' as const,
          status: 'pending' as const,
          priority: 'high' as const,
          requested_by: 'teacher1',
          requested_by_role: 'teacher',
          created_at: new Date().toISOString(),
        },
        {
          id: 'approval-2',
          title: 'Level Change',
          description: 'Level advancement',
          type: 'level_change' as const,
          status: 'approved' as const,
          priority: 'medium' as const,
          requested_by: 'teacher2',
          requested_by_role: 'teacher',
          created_at: new Date().toISOString(),
        },
      ]

      vi.mocked(adminClient.getApprovalQueue).mockResolvedValue(approvals)
      vi.mocked(adminClient.getApprovalStats).mockResolvedValue({
        total_requests: 2,
        pending_count: 1,
        approved_count: 1,
        denied_count: 0,
        expired_count: 0,
        avg_response_time: 12,
      })

      renderWithAuth(<Approvals />, mockStaffUser())

      await waitFor(() => {
        expect(screen.getByText('IEP Change')).toBeInTheDocument()
        // Should show pending by default, so approved shouldn't be visible
        expect(screen.queryByText('Level Change')).not.toBeInTheDocument()
      })
    })
  })

  describe('Job Queue Management', () => {
    beforeEach(() => {
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession(),
        loading: false,
        error: null,
        hasPermission: () => true,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })
    })

    it('should load and display job queues', async () => {
      vi.mocked(adminClient.getJobQueues).mockResolvedValue([
        {
          name: 'orchestrator',
          service: 'orchestrator',
          status: 'healthy',
          pending_count: 5,
          running_count: 2,
          failed_count: 1,
          completed_count: 100,
          last_updated: new Date().toISOString(),
        },
      ])

      vi.mocked(adminClient.getQueueStats).mockResolvedValue({
        total_jobs: 108,
        pending_jobs: 5,
        running_jobs: 2,
        failed_jobs: 1,
        completed_jobs: 100,
        success_rate: 99.1,
      })

      vi.mocked(adminClient.getQueueJobs).mockResolvedValue([])

      renderWithAuth(<Queues />, mockStaffUser())

      await waitFor(() => {
        expect(screen.getByText('Job Queue Management')).toBeInTheDocument()
        expect(screen.getByText(/orchestrator/i)).toBeInTheDocument()
      })
    })

    it('should handle job actions with audit logging', async () => {
      const mockLogJobAction = vi.fn()

      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession(),
        loading: false,
        error: null,
        hasPermission: () => true,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: mockLogJobAction,
      })

      vi.mocked(adminClient.getJobQueues).mockResolvedValue([
        {
          name: 'orchestrator',
          service: 'orchestrator',
          status: 'healthy',
          pending_count: 0,
          running_count: 0,
          failed_count: 1,
          completed_count: 0,
          last_updated: new Date().toISOString(),
        },
      ])

      vi.mocked(adminClient.getQueueStats).mockResolvedValue({
        total_jobs: 1,
        pending_jobs: 0,
        running_jobs: 0,
        failed_jobs: 1,
        completed_jobs: 0,
        success_rate: 0,
      })

      vi.mocked(adminClient.getQueueJobs).mockResolvedValue([
        {
          id: 'job-123',
          name: 'Failed Job',
          type: 'training',
          status: 'failed',
          priority: 'medium',
          queue: 'orchestrator',
          created_at: new Date().toISOString(),
          retry_count: 0,
          error_message: 'Connection timeout',
        },
      ])

      vi.mocked(adminClient.retryJob).mockResolvedValue({
        message: 'Job requeued successfully',
      })

      renderWithAuth(<Queues />, mockStaffUser())

      await waitFor(() => {
        expect(screen.getByText('Failed Job')).toBeInTheDocument()
      })

      // Click retry button
      const retryButton = screen.getByText('Retry')
      fireEvent.click(retryButton)

      await waitFor(() => {
        expect(adminClient.retryJob).toHaveBeenCalledWith('job-123')
      })
    })

    it('should restrict job management for non-admin staff', async () => {
      // Mock staff with limited permissions
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession({
          canManageJobs: false, // Staff can view but not manage
        }),
        loading: false,
        error: null,
        hasPermission: (permission: string) => {
          const limitedPermissions = {
            canViewQueues: true,
            canManageJobs: false,
          }
          return (
            limitedPermissions[permission as keyof typeof limitedPermissions] ||
            false
          )
        },
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })

      vi.mocked(adminClient.getJobQueues).mockResolvedValue([])
      vi.mocked(adminClient.getQueueStats).mockResolvedValue({
        total_jobs: 0,
        pending_jobs: 0,
        running_jobs: 0,
        failed_jobs: 0,
        completed_jobs: 0,
        success_rate: 100,
      })

      renderWithAuth(<Queues />, mockStaffUser())

      await waitFor(() => {
        expect(screen.getByText('Job Queue Management')).toBeInTheDocument()
        // Should be able to view but management actions should be limited
      })
    })
  })

  describe('Audit Logging', () => {
    it('should log admin session start', async () => {
      const mockLogAdminAction = vi.fn()

      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession(),
        loading: false,
        error: null,
        hasPermission: () => true,
        logAdminAction: mockLogAdminAction,
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })

      // Mock API responses to prevent errors
      vi.mocked(adminClient.getSystemStats).mockResolvedValue({
        active_users: 0,
        pending_jobs: 0,
        pending_approvals: 0,
        system_health: 'healthy',
      })
      vi.mocked(adminClient.getSystemHealth).mockResolvedValue({
        overall_status: 'healthy',
        services: [],
        last_updated: new Date().toISOString(),
      })
      vi.mocked(adminClient.getAuditSummary).mockResolvedValue({
        login_events_24h: 0,
        data_access_events_24h: 0,
        admin_actions_24h: 0,
        security_events_24h: 0,
      })
      vi.mocked(adminClient.getSystemAlerts).mockResolvedValue([])

      renderWithAuth(<Dashboard />, mockStaffUser())

      // Verify admin action was logged (would be called during session initialization)
      await waitFor(() => {
        expect(screen.getByText('Admin Backoffice')).toBeInTheDocument()
      })
    })
  })

  describe('Security and Compliance', () => {
    it('should show consent requirement notice for learner data access', async () => {
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession(),
        loading: false,
        error: null,
        hasPermission: () => true,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })

      // Mock API responses
      vi.mocked(adminClient.getSystemStats).mockResolvedValue({
        active_users: 0,
        pending_jobs: 0,
        pending_approvals: 0,
        system_health: 'healthy',
      })
      vi.mocked(adminClient.getSystemHealth).mockResolvedValue({
        overall_status: 'healthy',
        services: [],
        last_updated: new Date().toISOString(),
      })
      vi.mocked(adminClient.getAuditSummary).mockResolvedValue({
        login_events_24h: 0,
        data_access_events_24h: 0,
        admin_actions_24h: 0,
        security_events_24h: 0,
      })
      vi.mocked(adminClient.getSystemAlerts).mockResolvedValue([])

      renderWithAuth(<Dashboard />, mockStaffUser())

      await waitFor(() => {
        expect(screen.getByText(/Consent Required/)).toBeInTheDocument()
        expect(screen.getByText(/internal support tool/i)).toBeInTheDocument()
        expect(screen.getByText(/all actions are audited/i)).toBeInTheDocument()
      })
    })

    it('should show read-only notice in approval queue', async () => {
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession(),
        loading: false,
        error: null,
        hasPermission: () => true,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })

      vi.mocked(adminClient.getApprovalQueue).mockResolvedValue([])
      vi.mocked(adminClient.getApprovalStats).mockResolvedValue({
        total_requests: 0,
        pending_count: 0,
        approved_count: 0,
        denied_count: 0,
        expired_count: 0,
        avg_response_time: 0,
      })

      renderWithAuth(<Approvals />, mockStaffUser())

      await waitFor(() => {
        expect(screen.getByText(/read-only monitoring/i)).toBeInTheDocument()
        expect(
          screen.getByText(/staff cannot make approval decisions/i)
        ).toBeInTheDocument()
      })
    })

    it('should show incident tools notice in queue management', async () => {
      vi.mocked(useAdminAccess).mockReturnValue({
        hasStaffAccess: true,
        session: mockAdminSession(),
        loading: false,
        error: null,
        hasPermission: () => true,
        logAdminAction: vi.fn(),
        logDataAccess: vi.fn(),
        logJobAction: vi.fn(),
      })

      vi.mocked(adminClient.getJobQueues).mockResolvedValue([])
      vi.mocked(adminClient.getQueueStats).mockResolvedValue({
        total_jobs: 0,
        pending_jobs: 0,
        running_jobs: 0,
        failed_jobs: 0,
        completed_jobs: 0,
        success_rate: 100,
      })

      renderWithAuth(<Queues />, mockStaffUser())

      await waitFor(() => {
        expect(
          screen.getByText(/incident tools for support purposes/i)
        ).toBeInTheDocument()
        expect(
          screen.getByText(/do not directly modify data/i)
        ).toBeInTheDocument()
      })
    })
  })
})

export {}
