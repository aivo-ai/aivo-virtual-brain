const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// Lesson Registry Types
export interface LessonContent {
  id: string
  type: 'video' | 'interactive' | 'text' | 'audio' | 'simulation' | 'game'
  title: string
  description?: string
  content: any // Flexible content structure
  duration?: number // in seconds
  metadata?: {
    difficulty: 'beginner' | 'intermediate' | 'advanced'
    tags: string[]
    prerequisites: string[]
    learningObjectives: string[]
  }
}

export interface LessonSection {
  id: string
  title: string
  type: 'introduction' | 'content' | 'practice' | 'assessment' | 'summary'
  content: LessonContent[]
  estimatedDuration: number
  isRequired: boolean
  completionCriteria?: {
    minTimeSpent?: number
    requiredInteractions?: string[]
    passingScore?: number
  }
}

export interface Lesson {
  id: string
  title: string
  description: string
  subject: string
  gradeLevel: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  estimatedDuration: number // total lesson duration in seconds
  learningObjectives: string[]
  prerequisites: string[]
  sections: LessonSection[]
  metadata: {
    author: string
    createdAt: string
    updatedAt: string
    version: string
    tags: string[]
    thumbnailUrl?: string
    language: string
  }
  gameBreakConfig?: {
    enabled: boolean
    intervalMinutes: number
    durationMinutes: number
    games: string[]
  }
}

export interface LessonProgress {
  lessonId: string
  learnerId: string
  status: 'not-started' | 'in-progress' | 'completed' | 'paused'
  currentSectionId?: string
  currentContentId?: string
  progress: number // 0-100 percentage
  timeSpent: number // in seconds
  sectionsCompleted: string[]
  startedAt?: string
  lastAccessedAt?: string
  completedAt?: string
  interactions: LessonInteraction[]
}

export interface LessonInteraction {
  id: string
  type: 'view' | 'click' | 'input' | 'completion' | 'pause' | 'resume' | 'skip'
  contentId: string
  timestamp: string
  data?: any
  timeSpent?: number
}

export interface LearningSession {
  id: string
  learnerId: string
  lessonId: string
  status: 'active' | 'paused' | 'completed' | 'abandoned'
  startedAt: string
  endedAt?: string
  totalTimeSpent: number
  currentPosition: {
    sectionId: string
    contentId: string
    timestamp: number
  }
  gameBreaks: GameBreakEvent[]
  telemetrySessionId: string
}

export interface GameBreakEvent {
  id: string
  triggeredAt: string
  durationMinutes: number
  gameSelected?: string
  completed: boolean
  resumedAt?: string
}

export interface LessonSearchQuery {
  query?: string
  subject?: string
  gradeLevel?: string
  difficulty?: 'beginner' | 'intermediate' | 'advanced'
  tags?: string[]
  limit?: number
  offset?: number
}

export interface LessonSearchResult {
  lessons: Lesson[]
  total: number
  hasMore: boolean
}

class LessonRegistryClient {
  // Search lessons
  async searchLessons(query: LessonSearchQuery): Promise<LessonSearchResult> {
    const params = new URLSearchParams()

    if (query.query) params.append('q', query.query)
    if (query.subject) params.append('subject', query.subject)
    if (query.gradeLevel) params.append('gradeLevel', query.gradeLevel)
    if (query.difficulty) params.append('difficulty', query.difficulty)
    if (query.tags) query.tags.forEach(tag => params.append('tags', tag))
    if (query.limit) params.append('limit', query.limit.toString())
    if (query.offset) params.append('offset', query.offset.toString())

    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/lessons/search?${params}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to search lessons')
    return response.json()
  }

  // Get lesson by ID
  async getLesson(lessonId: string): Promise<Lesson> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/lessons/${lessonId}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to get lesson')
    return response.json()
  }

  // Get lesson content
  async getLessonContent(
    lessonId: string,
    sectionId: string,
    contentId: string
  ): Promise<LessonContent> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/lessons/${lessonId}/sections/${sectionId}/content/${contentId}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to get lesson content')
    return response.json()
  }

  // Start learning session
  async startLearningSession(
    learnerId: string,
    lessonId: string
  ): Promise<LearningSession> {
    const response = await fetch(`${API_BASE}/lesson-registry-svc/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Context': 'learning',
      },
      body: JSON.stringify({
        learnerId,
        lessonId,
        telemetrySessionId: `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      }),
    })

    if (!response.ok) throw new Error('Failed to start learning session')
    return response.json()
  }

  // Get learning session
  async getLearningSession(sessionId: string): Promise<LearningSession> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/sessions/${sessionId}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to get learning session')
    return response.json()
  }

  // Update session progress
  async updateSessionProgress(
    sessionId: string,
    progress: Partial<LearningSession>
  ): Promise<void> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/sessions/${sessionId}/progress`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
        body: JSON.stringify(progress),
      }
    )

    if (!response.ok) throw new Error('Failed to update session progress')
  }

  // Record interaction
  async recordInteraction(
    sessionId: string,
    interaction: Omit<LessonInteraction, 'id' | 'timestamp'>
  ): Promise<void> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/sessions/${sessionId}/interactions`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
        body: JSON.stringify({
          ...interaction,
          timestamp: new Date().toISOString(),
        }),
      }
    )

    if (!response.ok) throw new Error('Failed to record interaction')
  }

  // Trigger game break
  async triggerGameBreak(
    sessionId: string,
    durationMinutes: number
  ): Promise<GameBreakEvent> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/sessions/${sessionId}/game-break`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
        body: JSON.stringify({
          durationMinutes,
          triggeredAt: new Date().toISOString(),
        }),
      }
    )

    if (!response.ok) throw new Error('Failed to trigger game break')
    return response.json()
  }

  // Resume from game break
  async resumeFromGameBreak(
    sessionId: string,
    gameBreakId: string
  ): Promise<void> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/sessions/${sessionId}/game-break/${gameBreakId}/resume`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
        body: JSON.stringify({
          resumedAt: new Date().toISOString(),
        }),
      }
    )

    if (!response.ok) throw new Error('Failed to resume from game break')
  }

  // End learning session
  async endLearningSession(sessionId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/sessions/${sessionId}/end`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
        body: JSON.stringify({
          endedAt: new Date().toISOString(),
        }),
      }
    )

    if (!response.ok) throw new Error('Failed to end learning session')
  }

  // Get learner progress for lesson
  async getLearnerProgress(
    learnerId: string,
    lessonId: string
  ): Promise<LessonProgress | null> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/learners/${learnerId}/lessons/${lessonId}/progress`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (response.status === 404) return null
    if (!response.ok) throw new Error('Failed to get learner progress')
    return response.json()
  }

  // Get recommended lessons
  async getRecommendedLessons(
    learnerId: string,
    limit = 10
  ): Promise<Lesson[]> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/learners/${learnerId}/recommendations?limit=${limit}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to get recommended lessons')
    return response.json()
  }

  // Get lesson analytics
  async getLessonAnalytics(lessonId: string): Promise<any> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/lessons/${lessonId}/analytics`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'learning',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to get lesson analytics')
    return response.json()
  }

  // Coursework-Lesson Linkback methods (S5-10)

  async searchLessons(params: {
    subject?: string
    gradeBand?: string
    limit?: number
  }): Promise<Lesson[]> {
    const searchParams = new URLSearchParams()
    if (params.subject) searchParams.append('subject', params.subject)
    if (params.gradeBand) searchParams.append('grade_band', params.gradeBand)
    if (params.limit) searchParams.append('limit', params.limit.toString())

    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/lessons?${searchParams}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'linkback',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to search lessons')
    return response.json()
  }

  async createCourseworkLink(request: {
    coursework_id: string
    lesson_id: string
    learner_id?: string
    mastery_weight?: number
    difficulty_adjustment?: number
    link_context?: any
  }): Promise<any> {
    const response = await fetch(`${API_BASE}/lesson-registry-svc/linkback`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Context': 'linkback',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) throw new Error('Failed to create coursework link')
    return response.json()
  }

  async getCourseworkLinks(
    courseworkId: string,
    learnerId?: string
  ): Promise<any> {
    const params = new URLSearchParams()
    if (learnerId) params.append('learner_id', learnerId)

    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/linkback/coursework/${courseworkId}/links?${params}`,
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'linkback',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to get coursework links')
    return response.json()
  }

  async deleteCourseworkLink(linkId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE}/lesson-registry-svc/linkback/links/${linkId}`,
      {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'X-Context': 'linkback',
        },
      }
    )

    if (!response.ok) throw new Error('Failed to delete coursework link')
  }
}

export const lessonRegistryClient = new LessonRegistryClient()
