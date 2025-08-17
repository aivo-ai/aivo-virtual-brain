/**
 * S3-12 SLP Types and Client (TypeScript-only version)
 * Core types and API client without JSX dependencies
 */

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
  duration: number
  frequency: number
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
export class SLPGraphQLClient {
  private baseURL: string

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

  // TTS/ASR integration methods
  async synthesizeSpeech(_text: string, _config?: TTSConfig): Promise<string> {
    // Mock implementation
    const audioUrl = `data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmEaBC2OzvLSfC0EKXzI8NuRQgsTYbXa6z`
    return Promise.resolve(audioUrl)
  }

  async startASR(_config?: ASRConfig): Promise<MediaRecorder> {
    // Mock implementation
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mediaRecorder = new MediaRecorder(stream)

    mediaRecorder.start()
    return mediaRecorder
  }

  async stopASR(mediaRecorder: MediaRecorder): Promise<string> {
    return new Promise(resolve => {
      mediaRecorder.stop()
      mediaRecorder.ondataavailable = () => {
        resolve('Transcribed speech text')
      }
    })
  }
}

export const slpClient = new SLPGraphQLClient()

// API functions that can be used without React hooks
export async function getStudent(id: string): Promise<SLPStudent> {
  const result = await slpClient.getStudent(id)
  return result.student
}

export async function getProviderMatrix(): Promise<ProviderMatrix> {
  const result = await slpClient.getProviderMatrix()
  return result.providerMatrix
}

export async function createScreening(
  input: ScreeningCreateInput
): Promise<SLPScreening> {
  const result = await slpClient.createScreening(input)
  return result.createScreening.screening
}
