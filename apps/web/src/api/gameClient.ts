const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// Game Types from game-gen-svc
export type GameType =
  | 'vocabulary_builder'
  | 'math_puzzle'
  | 'science_experiment'
  | 'history_timeline'
  | 'reading_comprehension'
  | 'creative_writing'
  | 'logic_puzzle'
  | 'memory_game'
  | 'pattern_recognition'
  | 'critical_thinking'

export type GameDifficulty = 'beginner' | 'easy' | 'medium' | 'hard' | 'expert'
export type GameStatus =
  | 'draft'
  | 'ready'
  | 'in_progress'
  | 'completed'
  | 'failed'
export type SubjectArea =
  | 'english'
  | 'mathematics'
  | 'science'
  | 'history'
  | 'geography'
  | 'arts'
  | 'physical_education'
  | 'foreign_language'
export type GradeBand = 'K-2' | '3-5' | '6-8' | '9-12'

// Game Asset Types
export interface GameAsset {
  id: string
  type: 'image' | 'audio' | 'video' | 'text' | 'interactive'
  url?: string
  content?: string
  metadata?: Record<string, any>
}

// Game Scene Types
export interface GameScene {
  id: string
  title: string
  description: string
  type: 'intro' | 'gameplay' | 'challenge' | 'result' | 'break'
  duration_seconds?: number
  assets: GameAsset[]
  interactions: GameInteraction[]
  success_criteria?: SuccessCriteria
  next_scene_id?: string
  background?: string
  ui_elements?: UIElement[]
}

export interface GameInteraction {
  id: string
  type: 'click' | 'drag' | 'type' | 'select' | 'keyboard' | 'touch'
  target: string
  action: string
  feedback?: string
  points?: number
  required?: boolean
  keyboard_shortcut?: string
}

export interface SuccessCriteria {
  type: 'score' | 'accuracy' | 'time' | 'completion'
  target_value: number
  operator: 'gte' | 'lte' | 'eq' | 'between'
}

export interface UIElement {
  id: string
  type: 'button' | 'text' | 'input' | 'progress' | 'timer' | 'score'
  position: { x: number; y: number }
  size?: { width: number; height: number }
  properties: Record<string, any>
}

// Game Rules and Configuration
export interface GameRules {
  scoring_system: ScoringSystem
  time_limits: TimeLimits
  hint_system?: HintSystem
  pause_allowed: boolean
  save_progress: boolean
  keyboard_navigation: boolean
  accessibility_features: AccessibilityFeatures
}

export interface ScoringSystem {
  type: 'points' | 'percentage' | 'ranking' | 'pass_fail'
  max_score?: number
  bonus_multipliers?: Record<string, number>
  penalty_system?: Record<string, number>
}

export interface TimeLimits {
  total_minutes: number
  scene_timeouts?: Record<string, number>
  grace_period_seconds?: number
  warning_time_seconds?: number
}

export interface HintSystem {
  enabled: boolean
  max_hints?: number
  hint_penalty?: number
  progressive_hints?: boolean
}

export interface AccessibilityFeatures {
  screen_reader_support: boolean
  keyboard_only_navigation: boolean
  high_contrast_mode: boolean
  font_size_scaling: boolean
  color_blind_support: boolean
  audio_descriptions: boolean
}

// Main Game Manifest
export interface GameManifest {
  id: string
  learner_id: string
  tenant_id: string
  game_title: string
  game_type: GameType
  game_description: string
  game_version: string
  subject_area: SubjectArea
  target_duration_minutes: number
  difficulty_level: GameDifficulty
  grade_band: GradeBand

  // Game Content
  game_scenes: GameScene[]
  game_assets: GameAsset[]
  game_rules: GameRules
  game_config?: Record<string, any>

  // UI Configuration
  user_interface?: {
    theme: string
    layout: string
    controls: Record<string, any>
  }

  // Status and Metadata
  status: GameStatus
  estimated_duration_minutes: number
  expected_learning_outcomes: string[]
  created_at: string
  expires_at?: string
}

// Game Session Types
export interface GameSession {
  id: string
  game_manifest_id: string
  learner_id: string
  status: GameStatus
  progress_data: GameProgress
  performance_metrics: PerformanceMetrics
  completion_percentage: number
  expected_duration?: number
  actual_duration?: number
  started_at: string
  ended_at?: string
  paused_at?: string
  pause_duration_seconds?: number
}

export interface GameProgress {
  current_scene_id: string
  completed_scenes: string[]
  current_score: number
  interactions_completed: number
  hints_used: number
  mistakes_made: number
  time_spent_seconds: number
  checkpoints?: Record<string, any>
}

export interface PerformanceMetrics {
  accuracy_percentage: number
  speed_score: number
  consistency_score: number
  learning_efficiency: number
  engagement_level: number
  completion_rate: number
  retry_attempts: number
  help_requests: number
}

// Event Types
export interface GameEvent {
  event_type:
    | 'GAME_STARTED'
    | 'GAME_PAUSED'
    | 'GAME_RESUMED'
    | 'GAME_COMPLETED'
    | 'SCENE_COMPLETED'
    | 'INTERACTION_COMPLETED'
    | 'SCORE_UPDATED'
    | 'HINT_REQUESTED'
    | 'ERROR_OCCURRED'
  session_id: string
  learner_id: string
  game_id: string
  timestamp: string
  data?: Record<string, any>
}

// Game Generation Request
export interface GameGenerationRequest {
  learner_id: string
  duration_minutes: number
  game_type?: GameType
  subject_area?: SubjectArea
  difficulty?: GameDifficulty
  grade_band?: GradeBand
  learning_objectives?: string[]
  custom_requirements?: Record<string, any>
}

// API Response Types
export interface GameGenerationResponse {
  game_id: string
  manifest: GameManifest
  estimated_duration: number
  actual_generation_time: number
  status: GameStatus
  ai_generated: boolean
  fallback_used: boolean
  event_emitted: boolean
  created_at: string
}

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
  timestamp: string
}

// Game Client Implementation
class GameClient {
  private baseUrl: string
  private abortController: AbortController | null = null

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl
  }

  // Generate a new game
  async generateGame(
    request: GameGenerationRequest
  ): Promise<GameGenerationResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/games/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...request,
          minutes: request.duration_minutes, // API expects 'minutes' field
        }),
      })

      if (!response.ok) {
        throw new Error(`Game generation failed: ${response.statusText}`)
      }

      const result: ApiResponse<GameGenerationResponse> = await response.json()

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Game generation failed')
      }

      return result.data
    } catch (error) {
      console.error('Error generating game:', error)
      throw error
    }
  }

  // Get game manifest by ID
  async getGameManifest(gameId: string): Promise<GameManifest> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/v1/games/${gameId}/manifest`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch game manifest: ${response.statusText}`)
      }

      const result: ApiResponse<GameManifest> = await response.json()

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Failed to fetch game manifest')
      }

      return result.data
    } catch (error) {
      console.error('Error fetching game manifest:', error)
      throw error
    }
  }

  // Create a new game session
  async createGameSession(
    gameId: string,
    learnerId: string,
    expectedDuration?: number
  ): Promise<GameSession> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/v1/games/${gameId}/sessions`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            game_id: gameId,
            learner_id: learnerId,
            expected_duration: expectedDuration,
            session_context: {
              client_type: 'web',
              browser: navigator.userAgent,
              timestamp: new Date().toISOString(),
            },
          }),
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to create game session: ${response.statusText}`)
      }

      const result: ApiResponse<GameSession> = await response.json()

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Failed to create game session')
      }

      return result.data
    } catch (error) {
      console.error('Error creating game session:', error)
      throw error
    }
  }

  // Update game session progress
  async updateGameSession(
    sessionId: string,
    updates: Partial<GameSession>
  ): Promise<GameSession> {
    try {
      const response = await fetch(
        `${this.baseUrl}/api/v1/games/sessions/${sessionId}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updates),
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to update game session: ${response.statusText}`)
      }

      const result: ApiResponse<GameSession> = await response.json()

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Failed to update game session')
      }

      return result.data
    } catch (error) {
      console.error('Error updating game session:', error)
      throw error
    }
  }

  // Send game event
  async sendGameEvent(event: GameEvent): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/games/events`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(event),
      })

      if (!response.ok) {
        throw new Error(`Failed to send game event: ${response.statusText}`)
      }

      const result: ApiResponse = await response.json()

      if (!result.success) {
        throw new Error(result.error || 'Failed to send game event')
      }
    } catch (error) {
      console.error('Error sending game event:', error)
      // Don't throw - events are fire-and-forget
    }
  }

  // Complete game session
  async completeGame(
    sessionId: string,
    finalMetrics: PerformanceMetrics
  ): Promise<GameSession> {
    try {
      // Send completion event first
      await this.sendGameEvent({
        event_type: 'GAME_COMPLETED',
        session_id: sessionId,
        learner_id: '', // Will be filled by server
        game_id: '', // Will be filled by server
        timestamp: new Date().toISOString(),
        data: finalMetrics,
      })

      // Update session with final data
      const response = await fetch(
        `${this.baseUrl}/api/v1/games/sessions/${sessionId}/complete`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            performance_metrics: finalMetrics,
            completion_percentage: 100,
            ended_at: new Date().toISOString(),
          }),
        }
      )

      if (!response.ok) {
        throw new Error(`Failed to complete game: ${response.statusText}`)
      }

      const result: ApiResponse<GameSession> = await response.json()

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Failed to complete game')
      }

      return result.data
    } catch (error) {
      console.error('Error completing game:', error)
      throw error
    }
  }

  // Pause game session
  async pauseGame(sessionId: string): Promise<GameSession> {
    try {
      return await this.updateGameSession(sessionId, {
        status: 'in_progress',
        paused_at: new Date().toISOString(),
      })
    } catch (error) {
      console.error('Error pausing game:', error)
      throw error
    }
  }

  // Resume game session
  async resumeGame(
    sessionId: string,
    pauseDurationSeconds: number
  ): Promise<GameSession> {
    try {
      return await this.updateGameSession(sessionId, {
        status: 'in_progress',
        paused_at: undefined,
        pause_duration_seconds: pauseDurationSeconds,
      })
    } catch (error) {
      console.error('Error resuming game:', error)
      throw error
    }
  }

  // Cancel ongoing requests
  cancelRequests(): void {
    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }
  }
}

// Create singleton instance
export const gameClient = new GameClient()

// Export types and client
export default gameClient
