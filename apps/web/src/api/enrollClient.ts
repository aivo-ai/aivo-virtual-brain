import { ScheduleBaseline } from '../hooks/useOnboarding'

const API_BASE = process.env.VITE_API_BASE_URL || '/api'

export interface Enrollment {
  id: string
  learnerId: string
  tenantId?: string
  status: 'pending' | 'active' | 'suspended' | 'completed'
  enrollmentDate: string
  expectedCompletionDate?: string
  actualCompletionDate?: string
  schedule: ScheduleBaseline
  progress: {
    totalHours: number
    completedLessons: number
    averageScore: number
    lastActivity: string
  }
  createdAt: string
  updatedAt: string
}

export interface CreateEnrollmentRequest {
  learnerId: string
  tenantId?: string
  schedule: ScheduleBaseline
  startDate?: string
}

export interface UpdateEnrollmentRequest {
  enrollmentId: string
  schedule?: ScheduleBaseline
  status?: Enrollment['status']
}

export interface DistrictEnrollmentRequest {
  learnerIds: string[]
  tenantId: string
  schedule: ScheduleBaseline
  enrollmentType: 'individual' | 'classroom' | 'district'
}

export interface EnrollmentBatch {
  id: string
  tenantId: string
  totalLearners: number
  successfulEnrollments: number
  failedEnrollments: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  createdAt: string
  completedAt?: string
}

class EnrollClient {
  async createEnrollment(
    enrollmentData: CreateEnrollmentRequest
  ): Promise<Enrollment> {
    const response = await fetch(`${API_BASE}/enrollment-router/enrollments`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(enrollmentData),
    })

    if (!response.ok) {
      throw new Error(`Failed to create enrollment: ${response.statusText}`)
    }

    return response.json()
  }

  async updateEnrollment(
    enrollmentData: UpdateEnrollmentRequest
  ): Promise<Enrollment> {
    const response = await fetch(
      `${API_BASE}/enrollment-router/enrollments/${enrollmentData.enrollmentId}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(enrollmentData),
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to update enrollment: ${response.statusText}`)
    }

    return response.json()
  }

  async getEnrollment(enrollmentId: string): Promise<Enrollment> {
    const response = await fetch(
      `${API_BASE}/enrollment-router/enrollments/${enrollmentId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get enrollment: ${response.statusText}`)
    }

    return response.json()
  }

  async getEnrollmentsByLearner(learnerId: string): Promise<Enrollment[]> {
    const response = await fetch(
      `${API_BASE}/enrollment-router/enrollments?learnerId=${learnerId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(
        `Failed to get learner enrollments: ${response.statusText}`
      )
    }

    return response.json()
  }

  async getEnrollmentsByTenant(tenantId: string): Promise<Enrollment[]> {
    const response = await fetch(
      `${API_BASE}/enrollment-router/enrollments?tenantId=${tenantId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(
        `Failed to get tenant enrollments: ${response.statusText}`
      )
    }

    return response.json()
  }

  async deleteEnrollment(enrollmentId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/enrollment-router/enrollments/${enrollmentId}`,
      {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to delete enrollment: ${response.statusText}`)
    }
  }

  async createDistrictEnrollment(
    enrollmentData: DistrictEnrollmentRequest
  ): Promise<EnrollmentBatch> {
    const response = await fetch(
      `${API_BASE}/enrollment-router/enrollments/district`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(enrollmentData),
      }
    )

    if (!response.ok) {
      throw new Error(
        `Failed to create district enrollment: ${response.statusText}`
      )
    }

    return response.json()
  }

  async getEnrollmentBatch(batchId: string): Promise<EnrollmentBatch> {
    const response = await fetch(
      `${API_BASE}/enrollment-router/enrollments/batches/${batchId}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get enrollment batch: ${response.statusText}`)
    }

    return response.json()
  }

  async enrollLearner(
    learnerId: string,
    schedule: ScheduleBaseline,
    tenantId?: string
  ): Promise<Enrollment> {
    return this.createEnrollment({
      learnerId,
      tenantId,
      schedule,
    })
  }

  async bulkEnrollLearners(
    learnerIds: string[],
    schedule: ScheduleBaseline,
    tenantId?: string
  ): Promise<Enrollment[]> {
    if (tenantId) {
      // Use district enrollment for bulk operations with tenant
      const batch = await this.createDistrictEnrollment({
        learnerIds,
        tenantId,
        schedule,
        enrollmentType: 'district',
      })

      // Wait for batch completion and return enrollments
      return this.waitForBatchCompletion(batch.id)
    } else {
      // Individual enrollments for non-district users
      const results = await Promise.all(
        learnerIds.map(learnerId => this.enrollLearner(learnerId, schedule))
      )
      return results
    }
  }

  async waitForBatchCompletion(
    batchId: string,
    maxAttempts: number = 30
  ): Promise<Enrollment[]> {
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      const batch = await this.getEnrollmentBatch(batchId)

      if (batch.status === 'completed') {
        // Get all enrollments for this batch
        // Note: This would require additional API endpoint in real implementation
        throw new Error(
          'Batch enrollment completion tracking not fully implemented'
        )
      } else if (batch.status === 'failed') {
        throw new Error('Batch enrollment failed')
      }

      // Wait 2 seconds before next check
      await new Promise(resolve => setTimeout(resolve, 2000))
    }

    throw new Error('Batch enrollment timeout')
  }

  // Utility methods for schedule creation
  createBasicSchedule(
    weeklyHours: number,
    subjects: string[]
  ): ScheduleBaseline {
    return {
      weeklyGoal: weeklyHours,
      preferredTimeSlots: ['after-school'], // Default time slot
      subjects,
      difficulty: 'intermediate',
    }
  }

  createCustomSchedule(
    weeklyHours: number,
    timeSlots: string[],
    subjects: string[],
    difficulty: 'beginner' | 'intermediate' | 'advanced'
  ): ScheduleBaseline {
    return {
      weeklyGoal: weeklyHours,
      preferredTimeSlots: timeSlots,
      subjects,
      difficulty,
    }
  }
}

export const enrollClient = new EnrollClient()
