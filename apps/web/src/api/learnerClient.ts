// Base API URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface Learner {
  id: string
  guardianId: string
  firstName: string
  lastName: string
  dateOfBirth: string
  gradeDefault: number
  gradeBand: string
  specialNeeds?: string
  interests?: string[]
  tenantId?: string
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface CreateLearnerRequest {
  guardianId: string
  firstName: string
  lastName: string
  dateOfBirth: string
  gradeDefault: number
  gradeBand: string
  specialNeeds?: string
  interests?: string[]
  tenantId?: string
}

export interface UpdateLearnerRequest
  extends Partial<Omit<CreateLearnerRequest, 'guardianId'>> {
  id: string
}

export interface LearnerProgress {
  learnerId: string
  totalHours: number
  weeklyHours: number
  completedLessons: number
  averageScore: number
  streakDays: number
  lastActivity: string
}

export interface BrainPersona {
  alias: string // Never logged, PII-protected
  voice: 'friendly' | 'encouraging' | 'professional' | 'playful'
  tone: 'casual' | 'formal' | 'nurturing' | 'direct'
  personalityTraits: string[]
  preferredSubjects: string[]
  lastUpdated: string
}

export interface LearnerPreferences {
  theme: 'light' | 'dark' | 'auto'
  language: string
  timezone: string
  accessibilityOptions: AccessibilityOptions
  notificationSettings: NotificationSettings
}

export interface AccessibilityOptions {
  fontSize: 'small' | 'medium' | 'large' | 'extra-large'
  highContrast: boolean
  screenReader: boolean
  keyboardNavigation: boolean
  reducedMotion: boolean
}

export interface NotificationSettings {
  email: boolean
  push: boolean
  sms: boolean
  parentNotifications: boolean
  achievementAlerts: boolean
  assignmentReminders: boolean
  progressUpdates: boolean
}

export interface TeacherAssignment {
  id: string
  teacherId: string
  teacherName: string
  teacherEmail: string
  email: string // alias for teacherEmail
  subject: string
  assignedAt: string
  assignedDate: string // alias for assignedAt
  status: 'active' | 'inactive'
  role: 'primary' | 'secondary' | 'specialist'
}

export interface GradeBandPreview {
  gradeLevel: string
  currentGrade: number
  previewGrade: number
  uiTheme: string
  contentComplexity: 'elementary' | 'middle' | 'high'
  featureSet: string[]
  exampleContent: {
    mathSample: string
    readingSample: string
    scienceSample: string
  }
}

export interface LearnerProfile {
  id: string
  firstName: string
  lastName: string
  gradeLevel: number
  school: string
  enrollmentDate: string
  preferences?: LearnerPreferences
  persona?: BrainPersona
}

class LearnerClient {
  async createLearner(learnerData: CreateLearnerRequest): Promise<Learner> {
    const response = await fetch(`${API_BASE}/learner-svc/learners`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(learnerData),
    })

    if (!response.ok) {
      throw new Error(`Failed to create learner: ${response.statusText}`)
    }

    return response.json()
  }

  async updateLearner(learnerData: UpdateLearnerRequest): Promise<Learner> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerData.id}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(learnerData),
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to update learner: ${response.statusText}`)
    }

    return response.json()
  }

  async getLearner(learnerId: string): Promise<Learner> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get learner: ${response.statusText}`)
    }

    return response.json()
  }

  async getLearnersByGuardian(guardianId: string): Promise<Learner[]> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners?guardianId=${guardianId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get learners: ${response.statusText}`)
    }

    return response.json()
  }

  async deleteLearner(learnerId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}`,
      {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to delete learner: ${response.statusText}`)
    }
  }

  async getLearnerProgress(learnerId: string): Promise<LearnerProgress> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}/progress`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get learner progress: ${response.statusText}`)
    }

    return response.json()
  }

  async createLearnerFromProfile(
    guardianId: string,
    profile: LearnerProfile
  ): Promise<Learner> {
    return this.createLearner({
      guardianId,
      firstName: profile.firstName,
      lastName: profile.lastName,
      dateOfBirth: profile.enrollmentDate, // Map enrollment date as birth date for now
      gradeDefault: profile.gradeLevel,
      gradeBand: `Grade ${profile.gradeLevel}`, // Map grade level to grade band
      specialNeeds: undefined,
      interests: [],
    })
  }

  async bulkCreateLearners(
    guardianId: string,
    profiles: LearnerProfile[]
  ): Promise<Learner[]> {
    const results = await Promise.all(
      profiles.map(profile =>
        this.createLearnerFromProfile(guardianId, profile)
      )
    )
    return results
  }

  // Grade calculation utilities
  calculateGradeFromAge(age: number): number {
    return Math.max(0, Math.min(12, age - 5))
  }

  calculateGradeFromDOB(dateOfBirth: string): number {
    const birth = new Date(dateOfBirth)
    const today = new Date()
    let age = today.getFullYear() - birth.getFullYear()
    const monthDiff = today.getMonth() - birth.getMonth()
    if (
      monthDiff < 0 ||
      (monthDiff === 0 && today.getDate() < birth.getDate())
    ) {
      age--
    }
    return this.calculateGradeFromAge(age)
  }

  getGradeBand(grade: number): string {
    if (grade <= 2) return 'Early Elementary (K-2)'
    if (grade <= 5) return 'Elementary (3-5)'
    if (grade <= 8) return 'Middle School (6-8)'
    return 'High School (9-12)'
  }

  // S3-07: Learner Profile Management
  async getLearnerProfile(learnerId: string): Promise<LearnerProfile> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}/profile`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learner',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to get learner profile')
    return response.json()
  }

  async getTeacherAssignments(learnerId: string): Promise<TeacherAssignment[]> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}/teachers`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learner',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to get teacher assignments')
    const assignments = await response.json()
    // Add computed properties for compatibility
    return assignments.map((assignment: TeacherAssignment) => ({
      ...assignment,
      email: assignment.teacherEmail,
      assignedDate: assignment.assignedAt,
    }))
  }

  async getGradeBandPreview(learnerId: string): Promise<GradeBandPreview> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}/grade-preview`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learner',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to get grade band preview')
    const preview = await response.json()
    // Add computed properties for compatibility
    return {
      ...preview,
      currentGrade: parseInt(preview.gradeLevel) || 1,
      previewGrade: parseInt(preview.gradeLevel) || 1,
    }
  }

  async getAvailableVoices(): Promise<string[]> {
    // Fallback implementation for client-side
    return ['friendly', 'encouraging', 'professional', 'playful']
  }

  async getAvailableTones(): Promise<string[]> {
    // Fallback implementation for client-side
    return ['formal', 'casual', 'nurturing', 'direct']
  }

  // S3-07: Brain Persona Management (PII-protected)
  async getBrainPersona(learnerId: string): Promise<BrainPersona> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}/persona`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learner',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to get brain persona')
    return response.json()
  }

  async updateBrainPersona(
    learnerId: string,
    persona: Partial<BrainPersona>
  ): Promise<BrainPersona> {
    // Client-side profanity/PII guard before sending
    const cleanedPersona = this.sanitizePersonaForSend(persona)

    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}/persona`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learner',
        },
        body: JSON.stringify(cleanedPersona),
      }
    )
    if (!response.ok) throw new Error('Failed to update brain persona')
    return response.json()
  }

  // PII Protection: Client-side sanitization (alias is never logged)
  sanitizePersona(persona: Partial<BrainPersona>): {
    isValid: boolean
    reason?: string
  } {
    if (!persona.alias) {
      return { isValid: true }
    }

    // Basic profanity filter (client-side mirror)
    const profanityList = [
      'damn',
      'hell',
      'stupid',
      'idiot',
      'dumb',
      'hate',
      'shut up',
      'kill',
      'die',
      'dead',
      'murder',
      'stab',
      'gun',
      'bomb',
    ]

    // PII detection patterns
    const piiPatterns = [
      /\b\d{3}-\d{2}-\d{4}\b/, // SSN
      /\b\d{3}-\d{3}-\d{4}\b/, // Phone
      /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/, // Email
      /\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b/, // Credit card
    ]

    let alias = persona.alias.toLowerCase()

    // Check for profanity
    for (const word of profanityList) {
      if (alias.includes(word)) {
        return {
          isValid: false,
          reason: 'Alias contains inappropriate language',
        }
      }
    }

    // Check for PII
    for (const pattern of piiPatterns) {
      if (pattern.test(persona.alias)) {
        return {
          isValid: false,
          reason: 'Alias cannot contain personal information',
        }
      }
    }

    return { isValid: true }
  }

  private sanitizePersonaForSend(
    persona: Partial<BrainPersona>
  ): Partial<BrainPersona> {
    const validation = this.sanitizePersona(persona)
    if (!validation.isValid) {
      throw new Error(validation.reason || 'Invalid persona data')
    }

    return { ...persona }
  }

  // Learner Preferences
  async getLearnerPreferences(learnerId: string): Promise<LearnerPreferences> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}/preferences`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learner',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to get learner preferences')
    return response.json()
  }

  async updateLearnerPreferences(
    learnerId: string,
    preferences: Partial<LearnerPreferences>
  ): Promise<LearnerPreferences> {
    const response = await fetch(
      `${API_BASE}/learner-svc/learners/${learnerId}/preferences`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learner',
        },
        body: JSON.stringify(preferences),
      }
    )
    if (!response.ok) throw new Error('Failed to update learner preferences')
    return response.json()
  }
}

export const learnerClient = new LearnerClient()
