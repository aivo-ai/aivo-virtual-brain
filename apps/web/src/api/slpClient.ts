/**
 * S3-12 SLP GraphQL Client
 * Provides hooks and types for SLP operations with TTS/ASR integration
 */

import { useState, useCallback } from 'react'

// Base GraphQL configuration
const SLP_GRAPHQL_URL =
  (typeof window !== 'undefined' && (window as any).VITE_SLP_GRAPHQL_URL) ||
  'http://localhost:8006/graphql'

// TypeScript types based on GraphQL schema
export interface SLPStudent {
  id: string
  tenantId: string
  firstName: string
  lastName: string
  dateOfBirth: string
  gradeLevel: string
  parentConsent: ConsentStatus
  videoConsent: ConsentStatus
  audioConsent: ConsentStatus
  createdAt: string
  updatedAt: string
}

export interface SLPScreening {
  id: string
  studentId: string
  tenantId: string
  screeningType: ScreeningType
  status: ScreeningStatus
  responses: ScreeningResponse[]
  totalScore: number
  riskLevel: RiskLevel
  recommendations: string[]
  completedAt?: string
  createdBy: string
  createdAt: string
  updatedAt: string
}

export interface ScreeningResponse {
  questionId: string
  questionText: string
  responseType: ResponseType
  value: string | number | boolean
  score: number
  notes?: string
}

export interface SLPPlan {
  id: string
  studentId: string
  tenantId: string
  screeningId: string
  goals: TherapyGoal[]
  sessions: TherapySession[]
  duration: number // weeks
  frequency: number // sessions per week
  status: PlanStatus
  createdBy: string
  approvedBy?: string
  approvedAt?: string
  createdAt: string
  updatedAt: string
}

export interface TherapyGoal {
  id: string
  category: GoalCategory
  description: string
  targetBehavior: string
  measurableOutcome: string
  timeframe: string
  priority: Priority
  status: GoalStatus
}

export interface TherapySession {
  id: string
  planId: string
  sessionNumber: number
  scheduledDate: string
  status: SessionStatus
  exercises: Exercise[]
  notes?: string
  duration?: number
  completedAt?: string
  createdAt: string
  updatedAt: string
}

export interface Exercise {
  id: string
  type: ExerciseType
  title: string
  description: string
  instructions: string
  targetGoals: string[]
  ttsEnabled: boolean
  asrEnabled: boolean
  recordingRequired: boolean
  estimatedDuration: number
  materials: ExerciseMaterial[]
  prompts: ExercisePrompt[]
  status: ExerciseStatus
  attempts: ExerciseAttempt[]
}

export interface ExerciseMaterial {
  id: string
  type: MaterialType
  title: string
  description?: string
  url?: string
  content?: string
  metadata: Record<string, unknown>
}

export interface ExercisePrompt {
  id: string
  text: string
  audioUrl?: string
  order: number
  ttsEnabled: boolean
  expectedResponse?: string
  scoringCriteria?: string[]
}

export interface ExerciseAttempt {
  id: string
  exerciseId: string
  sessionId: string
  studentResponse?: string
  audioRecordingUrl?: string
  score?: number
  feedback?: string
  completedAt: string
  metadata: Record<string, unknown>
}

export interface ConsentStatus {
  granted: boolean
  grantedAt?: string
  grantedBy?: string
  expiresAt?: string
  restrictions?: string[]
}

export interface TTSConfig {
  enabled: boolean
  voice: string
  rate: number
  pitch: number
  volume: number
}

export interface ASRConfig {
  enabled: boolean
  language: string
  sensitivity: number
  timeout: number
}

export interface ProviderMatrix {
  tts: TTSProvider
  asr: ASRProvider
  recording: RecordingProvider
}

export interface TTSProvider {
  name: string
  enabled: boolean
  config: TTSConfig
}

export interface ASRProvider {
  name: string
  enabled: boolean
  config: ASRConfig
}

export interface RecordingProvider {
  name: string
  enabled: boolean
  maxDuration: number
  format: string
}

// Enums
export enum ScreeningType {
  ARTICULATION = 'ARTICULATION',
  LANGUAGE = 'LANGUAGE',
  FLUENCY = 'FLUENCY',
  VOICE = 'VOICE',
  COMPREHENSIVE = 'COMPREHENSIVE',
}

export enum ScreeningStatus {
  DRAFT = 'DRAFT',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
  REVIEWED = 'REVIEWED',
}

export enum RiskLevel {
  LOW = 'LOW',
  MODERATE = 'MODERATE',
  HIGH = 'HIGH',
  SEVERE = 'SEVERE',
}

export enum ResponseType {
  BOOLEAN = 'BOOLEAN',
  SCALE = 'SCALE',
  TEXT = 'TEXT',
  MULTIPLE_CHOICE = 'MULTIPLE_CHOICE',
}

export enum PlanStatus {
  DRAFT = 'DRAFT',
  PENDING_APPROVAL = 'PENDING_APPROVAL',
  APPROVED = 'APPROVED',
  ACTIVE = 'ACTIVE',
  COMPLETED = 'COMPLETED',
  DISCONTINUED = 'DISCONTINUED',
}

export enum GoalCategory {
  ARTICULATION = 'ARTICULATION',
  LANGUAGE_EXPRESSION = 'LANGUAGE_EXPRESSION',
  LANGUAGE_COMPREHENSION = 'LANGUAGE_COMPREHENSION',
  FLUENCY = 'FLUENCY',
  VOICE = 'VOICE',
  SOCIAL_COMMUNICATION = 'SOCIAL_COMMUNICATION',
}

export enum Priority {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

export enum GoalStatus {
  NOT_STARTED = 'NOT_STARTED',
  IN_PROGRESS = 'IN_PROGRESS',
  ACHIEVED = 'ACHIEVED',
  DISCONTINUED = 'DISCONTINUED',
}

export enum SessionStatus {
  SCHEDULED = 'SCHEDULED',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
  CANCELLED = 'CANCELLED',
  NO_SHOW = 'NO_SHOW',
}

export enum ExerciseType {
  ARTICULATION_DRILL = 'ARTICULATION_DRILL',
  VOCABULARY_BUILDING = 'VOCABULARY_BUILDING',
  SENTENCE_COMPLETION = 'SENTENCE_COMPLETION',
  STORY_RETELLING = 'STORY_RETELLING',
  CONVERSATION_PRACTICE = 'CONVERSATION_PRACTICE',
  BREATHING_EXERCISE = 'BREATHING_EXERCISE',
  VOICE_MODULATION = 'VOICE_MODULATION',
}

export enum ExerciseStatus {
  NOT_STARTED = 'NOT_STARTED',
  IN_PROGRESS = 'IN_PROGRESS',
  COMPLETED = 'COMPLETED',
  SKIPPED = 'SKIPPED',
}

export enum MaterialType {
  IMAGE = 'IMAGE',
  AUDIO = 'AUDIO',
  VIDEO = 'VIDEO',
  TEXT = 'TEXT',
  INTERACTIVE = 'INTERACTIVE',
}

// GraphQL operation types
export interface ScreeningCreateInput {
  studentId: string
  tenantId: string
  screeningType: ScreeningType
}

export interface ScreeningUpdateInput {
  responses: ScreeningResponse[]
  status?: ScreeningStatus
}

export interface PlanCreateInput {
  studentId: string
  tenantId: string
  screeningId: string
  goals: Omit<TherapyGoal, 'id' | 'status'>[]
  duration: number
  frequency: number
}

export interface SessionCreateInput {
  planId: string
  scheduledDate: string
  exercises: Omit<Exercise, 'id' | 'status' | 'attempts'>[]
}

export interface ExerciseAttemptInput {
  exerciseId: string
  sessionId: string
  studentResponse?: string
  audioRecordingUrl?: string
  metadata?: Record<string, unknown>
}

export interface SLPUpdateEvent {
  type:
    | 'SCREENING_UPDATED'
    | 'PLAN_UPDATED'
    | 'SESSION_UPDATED'
    | 'EXERCISE_COMPLETED'
  studentId: string
  entityId: string
  timestamp: string
  metadata?: Record<string, unknown>
}

// GraphQL client class
class SLPGraphQLClient {
  private baseURL: string
  private subscriptions: Map<string, WebSocket> = new Map()

  constructor() {
    this.baseURL = SLP_GRAPHQL_URL
  }

  private async request<T>(
    query: string,
    variables?: Record<string, unknown>
  ): Promise<T> {
    const response = await fetch(this.baseURL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('authToken') || ''}`,
      },
      body: JSON.stringify({ query, variables }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const result = await response.json()
    if (result.errors) {
      throw new Error(
        `GraphQL errors: ${result.errors.map((e: { message: string }) => e.message).join(', ')}`
      )
    }

    return result.data
  }

  async getStudent(id: string): Promise<{ student: SLPStudent }> {
    const query = `
      query GetStudent($id: String!) {
        student(id: $id) {
          id
          tenantId
          firstName
          lastName
          dateOfBirth
          gradeLevel
          parentConsent {
            granted
            grantedAt
            grantedBy
            expiresAt
            restrictions
          }
          videoConsent {
            granted
            grantedAt
            grantedBy
            expiresAt
            restrictions
          }
          audioConsent {
            granted
            grantedAt
            grantedBy
            expiresAt
            restrictions
          }
          createdAt
          updatedAt
        }
      }
    `
    return this.request(query, { id })
  }

  async createScreening(input: ScreeningCreateInput): Promise<{
    createScreening: { screening: SLPScreening; success: boolean }
  }> {
    const query = `
      mutation CreateScreening($input: ScreeningCreateInput!) {
        createScreening(input: $input) {
          screening {
            id
            studentId
            tenantId
            screeningType
            status
            responses {
              questionId
              questionText
              responseType
              value
              score
              notes
            }
            totalScore
            riskLevel
            recommendations
            completedAt
            createdBy
            createdAt
            updatedAt
          }
          success
        }
      }
    `
    return this.request(query, { input })
  }

  async updateScreening(
    id: string,
    input: ScreeningUpdateInput
  ): Promise<{
    updateScreening: { screening: SLPScreening; success: boolean }
  }> {
    const query = `
      mutation UpdateScreening($id: String!, $input: ScreeningUpdateInput!) {
        updateScreening(id: $id, input: $input) {
          screening {
            id
            studentId
            tenantId
            screeningType
            status
            responses {
              questionId
              questionText
              responseType
              value
              score
              notes
            }
            totalScore
            riskLevel
            recommendations
            completedAt
            createdBy
            createdAt
            updatedAt
          }
          success
        }
      }
    `
    return this.request(query, { id, input })
  }

  async createPlan(
    input: PlanCreateInput
  ): Promise<{ createPlan: { plan: SLPPlan; success: boolean } }> {
    const query = `
      mutation CreatePlan($input: PlanCreateInput!) {
        createPlan(input: $input) {
          plan {
            id
            studentId
            tenantId
            screeningId
            goals {
              id
              category
              description
              targetBehavior
              measurableOutcome
              timeframe
              priority
              status
            }
            sessions {
              id
              planId
              sessionNumber
              scheduledDate
              status
              exercises {
                id
                type
                title
                description
                instructions
                targetGoals
                ttsEnabled
                asrEnabled
                recordingRequired
                estimatedDuration
                status
              }
              notes
              duration
              completedAt
              createdAt
              updatedAt
            }
            duration
            frequency
            status
            createdBy
            approvedBy
            approvedAt
            createdAt
            updatedAt
          }
          success
        }
      }
    `
    return this.request(query, { input })
  }

  async submitExerciseAttempt(input: ExerciseAttemptInput): Promise<{
    submitExerciseAttempt: { attempt: ExerciseAttempt; success: boolean }
  }> {
    const query = `
      mutation SubmitExerciseAttempt($input: ExerciseAttemptInput!) {
        submitExerciseAttempt(input: $input) {
          attempt {
            id
            exerciseId
            sessionId
            studentResponse
            audioRecordingUrl
            score
            feedback
            completedAt
            metadata
          }
          success
        }
      }
    `
    return this.request(query, { input })
  }

  async getProviderMatrix(): Promise<{ providerMatrix: ProviderMatrix }> {
    const query = `
      query GetProviderMatrix {
        providerMatrix {
          tts {
            name
            enabled
            config {
              enabled
              voice
              rate
              pitch
              volume
            }
          }
          asr {
            name
            enabled
            config {
              enabled
              language
              sensitivity
              timeout
            }
          }
          recording {
            name
            enabled
            maxDuration
            format
          }
        }
      }
    `
    return this.request(query)
  }

  subscribeToSLPUpdates(
    studentId: string,
    onUpdate: (event: SLPUpdateEvent) => void
  ): () => void {
    const wsUrl = this.baseURL
      .replace('http', 'ws')
      .replace('/graphql', '/graphql-ws')
    const ws = new WebSocket(wsUrl, 'graphql-ws')

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          type: 'connection_init',
          payload: {
            Authorization: `Bearer ${localStorage.getItem('authToken') || ''}`,
          },
        })
      )
    }

    ws.onmessage = event => {
      const message = JSON.parse(event.data)
      if (message.type === 'data' && message.payload?.data?.slpUpdated) {
        onUpdate(message.payload.data.slpUpdated)
      }
    }

    this.subscriptions.set(studentId, ws)

    // Send subscription
    setTimeout(() => {
      ws.send(
        JSON.stringify({
          id: studentId,
          type: 'start',
          payload: {
            query: `
            subscription SLPUpdated($studentId: String!) {
              slpUpdated(studentId: $studentId) {
                type
                studentId
                entityId
                timestamp
                metadata
              }
            }
          `,
            variables: { studentId },
          },
        })
      )
    }, 1000)

    // Return cleanup function
    return () => {
      ws.close()
      this.subscriptions.delete(studentId)
    }
  }

  // TTS/ASR integration methods
  async synthesizeSpeech(_text: string, _config?: TTSConfig): Promise<string> {
    // Mock implementation - would integrate with actual TTS provider
    const audioUrl = `data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmEaBC2OzvLSfC0EKXzI8NuRQgsTYbXa6z`
    return Promise.resolve(audioUrl)
  }

  async startASR(_config?: ASRConfig): Promise<MediaRecorder> {
    // Mock implementation - would integrate with actual ASR provider
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mediaRecorder = new MediaRecorder(stream)

    mediaRecorder.start()
    return mediaRecorder
  }

  async stopASR(mediaRecorder: MediaRecorder): Promise<string> {
    return new Promise(resolve => {
      mediaRecorder.stop()
      mediaRecorder.ondataavailable = () => {
        // Mock transcription result
        resolve('Transcribed speech text')
      }
    })
  }
}

export const slpClient = new SLPGraphQLClient()

// React hooks
export function useSLPQueries() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const getStudent = useCallback(async (id: string) => {
    try {
      setLoading(true)
      setError(null)
      const result = await slpClient.getStudent(id)
      return result.student
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch student'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  const getProviderMatrix = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await slpClient.getProviderMatrix()
      return result.providerMatrix
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to fetch provider matrix'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    getStudent,
    getProviderMatrix,
    loading,
    error,
  }
}

export function useSLPMutations() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createScreening = useCallback(async (input: ScreeningCreateInput) => {
    try {
      setLoading(true)
      setError(null)
      const result = await slpClient.createScreening(input)
      return result.createScreening
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to create screening'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  const updateScreening = useCallback(
    async (id: string, input: ScreeningUpdateInput) => {
      try {
        setLoading(true)
        setError(null)
        const result = await slpClient.updateScreening(id, input)
        return result.updateScreening
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to update screening'
        setError(errorMessage)
        throw new Error(errorMessage)
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const createPlan = useCallback(async (input: PlanCreateInput) => {
    try {
      setLoading(true)
      setError(null)
      const result = await slpClient.createPlan(input)
      return result.createPlan
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to create plan'
      setError(errorMessage)
      throw new Error(errorMessage)
    } finally {
      setLoading(false)
    }
  }, [])

  const submitExerciseAttempt = useCallback(
    async (input: ExerciseAttemptInput) => {
      try {
        setLoading(true)
        setError(null)
        const result = await slpClient.submitExerciseAttempt(input)

        // Emit SLP_UPDATED event on session submit
        window.dispatchEvent(
          new CustomEvent('SLP_UPDATED', {
            detail: {
              type: 'EXERCISE_COMPLETED',
              studentId: input.sessionId, // In real app, would extract from session
              entityId: input.exerciseId,
              timestamp: new Date().toISOString(),
              metadata: input.metadata,
            },
          })
        )

        return result.submitExerciseAttempt
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : 'Failed to submit exercise attempt'
        setError(errorMessage)
        throw new Error(errorMessage)
      } finally {
        setLoading(false)
      }
    },
    []
  )

  return {
    createScreening,
    updateScreening,
    createPlan,
    submitExerciseAttempt,
    loading,
    error,
  }
}

// TTS/ASR hooks
export function useTTS() {
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const speak = useCallback(async (text: string, config?: TTSConfig) => {
    try {
      setIsPlaying(true)
      setError(null)

      const audioUrl = await slpClient.synthesizeSpeech(text, config)
      const audio = new Audio(audioUrl)

      audio.onended = () => setIsPlaying(false)
      audio.onerror = () => {
        setError('Failed to play audio')
        setIsPlaying(false)
      }

      await audio.play()
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to synthesize speech'
      setError(errorMessage)
      setIsPlaying(false)
    }
  }, [])

  return {
    speak,
    isPlaying,
    error,
  }
}

export function useASR() {
  const [isRecording, setIsRecording] = useState(false)
  const [transcript, setTranscript] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)

  const startRecording = useCallback(async (config?: ASRConfig) => {
    try {
      setIsRecording(true)
      setError(null)
      setTranscript('')

      const recorder = await slpClient.startASR(config)
      setMediaRecorder(recorder)
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to start recording'
      setError(errorMessage)
      setIsRecording(false)
    }
  }, [])

  const stopRecording = useCallback(async () => {
    if (!mediaRecorder) return ''

    try {
      const result = await slpClient.stopASR(mediaRecorder)
      setTranscript(result)
      setIsRecording(false)
      setMediaRecorder(null)
      return result
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to stop recording'
      setError(errorMessage)
      setIsRecording(false)
      return ''
    }
  }, [mediaRecorder])

  return {
    startRecording,
    stopRecording,
    isRecording,
    transcript,
    error,
  }
}
