export interface Learner {
  id: string
  firstName: string
  lastName: string
  email: string
  gradeLevel: string
  dateOfBirth: string
  parentEmail?: string
  profileImage?: string
  status: 'active' | 'inactive' | 'pending'
  assignedAt: string
  lastActivity?: string
  subjects: SubjectAssignment[]
  academicProgress: AcademicProgress
  approvalHistory: ApprovalRecord[]
}

export interface SubjectAssignment {
  id: string
  learnerId: string
  subjectType:
    | 'ELA'
    | 'Math'
    | 'Science'
    | 'Social Studies'
    | 'Art'
    | 'Music'
    | 'PE'
    | 'Other'
  customSubjectName?: string
  assignedAt: string
  status: 'active' | 'paused' | 'completed'
  progressPercentage: number
  currentUnit?: string
  nextMilestone?: string
  estimatedCompletion?: string
}

export interface AcademicProgress {
  overallScore: number
  gradeEquivalent: string
  strengths: string[]
  areasForImprovement: string[]
  lastAssessment: string
  totalHoursLogged: number
  weeklyGoalHours: number
  completedAssignments: number
  totalAssignments: number
}

export interface ApprovalRecord {
  id: string
  learnerId: string
  type:
    | 'activity_request'
    | 'grade_change'
    | 'subject_completion'
    | 'parent_concern'
    | 'accommodation_request'
  title: string
  description: string
  status: 'pending' | 'approved' | 'denied' | 'needs_info'
  priority: 'low' | 'medium' | 'high' | 'urgent'
  requestedBy: string
  requestedAt: string
  reviewedBy?: string
  reviewedAt?: string
  comments?: string
  relatedSubject?: string
  attachments?: string[]
}

export interface TeacherInvite {
  id: string
  teacherEmail: string
  invitedBy: string
  schoolId: string
  schoolName: string
  role: 'teacher' | 'lead_teacher' | 'specialist'
  subjects: string[]
  gradeLevel?: string
  inviteToken: string
  expiresAt: string
  status: 'pending' | 'accepted' | 'expired' | 'declined'
  sentAt: string
}

export interface TeacherProfile {
  id: string
  firstName: string
  lastName: string
  email: string
  schoolId: string
  schoolName: string
  role: 'teacher' | 'lead_teacher' | 'specialist'
  subjects: string[]
  gradeLevel?: string
  profileImage?: string
  bio?: string
  yearsExperience?: number
  certifications: string[]
  preferredContactMethod: 'email' | 'phone' | 'app'
  phoneNumber?: string
  status: 'active' | 'inactive'
  createdAt: string
  lastLogin?: string
}

export interface LearnerStats {
  totalLearners: number
  activeLearners: number
  pendingApprovals: number
  averageProgress: number
  hoursThisWeek: number
  completedAssignments: number
  subjectDistribution: Record<string, number>
}

export interface RecentActivity {
  id: string
  type:
    | 'assignment_completed'
    | 'approval_pending'
    | 'parent_message'
    | 'progress_milestone'
  title: string
  description: string
  timestamp: string
  learnerId?: string
  learnerName?: string
  urgent?: boolean
}

class TeacherClient {
  private baseURL: string

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:3001'
  }

  private async request<T>(
    endpoint: string,
    options: {
      method?: string
      body?: string
      headers?: Record<string, string>
    } = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`
    const token = localStorage.getItem('authToken')

    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
        'X-Context': 'teacher',
        ...(options.headers || {}),
      },
    })

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`)
    }

    return response.json()
  }

  // Teacher Profile & Invites
  async acceptInvite(
    inviteToken: string,
    teacherData: Partial<TeacherProfile>
  ): Promise<TeacherProfile> {
    return this.request<TeacherProfile>('/api/v1/teacher/invites/accept', {
      method: 'POST',
      body: JSON.stringify({ inviteToken, ...teacherData }),
    })
  }

  async getInviteDetails(inviteToken: string): Promise<TeacherInvite> {
    return this.request<TeacherInvite>(`/api/v1/teacher/invites/${inviteToken}`)
  }

  async getProfile(): Promise<TeacherProfile> {
    return this.request<TeacherProfile>('/api/v1/teacher/profile')
  }

  async updateProfile(
    profileData: Partial<TeacherProfile>
  ): Promise<TeacherProfile> {
    return this.request<TeacherProfile>('/api/v1/teacher/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    })
  }

  // Dashboard & Stats
  async getDashboardStats(): Promise<LearnerStats> {
    return this.request<LearnerStats>('/api/v1/teacher/dashboard/stats')
  }

  async getRecentActivity(): Promise<RecentActivity[]> {
    return this.request<RecentActivity[]>('/api/v1/teacher/dashboard/activity')
  }

  // Learner Management
  async getAssignedLearners(): Promise<Learner[]> {
    return this.request<Learner[]>('/api/v1/teacher/learners')
  }

  async getLearner(learnerId: string): Promise<Learner> {
    return this.request<Learner>(`/api/v1/teacher/learners/${learnerId}`)
  }

  async updateLearnerNotes(learnerId: string, notes: string): Promise<void> {
    return this.request<void>(`/api/v1/teacher/learners/${learnerId}/notes`, {
      method: 'PUT',
      body: JSON.stringify({ notes }),
    })
  }

  async updateLearnerStatus(
    learnerId: string,
    status: 'active' | 'inactive' | 'pending'
  ): Promise<Learner> {
    return this.request<Learner>(
      `/api/v1/teacher/learners/${learnerId}/status`,
      {
        method: 'PUT',
        body: JSON.stringify({ status }),
      }
    )
  }

  // Subject Management
  async getAvailableSubjects(): Promise<string[]> {
    return this.request<string[]>('/api/v1/teacher/subjects/available')
  }

  async assignSubjectToLearner(
    learnerId: string,
    subjectData: {
      subjectType: string
      customSubjectName?: string
      weeklyGoalHours?: number
    }
  ): Promise<SubjectAssignment> {
    return this.request<SubjectAssignment>(
      `/api/v1/teacher/learners/${learnerId}/subjects`,
      {
        method: 'POST',
        body: JSON.stringify(subjectData),
      }
    )
  }

  async updateSubjectAssignment(
    learnerId: string,
    subjectId: string,
    updates: Partial<SubjectAssignment>
  ): Promise<SubjectAssignment> {
    return this.request<SubjectAssignment>(
      `/api/v1/teacher/learners/${learnerId}/subjects/${subjectId}`,
      {
        method: 'PUT',
        body: JSON.stringify(updates),
      }
    )
  }

  async removeSubjectFromLearner(
    learnerId: string,
    subjectId: string
  ): Promise<void> {
    return this.request<void>(
      `/api/v1/teacher/learners/${learnerId}/subjects/${subjectId}`,
      {
        method: 'DELETE',
      }
    )
  }

  async getLearnerProgress(
    learnerId: string,
    subjectId?: string
  ): Promise<AcademicProgress> {
    const endpoint = subjectId
      ? `/api/v1/teacher/learners/${learnerId}/progress?subject=${subjectId}`
      : `/api/v1/teacher/learners/${learnerId}/progress`
    return this.request<AcademicProgress>(endpoint)
  }

  // Approvals Management
  async getPendingApprovals(): Promise<ApprovalRecord[]> {
    return this.request<ApprovalRecord[]>('/api/v1/teacher/approvals')
  }

  async getApprovalsByLearner(learnerId: string): Promise<ApprovalRecord[]> {
    return this.request<ApprovalRecord[]>(
      `/api/v1/teacher/approvals?learnerId=${learnerId}`
    )
  }

  async reviewApproval(
    approvalId: string,
    decision: {
      status: 'approved' | 'denied' | 'needs_info'
      comments?: string
    }
  ): Promise<ApprovalRecord> {
    return this.request<ApprovalRecord>(
      `/api/v1/teacher/approvals/${approvalId}/review`,
      {
        method: 'PUT',
        body: JSON.stringify(decision),
      }
    )
  }

  async createApprovalRequest(approvalData: {
    learnerId: string
    type: ApprovalRecord['type']
    title: string
    description: string
    priority?: 'low' | 'medium' | 'high' | 'urgent'
    relatedSubject?: string
  }): Promise<ApprovalRecord> {
    return this.request<ApprovalRecord>('/api/v1/teacher/approvals', {
      method: 'POST',
      body: JSON.stringify(approvalData),
    })
  }

  // Communication & Reports
  async sendMessageToParent(
    learnerId: string,
    message: {
      subject: string
      body: string
      priority?: 'low' | 'medium' | 'high'
    }
  ): Promise<void> {
    return this.request<void>(
      `/api/v1/teacher/learners/${learnerId}/message-parent`,
      {
        method: 'POST',
        body: JSON.stringify(message),
      }
    )
  }

  async generateProgressReport(
    learnerId: string,
    options: {
      includeSubjects?: string[]
      dateRange?: { startDate: string; endDate: string }
      format: 'pdf' | 'email'
    }
  ): Promise<{ reportUrl?: string; success: boolean }> {
    return this.request<{ reportUrl?: string; success: boolean }>(
      `/api/v1/teacher/learners/${learnerId}/report`,
      {
        method: 'POST',
        body: JSON.stringify(options),
      }
    )
  }

  // Quick Actions
  async scheduleParentConference(
    learnerId: string,
    conferenceData: {
      requestedDates: string[]
      duration: number // minutes
      topic: string
      format: 'in_person' | 'video' | 'phone'
    }
  ): Promise<{ conferenceId: string }> {
    return this.request<{ conferenceId: string }>(
      `/api/v1/teacher/learners/${learnerId}/schedule-conference`,
      {
        method: 'POST',
        body: JSON.stringify(conferenceData),
      }
    )
  }

  async flagConcern(
    learnerId: string,
    concern: {
      type: 'academic' | 'behavioral' | 'attendance' | 'social' | 'other'
      severity: 'low' | 'medium' | 'high' | 'urgent'
      description: string
      recommendedActions?: string[]
    }
  ): Promise<void> {
    return this.request<void>(
      `/api/v1/teacher/learners/${learnerId}/flag-concern`,
      {
        method: 'POST',
        body: JSON.stringify(concern),
      }
    )
  }

  async requestAccommodation(
    learnerId: string,
    accommodation: {
      type:
        | 'extended_time'
        | 'alternative_format'
        | 'assistive_tech'
        | 'modified_curriculum'
        | 'other'
      description: string
      justification: string
      duration?: 'temporary' | 'permanent'
    }
  ): Promise<void> {
    return this.request<void>(
      `/api/v1/teacher/learners/${learnerId}/request-accommodation`,
      {
        method: 'POST',
        body: JSON.stringify(accommodation),
      }
    )
  }
}

export const teacherClient = new TeacherClient()
