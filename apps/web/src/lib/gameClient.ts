/**
 * Game Client API
 * Provides interface to the game-gen-svc for dynamic game generation and session management
 */

// Game Manifest Types
export interface GameElement {
  id: string
  type: 'text' | 'image' | 'button' | 'input' | 'draggable' | 'dropzone'
  position: { x: number; y: number }
  size: { width: number; height: number }
  content?: string
  styles?: Record<string, string>
  properties?: Record<string, any>
}

export interface GameInteraction {
  id: string
  type: 'click' | 'drag' | 'input' | 'hover' | 'keypress'
  targetElementId: string
  trigger?: string
  response?: string
  points?: number
  timeLimit?: number
}

export interface GameSuccessCriteria {
  id: string
  type:
    | 'interaction_complete'
    | 'score_threshold'
    | 'time_limit'
    | 'all_interactions'
  value?: number
  interactions?: string[]
}

export interface GameScene {
  id: string
  title: string
  description?: string
  elements: GameElement[]
  interactions: GameInteraction[]
  successCriteria: GameSuccessCriteria[]
  timeLimit?: number
  backgroundImage?: string
  backgroundMusic?: string
}

export interface GameManifest {
  id: string
  title: string
  description: string
  version: string
  timeLimit: number
  maxScore: number
  scenes: GameScene[]
  metadata: {
    topic: string
    difficulty: 'easy' | 'medium' | 'hard'
    gameType: 'reset'
    createdAt: string
    estimatedDuration: number
  }
}

// Game Session Types
export interface GameSession {
  sessionId: string
  gameId: string
  manifestId: string
  status: 'pending' | 'active' | 'paused' | 'completed' | 'failed'
  startedAt: string
  completedAt?: string
  currentSceneId?: string
  progress: {
    completedScenes: string[]
    currentScore: number
    timeElapsed: number
    interactions: number
  }
}

export interface GamePerformance {
  score: number
  maxScore: number
  accuracy: number
  completionTime: number
  interactions: number
  scenesCompleted: number
  totalScenes: number
  mistakes: number
  hintsUsed: number
}

// API Request/Response Types
export interface GameGenerationRequest {
  topic: string
  difficulty: 'easy' | 'medium' | 'hard'
  duration: number
  gameType?: 'reset'
  playerLevel?: number
  preferences?: Record<string, any>
}

export interface GameGenerationResponse {
  gameId: string
  manifest: GameManifest
}

export interface SessionStartResponse {
  sessionId: string
  gameId: string
  manifestId: string
  status: 'active'
  startedAt: string
}

export interface SessionEndResponse {
  sessionId: string
  completedAt: string
  performance: GamePerformance
}

// Game Events
export type GameEventType =
  | 'GAME_STARTED'
  | 'GAME_PAUSED'
  | 'GAME_RESUMED'
  | 'SCENE_STARTED'
  | 'SCENE_COMPLETED'
  | 'INTERACTION_PERFORMED'
  | 'GAME_COMPLETED'
  | 'GAME_FAILED'

export interface GameEvent {
  type: GameEventType
  timestamp: string
  sessionId: string
  gameId: string
  sceneId?: string
  data?: Record<string, any>
}

// API Client Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000'
const GAME_SERVICE_URL = `${API_BASE_URL}/api/game`

class GameClientError extends Error {
  constructor(
    message: string,
    public status?: number,
    public code?: string
  ) {
    super(message)
    this.name = 'GameClientError'
  }
}

/**
 * Game Client for interacting with game-gen-svc
 */
export class GameClient {
  private baseUrl: string

  constructor(baseUrl: string = GAME_SERVICE_URL) {
    this.baseUrl = baseUrl
  }

  /**
   * Generate a new game based on requirements
   */
  async generateGame(
    request: GameGenerationRequest
  ): Promise<GameGenerationResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ message: 'Failed to generate game' }))
        throw new GameClientError(
          error.message || 'Failed to generate game',
          response.status,
          error.code
        )
      }

      return await response.json()
    } catch (error) {
      if (error instanceof GameClientError) throw error
      throw new GameClientError('Network error while generating game')
    }
  }

  /**
   * Start a new game session
   */
  async startSession(
    gameId: string,
    manifestId?: string
  ): Promise<SessionStartResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ gameId, manifestId }),
      })

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ message: 'Failed to start session' }))
        throw new GameClientError(
          error.message || 'Failed to start session',
          response.status,
          error.code
        )
      }

      return await response.json()
    } catch (error) {
      if (error instanceof GameClientError) throw error
      throw new GameClientError('Network error while starting session')
    }
  }

  /**
   * Get current game session details
   */
  async getGameSession(sessionId: string): Promise<GameSession> {
    try {
      const response = await fetch(`${this.baseUrl}/session/${sessionId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ message: 'Failed to get session' }))
        throw new GameClientError(
          error.message || 'Failed to get session',
          response.status,
          error.code
        )
      }

      return await response.json()
    } catch (error) {
      if (error instanceof GameClientError) throw error
      throw new GameClientError('Network error while getting session')
    }
  }

  /**
   * Update game session progress
   */
  async updateSession(
    sessionId: string,
    progress: Partial<GameSession['progress']>
  ): Promise<GameSession> {
    try {
      const response = await fetch(`${this.baseUrl}/session/${sessionId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ progress }),
      })

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ message: 'Failed to update session' }))
        throw new GameClientError(
          error.message || 'Failed to update session',
          response.status,
          error.code
        )
      }

      return await response.json()
    } catch (error) {
      if (error instanceof GameClientError) throw error
      throw new GameClientError('Network error while updating session')
    }
  }

  /**
   * End a game session with performance data
   */
  async endSession(
    sessionId: string,
    performance: GamePerformance
  ): Promise<SessionEndResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/session/${sessionId}/end`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ performance }),
      })

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ message: 'Failed to end session' }))
        throw new GameClientError(
          error.message || 'Failed to end session',
          response.status,
          error.code
        )
      }

      return await response.json()
    } catch (error) {
      if (error instanceof GameClientError) throw error
      throw new GameClientError('Network error while ending session')
    }
  }

  /**
   * Emit a game event
   */
  async emitEvent(
    type: GameEventType,
    data: Omit<GameEvent, 'type' | 'timestamp'>
  ): Promise<void> {
    try {
      const event: GameEvent = {
        type,
        timestamp: new Date().toISOString(),
        ...data,
      }

      // Emit to backend for tracking
      await fetch(`${this.baseUrl}/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(event),
      })

      // Also emit as browser event for local handling
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent(type, { detail: event }))
      }
    } catch (error) {
      // Events are fire-and-forget, don't throw errors
      console.warn('Failed to emit game event:', error)
    }
  }

  /**
   * Get game manifest by ID
   */
  async getGameManifest(gameId: string): Promise<GameManifest> {
    try {
      const response = await fetch(`${this.baseUrl}/manifest/${gameId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ message: 'Failed to get manifest' }))
        throw new GameClientError(
          error.message || 'Failed to get manifest',
          response.status,
          error.code
        )
      }

      return await response.json()
    } catch (error) {
      if (error instanceof GameClientError) throw error
      throw new GameClientError('Network error while getting manifest')
    }
  }

  /**
   * Submit interaction result
   */
  async submitInteraction(
    sessionId: string,
    interactionId: string,
    result: {
      success: boolean
      timeToComplete: number
      attempts: number
      value?: any
    }
  ): Promise<void> {
    try {
      await fetch(`${this.baseUrl}/session/${sessionId}/interaction`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          interactionId,
          result,
          timestamp: new Date().toISOString(),
        }),
      })
    } catch (error) {
      console.warn('Failed to submit interaction:', error)
    }
  }
}

// Default client instance
export const gameClient = new GameClient()

// Helper functions for common game operations
export const GameHelpers = {
  /**
   * Calculate game progress percentage
   */
  calculateProgress(session: GameSession, manifest: GameManifest): number {
    const totalScenes = manifest.scenes.length
    const completedScenes = session.progress.completedScenes.length
    return totalScenes > 0 ? (completedScenes / totalScenes) * 100 : 0
  },

  /**
   * Format time display
   */
  formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  },

  /**
   * Calculate performance grade
   */
  calculateGrade(performance: GamePerformance): string {
    const scorePercentage = (performance.score / performance.maxScore) * 100
    if (scorePercentage >= 90) return 'A+'
    if (scorePercentage >= 85) return 'A'
    if (scorePercentage >= 80) return 'A-'
    if (scorePercentage >= 75) return 'B+'
    if (scorePercentage >= 70) return 'B'
    if (scorePercentage >= 65) return 'B-'
    if (scorePercentage >= 60) return 'C+'
    if (scorePercentage >= 55) return 'C'
    if (scorePercentage >= 50) return 'C-'
    return 'F'
  },

  /**
   * Determine performance level
   */
  getPerformanceLevel(
    performance: GamePerformance
  ): 'excellent' | 'good' | 'average' | 'needs_improvement' {
    const scorePercentage = (performance.score / performance.maxScore) * 100
    if (scorePercentage >= 85) return 'excellent'
    if (scorePercentage >= 70) return 'good'
    if (scorePercentage >= 60) return 'average'
    return 'needs_improvement'
  },

  /**
   * Check if scene is completed based on success criteria
   */
  checkSceneCompletion(
    scene: GameScene,
    completedInteractions: string[],
    currentScore: number,
    timeElapsed: number
  ): boolean {
    return scene.successCriteria.every(criteria => {
      switch (criteria.type) {
        case 'interaction_complete':
          return (
            criteria.interactions?.every(id =>
              completedInteractions.includes(id)
            ) ?? false
          )
        case 'score_threshold':
          return currentScore >= (criteria.value ?? 0)
        case 'time_limit':
          return timeElapsed <= (criteria.value ?? Infinity)
        case 'all_interactions':
          return scene.interactions.every(interaction =>
            completedInteractions.includes(interaction.id)
          )
        default:
          return false
      }
    })
  },
}
