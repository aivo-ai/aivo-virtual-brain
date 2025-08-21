/**
 * Admin API Client for Backoffice Operations
 * S4-17 Implementation - Internal support tools with strict RBAC
 */

// Type definitions
export interface User {
  id: string
  email: string
  roles: string[]
  name?: string
}

export interface AdminStats {
  active_users: number
  pending_jobs: number
  pending_approvals: number
  system_health: 'healthy' | 'degraded' | 'unhealthy'
}

export interface SystemHealth {
  overall_status: 'healthy' | 'degraded' | 'unhealthy'
  services: ServiceHealth[]
  last_updated: string
}

export interface ServiceHealth {
  name: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  response_time: number
  uptime: number
  version: string
}

export interface AuditSummary {
  login_events_24h: number
  data_access_events_24h: number
  admin_actions_24h: number
  security_events_24h: number
}

export interface AlertItem {
  id: string
  type: 'error' | 'warning' | 'info'
  title: string
  description: string
  timestamp: string
  resolved: boolean
  service?: string
}

export interface ApprovalQueueItem {
  id: string
  title: string
  description: string
  type: 'iep_change' | 'level_change' | 'parent_concern' | 'accommodation_request'
  status: 'pending' | 'approved' | 'denied' | 'expired'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  requested_by: string
  requested_by_role: string
  required_roles?: string[]
  approved_roles?: string[]
  pending_roles?: string[]
  created_at: string
  expires_at?: string
  context_data?: any
}

export interface ApprovalStats {
  total_requests: number
  pending_count: number
  approved_count: number
  denied_count: number
  expired_count: number
  avg_response_time: number
}

export interface JobQueue {
  name: string
  service: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  pending_count: number
  running_count: number
  failed_count: number
  completed_count: number
  last_updated: string
}

export interface QueueStats {
  total_jobs: number
  pending_jobs: number
  running_jobs: number
  failed_jobs: number
  completed_jobs: number
  success_rate: number
}

export interface JobItem {
  id: string
  name?: string
  type: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  queue: string
  created_at: string
  started_at?: string
  completed_at?: string
  duration?: number
  retry_count: number
  progress?: number
  error_message?: string
  error_stack?: string
  payload?: any
  result?: any
}

export interface LearnerState {
  learner_id: string
  learner_name: string
  current_level: string
  iep_status: string
  last_activity: string
  consent_status: 'active' | 'expired' | 'revoked'
  guardian_consent: boolean
  data_access_log: DataAccessEntry[]
}

export interface DataAccessEntry {
  timestamp: string
  accessor: string
  action: string
  purpose: string
  approved_by?: string
}

export interface SupportSession {
  session_id: string
  learner_id: string
  staff_member: string
  purpose: string
  consent_token: string
  started_at: string
  expires_at: string
  actions_taken: string[]
}

export interface AuditEvent {
  id: string
  timestamp: string
  event_type: string
  actor: string
  resource: string
  action: string
  details: any
  ip_address?: string
  user_agent?: string
}

// Admin API Client Class
class AdminAPIClient {
  private baseUrl: string
  private token: string | null = null

  constructor() {
    this.baseUrl = import.meta.env.VITE_ADMIN_API_URL || 'http://localhost:8000/admin'
  }

  setAuthToken(token: string) {
    this.token = token
  }

  private async makeRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })

    if (!response.ok) {
      if (response.status === 403) {
        throw new Error('Access denied: Staff permissions required')
      }
      if (response.status === 401) {
        throw new Error('Authentication failed')
      }
      throw new Error(`API request failed: ${response.statusText}`)
    }

    return response.json()
  }

  // System Stats and Health
  async getSystemStats(): Promise<AdminStats> {
    return this.makeRequest<AdminStats>('/stats')
  }

  async getSystemHealth(): Promise<SystemHealth> {
    return this.makeRequest<SystemHealth>('/health')
  }

  async getAuditSummary(): Promise<AuditSummary> {
    return this.makeRequest<AuditSummary>('/audit/summary')
  }

  async getSystemAlerts(): Promise<AlertItem[]> {
    return this.makeRequest<AlertItem[]>('/alerts')
  }

  // Approval Queue Management
  async getApprovalQueue(): Promise<ApprovalQueueItem[]> {
    return this.makeRequest<ApprovalQueueItem[]>('/approvals')
  }

  async getApprovalStats(): Promise<ApprovalStats> {
    return this.makeRequest<ApprovalStats>('/approvals/stats')
  }

  // Job Queue Management
  async getJobQueues(): Promise<JobQueue[]> {
    return this.makeRequest<JobQueue[]>('/queues')
  }

  async getQueueStats(): Promise<QueueStats> {
    return this.makeRequest<QueueStats>('/queues/stats')
  }

  async getQueueJobs(queueName: string, filters: any): Promise<JobItem[]> {
    const params = new URLSearchParams({
      service: filters.service,
      status: filters.status,
      priority: filters.priority
    })
    return this.makeRequest<JobItem[]>(`/queues/${queueName}/jobs?${params}`)
  }

  async requeueJob(jobId: string): Promise<{ message: string }> {
    return this.makeRequest<{ message: string }>(`/jobs/${jobId}/requeue`, {
      method: 'POST'
    })
  }

  async cancelJob(jobId: string): Promise<{ message: string }> {
    return this.makeRequest<{ message: string }>(`/jobs/${jobId}/cancel`, {
      method: 'POST'
    })
  }

  async retryJob(jobId: string): Promise<{ message: string }> {
    return this.makeRequest<{ message: string }>(`/jobs/${jobId}/retry`, {
      method: 'POST'
    })
  }

  // Learner State Inspection (requires consent)
  async requestSupportSession(learnerId: string, purpose: string): Promise<{ consent_url: string }> {
    return this.makeRequest<{ consent_url: string }>('/support-session/request', {
      method: 'POST',
      body: JSON.stringify({ learner_id: learnerId, purpose })
    })
  }

  async getLearnerState(learnerId: string, consentToken: string): Promise<LearnerState> {
    return this.makeRequest<LearnerState>(`/learners/${learnerId}/state`, {
      headers: {
        'X-Consent-Token': consentToken
      }
    })
  }

  async createSupportSession(learnerId: string, purpose: string, consentToken: string): Promise<SupportSession> {
    return this.makeRequest<SupportSession>('/support-session', {
      method: 'POST',
      body: JSON.stringify({
        learner_id: learnerId,
        purpose,
        consent_token: consentToken
      })
    })
  }

  // Audit and Security
  async getAuditEvents(filters: {
    event_type?: string
    actor?: string
    resource?: string
    start_date?: string
    end_date?: string
    limit?: number
  }): Promise<AuditEvent[]> {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.set(key, value.toString())
    })
    return this.makeRequest<AuditEvent[]>(`/audit/events?${params}`)
  }

  async exportAuditLog(filters: any): Promise<Blob> {
    const params = new URLSearchParams(filters)
    const response = await fetch(`${this.baseUrl}/audit/export?${params}`, {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    })
    return response.blob()
  }

  // System Flags and Configuration
  async getSystemFlags(): Promise<{ [key: string]: boolean }> {
    return this.makeRequest<{ [key: string]: boolean }>('/flags')
  }

  async toggleSystemFlag(flagName: string, enabled: boolean): Promise<{ message: string }> {
    return this.makeRequest<{ message: string }>(`/flags/${flagName}`, {
      method: 'PUT',
      body: JSON.stringify({ enabled })
    })
  }

  // Mock implementations for development
  private async mockSystemStats(): Promise<AdminStats> {
    await new Promise(resolve => setTimeout(resolve, 1000))
    return {
      active_users: 342,
      pending_jobs: 18,
      pending_approvals: 7,
      system_health: 'healthy'
    }
  }

  private async mockSystemHealth(): Promise<SystemHealth> {
    await new Promise(resolve => setTimeout(resolve, 800))
    return {
      overall_status: 'healthy',
      last_updated: new Date().toISOString(),
      services: [
        { name: 'auth-svc', status: 'healthy', response_time: 45, uptime: 99.9, version: '1.2.3' },
        { name: 'orchestrator-svc', status: 'healthy', response_time: 67, uptime: 99.8, version: '2.1.0' },
        { name: 'search-svc', status: 'degraded', response_time: 150, uptime: 98.5, version: '1.4.2' },
        { name: 'approval-svc', status: 'healthy', response_time: 23, uptime: 99.9, version: '1.1.0' }
      ]
    }
  }

  private async mockAuditSummary(): Promise<AuditSummary> {
    await new Promise(resolve => setTimeout(resolve, 600))
    return {
      login_events_24h: 156,
      data_access_events_24h: 89,
      admin_actions_24h: 12,
      security_events_24h: 3
    }
  }

  private async mockSystemAlerts(): Promise<AlertItem[]> {
    return [
      {
        id: '1',
        type: 'warning',
        title: 'High Memory Usage',
        description: 'Search service memory usage is at 85%',
        timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
        resolved: false,
        service: 'search-svc'
      },
      {
        id: '2',
        type: 'info',
        title: 'Scheduled Maintenance',
        description: 'Database maintenance window scheduled for tonight 2:00 AM',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        resolved: false
      }
    ]
  }

  // Use mock data in development
  async getMockData() {
    if (import.meta.env.DEV) {
      return {
        stats: await this.mockSystemStats(),
        health: await this.mockSystemHealth(),
        auditSummary: await this.mockAuditSummary(),
        alerts: await this.mockSystemAlerts()
      }
    }
    return null
  }
}

// Create and export singleton
export const adminClient = new AdminAPIClient()
export default adminClient
