import { LearnerProfile } from '../hooks/useOnboarding'

const API_BASE = process.env.VITE_API_BASE_URL || '/api'

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
      ...profile,
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
}

export const learnerClient = new LearnerClient()
