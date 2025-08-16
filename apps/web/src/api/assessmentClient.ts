const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// Assessment Types
export interface AssessmentItem {
  id: string
  type:
    | 'multiple-choice'
    | 'drag-drop'
    | 'audio-response'
    | 'drawing'
    | 'text-input'
  question: string
  audioUrl?: string
  imageUrl?: string
  options?: AssessmentOption[]
  correctAnswer?: string | string[]
  difficultyLevel: 'L0' | 'L1' | 'L2' | 'L3' | 'L4'
  estimatedDuration: number // seconds
  adaptiveMetadata?: {
    prerequisiteSkills: string[]
    targetSkills: string[]
    cognitiveLoad: 'low' | 'medium' | 'high'
  }
}

export interface AssessmentOption {
  id: string
  text: string
  imageUrl?: string
  audioUrl?: string
}

export interface AssessmentSession {
  id: string
  learnerId: string
  type: 'baseline' | 'progress' | 'diagnostic'
  status: 'not-started' | 'in-progress' | 'completed' | 'paused'
  startedAt?: string
  completedAt?: string
  currentItemIndex: number
  totalItems: number
  responses: AssessmentResponse[]
  estimatedLevel: 'L0' | 'L1' | 'L2' | 'L3' | 'L4'
  gradeBand: 'K-2' | '3-5' | '6-12'
  adaptiveSettings: {
    audioFirst: boolean
    largeTargets: boolean
    simplifiedInterface: boolean
    timeLimit?: number
  }
}

export interface AssessmentResponse {
  itemId: string
  response: string | string[]
  isCorrect: boolean
  timeSpent: number // milliseconds
  attempts: number
  confidenceLevel?: 'low' | 'medium' | 'high'
  timestamp: string
}

export interface AssessmentReport {
  sessionId: string
  learnerId: string
  type: 'baseline' | 'progress' | 'diagnostic'
  status: 'BASELINE_COMPLETE' | 'PROGRESS_COMPLETE' | 'DIAGNOSTIC_COMPLETE'
  completedAt: string
  surfaceLevel: 'L0' | 'L1' | 'L2' | 'L3' | 'L4'
  totalItems: number
  correctAnswers: number
  accuracyPercentage: number
  averageResponseTime: number
  skillsAssessed: SkillAssessment[]
  recommendations: string[]
  nextSteps: string[]
}

export interface SkillAssessment {
  skillId: string
  skillName: string
  level: 'L0' | 'L1' | 'L2' | 'L3' | 'L4'
  mastery: 'emerging' | 'developing' | 'proficient' | 'advanced'
  confidence: number // 0-1
  itemsAssessed: number
}

export interface StartAssessmentRequest {
  learnerId: string
  type: 'baseline' | 'progress' | 'diagnostic'
  gradeBand: 'K-2' | '3-5' | '6-12'
  adaptiveSettings: {
    audioFirst?: boolean
    largeTargets?: boolean
    simplifiedInterface?: boolean
    timeLimit?: number
  }
}

export interface SubmitResponseRequest {
  sessionId: string
  itemId: string
  response: string | string[]
  timeSpent: number
  attempts: number
  confidenceLevel?: 'low' | 'medium' | 'high'
}

export interface NextItemResponse {
  item?: AssessmentItem
  isComplete: boolean
  sessionUpdate: Partial<AssessmentSession>
}

class AssessmentClient {
  // Start a new assessment session
  async startAssessment(
    request: StartAssessmentRequest
  ): Promise<AssessmentSession> {
    const response = await fetch(`${API_BASE}/assessment-svc/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Context': 'assessment',
      },
      body: JSON.stringify(request),
    })
    if (!response.ok) throw new Error('Failed to start assessment')
    return response.json()
  }

  // Get current assessment session
  async getSession(sessionId: string): Promise<AssessmentSession> {
    const response = await fetch(
      `${API_BASE}/assessment-svc/sessions/${sessionId}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'assessment',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to get assessment session')
    return response.json()
  }

  // Submit response and get next item
  async submitResponseAndGetNext(
    request: SubmitResponseRequest
  ): Promise<NextItemResponse> {
    const response = await fetch(
      `${API_BASE}/assessment-svc/sessions/${request.sessionId}/respond`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'assessment',
        },
        body: JSON.stringify({
          itemId: request.itemId,
          response: request.response,
          timeSpent: request.timeSpent,
          attempts: request.attempts,
          confidenceLevel: request.confidenceLevel,
        }),
      }
    )
    if (!response.ok) throw new Error('Failed to submit response')
    return response.json()
  }

  // Get next item without submitting a response (for navigation)
  async getNextItem(sessionId: string): Promise<NextItemResponse> {
    const response = await fetch(
      `${API_BASE}/assessment-svc/sessions/${sessionId}/next`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'assessment',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to get next item')
    return response.json()
  }

  // Pause/save session
  async pauseSession(sessionId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/assessment-svc/sessions/${sessionId}/pause`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'assessment',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to pause session')
  }

  // Resume session
  async resumeSession(sessionId: string): Promise<AssessmentSession> {
    const response = await fetch(
      `${API_BASE}/assessment-svc/sessions/${sessionId}/resume`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'assessment',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to resume session')
    return response.json()
  }

  // Complete assessment and generate report
  async completeAssessment(sessionId: string): Promise<AssessmentReport> {
    const response = await fetch(
      `${API_BASE}/assessment-svc/sessions/${sessionId}/complete`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'assessment',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to complete assessment')
    return response.json()
  }

  // Get assessment report
  async getReport(sessionId: string): Promise<AssessmentReport> {
    const response = await fetch(
      `${API_BASE}/assessment-svc/sessions/${sessionId}/report`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'assessment',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to get assessment report')
    return response.json()
  }

  // Get learner's assessment history
  async getLearnerAssessments(learnerId: string): Promise<AssessmentSession[]> {
    const response = await fetch(
      `${API_BASE}/assessment-svc/learners/${learnerId}/assessments`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'assessment',
        },
      }
    )
    if (!response.ok) throw new Error('Failed to get learner assessments')
    return response.json()
  }

  // Auto-save session data (for periodic saves)
  async autoSaveSession(
    sessionId: string,
    partialData: Partial<AssessmentSession>
  ): Promise<void> {
    const response = await fetch(
      `${API_BASE}/assessment-svc/sessions/${sessionId}/autosave`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'assessment',
        },
        body: JSON.stringify(partialData),
      }
    )
    if (!response.ok) throw new Error('Failed to auto-save session')
  }
}

export const assessmentClient = new AssessmentClient()
