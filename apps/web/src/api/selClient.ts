/**
 * S3-13 SEL Client
 * Social-Emotional Learning API client with GraphQL integration
 */

import { gql } from 'graphql-request'
import { GraphQLClient } from 'graphql-request'
import { useState, useCallback } from 'react'

// SEL Types
export interface SELStudent {
  id: string
  tenantId: string
  firstName: string
  lastName: string
  gradeLevel: string
  dateOfBirth: string
  selConsent: ConsentRecord
  parentConsent: ConsentRecord
  createdAt: string
  updatedAt: string
}

export interface ConsentRecord {
  granted: boolean
  grantedAt?: string
  grantedBy?: string
  expiresAt?: string
  restrictions: string[]
}

export interface MoodCheckIn {
  id: string
  studentId: string
  tenantId: string
  timestamp: string
  moodLevel: number // 1-10 scale
  energyLevel: number // 1-10 scale
  stressLevel: number // 1-10 scale
  socialConnectedness: number // 1-10 scale
  academicConfidence: number // 1-10 scale
  notes?: string
  tags: string[]
  location?: string
  gradeBandVisuals: GradeBandVisuals
  createdAt: string
  updatedAt: string
}

export interface GradeBandVisuals {
  theme: 'elementary' | 'middle' | 'high'
  colors: string[]
  iconSet: string
  language: string
}

export interface SELStrategy {
  id: string
  title: string
  description: string
  category: StrategyCategory
  gradeBands: string[]
  instructions: string[]
  estimatedDuration: number // minutes
  tags: string[]
  effectiveness: number // 1-5 rating
  timesUsed: number
  lastUsed?: string
  isRecommended: boolean
  iconUrl?: string
  videoUrl?: string
  audioUrl?: string
  createdAt: string
  updatedAt: string
}

export enum StrategyCategory {
  MINDFULNESS = 'MINDFULNESS',
  BREATHING = 'BREATHING',
  MOVEMENT = 'MOVEMENT',
  COGNITIVE = 'COGNITIVE',
  SOCIAL = 'SOCIAL',
  CREATIVE = 'CREATIVE',
}

export interface SELAlert {
  id: string
  studentId: string
  tenantId: string
  alertType: AlertType
  severity: AlertSeverity
  message: string
  threshold: AlertThreshold
  triggeredBy: string // checkInId
  acknowledged: boolean
  acknowledgedBy?: string
  acknowledgedAt?: string
  resolvedAt?: string
  metadata: Record<string, any>
  createdAt: string
  updatedAt: string
}

export enum AlertType {
  MOOD_LOW = 'MOOD_LOW',
  STRESS_HIGH = 'STRESS_HIGH',
  SOCIAL_ISOLATION = 'SOCIAL_ISOLATION',
  ACADEMIC_STRUGGLE = 'ACADEMIC_STRUGGLE',
  ENERGY_CRASH = 'ENERGY_CRASH',
  PATTERN_CONCERNING = 'PATTERN_CONCERNING',
}

export enum AlertSeverity {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

export interface AlertThreshold {
  metric: string
  operator: 'lt' | 'gt' | 'eq' | 'pattern'
  value: number
  timeWindow?: number // days
  consecutiveCount?: number
}

export interface SELUpdateEvent {
  type:
    | 'CHECKIN_CREATED'
    | 'STRATEGY_USED'
    | 'ALERT_TRIGGERED'
    | 'ALERT_RESOLVED'
  studentId: string
  entityId: string
  timestamp: string
  metadata?: Record<string, any>
}

// Localized copy interface
export interface SELCopy {
  [key: string]: {
    [locale: string]: string
  }
}

// GraphQL Queries
const GET_STUDENT = gql`
  query GetSELStudent($studentId: ID!) {
    selStudent(id: $studentId) {
      id
      tenantId
      firstName
      lastName
      gradeLevel
      dateOfBirth
      selConsent {
        granted
        grantedAt
        grantedBy
        expiresAt
        restrictions
      }
      parentConsent {
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

const GET_RECENT_CHECKINS = gql`
  query GetRecentCheckIns($studentId: ID!, $limit: Int = 10) {
    recentCheckIns(studentId: $studentId, limit: $limit) {
      id
      studentId
      tenantId
      timestamp
      moodLevel
      energyLevel
      stressLevel
      socialConnectedness
      academicConfidence
      notes
      tags
      location
      gradeBandVisuals {
        theme
        colors
        iconSet
        language
      }
      createdAt
      updatedAt
    }
  }
`

const GET_STRATEGIES = gql`
  query GetSELStrategies($gradeLevel: String!, $category: StrategyCategory) {
    selStrategies(gradeLevel: $gradeLevel, category: $category) {
      id
      title
      description
      category
      gradeBands
      instructions
      estimatedDuration
      tags
      effectiveness
      timesUsed
      lastUsed
      isRecommended
      iconUrl
      videoUrl
      audioUrl
      createdAt
      updatedAt
    }
  }
`

const GET_ACTIVE_ALERTS = gql`
  query GetActiveAlerts($studentId: ID!) {
    activeAlerts(studentId: $studentId) {
      id
      studentId
      tenantId
      alertType
      severity
      message
      threshold {
        metric
        operator
        value
        timeWindow
        consecutiveCount
      }
      triggeredBy
      acknowledged
      acknowledgedBy
      acknowledgedAt
      resolvedAt
      metadata
      createdAt
      updatedAt
    }
  }
`

// GraphQL Mutations
const CREATE_CHECKIN = gql`
  mutation CreateCheckIn($input: CheckInInput!) {
    createCheckIn(input: $input) {
      checkIn {
        id
        studentId
        tenantId
        timestamp
        moodLevel
        energyLevel
        stressLevel
        socialConnectedness
        academicConfidence
        notes
        tags
        location
        gradeBandVisuals {
          theme
          colors
          iconSet
          language
        }
        createdAt
        updatedAt
      }
      alerts {
        id
        alertType
        severity
        message
      }
      success
    }
  }
`

const USE_STRATEGY = gql`
  mutation UseStrategy($strategyId: ID!, $studentId: ID!, $effectiveness: Int) {
    useStrategy(
      strategyId: $strategyId
      studentId: $studentId
      effectiveness: $effectiveness
    ) {
      strategy {
        id
        timesUsed
        lastUsed
        effectiveness
      }
      success
    }
  }
`

const ACKNOWLEDGE_ALERT = gql`
  mutation AcknowledgeAlert($alertId: ID!, $acknowledgedBy: String!) {
    acknowledgeAlert(alertId: $alertId, acknowledgedBy: $acknowledgedBy) {
      alert {
        id
        acknowledged
        acknowledgedBy
        acknowledgedAt
      }
      success
    }
  }
`

const RESOLVE_ALERT = gql`
  mutation ResolveAlert($alertId: ID!, $resolvedBy: String!) {
    resolveAlert(alertId: $alertId, resolvedBy: $resolvedBy) {
      alert {
        id
        resolvedAt
      }
      success
    }
  }
`

// Client Configuration
const client = new GraphQLClient('/api/graphql', {
  headers: {
    'Content-Type': 'application/json',
  },
})

// Custom Hooks
export function useSELQueries() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const getStudent = useCallback(
    async (studentId: string): Promise<SELStudent> => {
      setLoading(true)
      setError(null)
      try {
        const data = (await client.request(GET_STUDENT, { studentId })) as {
          selStudent: SELStudent
        }
        return data.selStudent
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to fetch student'
        setError(errorMessage)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const getRecentCheckIns = useCallback(
    async (studentId: string, limit = 10): Promise<MoodCheckIn[]> => {
      setLoading(true)
      setError(null)
      try {
        const data = (await client.request(GET_RECENT_CHECKINS, {
          studentId,
          limit,
        })) as { recentCheckIns: MoodCheckIn[] }
        return data.recentCheckIns
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to fetch check-ins'
        setError(errorMessage)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const getStrategies = useCallback(
    async (
      gradeLevel: string,
      category?: StrategyCategory
    ): Promise<SELStrategy[]> => {
      setLoading(true)
      setError(null)
      try {
        const data = (await client.request(GET_STRATEGIES, {
          gradeLevel,
          category,
        })) as { selStrategies: SELStrategy[] }
        return data.selStrategies
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to fetch strategies'
        setError(errorMessage)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const getActiveAlerts = useCallback(
    async (studentId: string): Promise<SELAlert[]> => {
      setLoading(true)
      setError(null)
      try {
        const data = (await client.request(GET_ACTIVE_ALERTS, {
          studentId,
        })) as { activeAlerts: SELAlert[] }
        return data.activeAlerts
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to fetch alerts'
        setError(errorMessage)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  return {
    getStudent,
    getRecentCheckIns,
    getStrategies,
    getActiveAlerts,
    loading,
    error,
  }
}

export function useSELMutations() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const createCheckIn = useCallback(
    async (input: {
      studentId: string
      mood: string
      energy: number
      stress: number
      tags: string[]
      notes?: string
    }) => {
      setLoading(true)
      setError(null)
      try {
        const data = (await client.request(CREATE_CHECKIN, { input })) as {
          createCheckIn: MoodCheckIn & { alerts?: SELAlert[] }
        }

        // Emit SEL_ALERT events for any alerts triggered
        if (data.createCheckIn.alerts && data.createCheckIn.alerts.length > 0) {
          data.createCheckIn.alerts.forEach((alert: SELAlert) => {
            const selAlertEvent = new CustomEvent('SEL_ALERT', {
              detail: {
                type: 'ALERT_TRIGGERED',
                alert,
                studentId: input.studentId,
                timestamp: new Date().toISOString(),
              },
            })
            window.dispatchEvent(selAlertEvent)
          })
        }

        return data.createCheckIn
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to create check-in'
        setError(errorMessage)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const useStrategy = useCallback(
    async (strategyId: string, studentId: string, effectiveness?: number) => {
      setLoading(true)
      setError(null)
      try {
        const data = (await client.request(USE_STRATEGY, {
          strategyId,
          studentId,
          effectiveness,
        })) as {
          useStrategy: {
            id: string
            strategyId: string
            effectiveness?: number
            createdAt: string
          }
        }
        return data.useStrategy
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to use strategy'
        setError(errorMessage)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const acknowledgeAlert = useCallback(
    async (alertId: string, acknowledgedBy: string) => {
      setLoading(true)
      setError(null)
      try {
        const data = (await client.request(ACKNOWLEDGE_ALERT, {
          alertId,
          acknowledgedBy,
        })) as {
          acknowledgeAlert: SELAlert
        }
        return data.acknowledgeAlert
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to acknowledge alert'
        setError(errorMessage)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  const resolveAlert = useCallback(
    async (alertId: string, resolvedBy: string) => {
      setLoading(true)
      setError(null)
      try {
        const data = (await client.request(RESOLVE_ALERT, {
          alertId,
          resolvedBy,
        })) as {
          resolveAlert: SELAlert
        }
        return data.resolveAlert
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to resolve alert'
        setError(errorMessage)
        throw err
      } finally {
        setLoading(false)
      }
    },
    []
  )

  return {
    createCheckIn,
    useStrategy,
    acknowledgeAlert,
    resolveAlert,
    loading,
    error,
  }
}

// Utility Functions
export const getGradeBandVisuals = (gradeLevel: string): GradeBandVisuals => {
  const grade = parseInt(gradeLevel.replace(/\D/g, ''), 10)

  if (grade <= 5) {
    return {
      theme: 'elementary',
      colors: ['#FFB5BA', '#FFE5AD', '#B5E8B5', '#A8D8FF', '#E8B5FF'],
      iconSet: 'playful',
      language: 'simple',
    }
  } else if (grade <= 8) {
    return {
      theme: 'middle',
      colors: ['#FF8A95', '#FFDD6B', '#8FE58F', '#7BC8FF', '#D68FFF'],
      iconSet: 'modern',
      language: 'moderate',
    }
  } else {
    return {
      theme: 'high',
      colors: ['#FF6B75', '#FFC93C', '#6BDA6B', '#4CB5FF', '#C46BFF'],
      iconSet: 'sophisticated',
      language: 'mature',
    }
  }
}

export const getLocalizedCopy = (key: string, locale = 'en'): string => {
  const copy: SELCopy = {
    'mood.question': {
      en: 'How are you feeling today?',
      es: '¿Cómo te sientes hoy?',
      fr: "Comment vous sentez-vous aujourd'hui?",
    },
    'energy.question': {
      en: "What's your energy level?",
      es: '¿Cuál es tu nivel de energía?',
      fr: "Quel est votre niveau d'énergie?",
    },
    'stress.question': {
      en: 'How stressed do you feel?',
      es: '¿Qué tan estresado te sientes?',
      fr: 'À quel point vous sentez-vous stressé?',
    },
    'social.question': {
      en: 'How connected do you feel to others?',
      es: '¿Qué tan conectado te sientes con otros?',
      fr: 'À quel point vous sentez-vous connecté aux autres?',
    },
    'academic.question': {
      en: 'How confident do you feel about your schoolwork?',
      es: '¿Qué tan seguro te sientes sobre tu trabajo escolar?',
      fr: 'À quel point vous sentez-vous confiant dans votre travail scolaire?',
    },
    'checkin.submit': {
      en: 'Submit Check-in',
      es: 'Enviar Check-in',
      fr: 'Soumettre le Check-in',
    },
    'strategies.title': {
      en: 'Helpful Strategies',
      es: 'Estrategias Útiles',
      fr: 'Stratégies Utiles',
    },
    'alert.mood.low': {
      en: 'Low mood detected - consider trying a mood-boosting strategy',
      es: 'Estado de ánimo bajo detectado - considera probar una estrategia para mejorar el ánimo',
      fr: "Humeur basse détectée - essayez une stratégie pour améliorer l'humeur",
    },
    'alert.stress.high': {
      en: 'High stress levels detected - breathing exercises might help',
      es: 'Niveles altos de estrés detectados - los ejercicios de respiración podrían ayudar',
      fr: 'Niveaux de stress élevés détectés - les exercices de respiration pourraient aider',
    },
    'consent.required': {
      en: 'SEL features require consent to be enabled',
      es: 'Las funciones SEL requieren consentimiento para ser habilitadas',
      fr: 'Les fonctionnalités SEL nécessitent un consentement pour être activées',
    },
  }

  return copy[key]?.[locale] || copy[key]?.['en'] || key
}

// SEL Update Subscription
export const subscribeToSELUpdates = (
  studentId: string,
  callback: (event: SELUpdateEvent) => void
): (() => void) => {
  const handleUpdate = (event: CustomEvent<SELUpdateEvent>) => {
    if (event.detail.studentId === studentId) {
      callback(event.detail)
    }
  }

  window.addEventListener(
    'SEL_UPDATE',
    handleUpdate as unknown as EventListener
  )

  return () => {
    window.removeEventListener(
      'SEL_UPDATE',
      handleUpdate as unknown as EventListener
    )
  }
}

// Default export
const selClient = {
  getStudent: (studentId: string) => client.request(GET_STUDENT, { studentId }),
  getRecentCheckIns: (studentId: string, limit = 10) =>
    client.request(GET_RECENT_CHECKINS, { studentId, limit }),
  getStrategies: (gradeLevel: string, category?: StrategyCategory) =>
    client.request(GET_STRATEGIES, { gradeLevel, category }),
  getActiveAlerts: (studentId: string) =>
    client.request(GET_ACTIVE_ALERTS, { studentId }),
  createCheckIn: (input: {
    studentId: string
    mood: string
    energy: number
    stress: number
    tags: string[]
    notes?: string
  }) => client.request(CREATE_CHECKIN, { input }),
  useStrategy: (
    strategyId: string,
    studentId: string,
    effectiveness?: number
  ) => client.request(USE_STRATEGY, { strategyId, studentId, effectiveness }),
  acknowledgeAlert: (alertId: string, acknowledgedBy: string) =>
    client.request(ACKNOWLEDGE_ALERT, { alertId, acknowledgedBy }),
  resolveAlert: (alertId: string, resolvedBy: string) =>
    client.request(RESOLVE_ALERT, { alertId, resolvedBy }),
  subscribeToSELUpdates,
}

export default selClient
