/**
 * S3-12 SLP Flow Component
 * Main orchestrator for SLP screening, planning, and sessions
 */

import { useState, useEffect } from 'react'
import { Button } from '../ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Alert, AlertDescription } from '../ui/Alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/Tabs'
import { User, ClipboardList, Target, Play, AlertTriangle } from '../ui/Icons'
import {
  type SLPStudent,
  type SLPScreening,
  type SLPPlan,
  type TherapySession,
  type ProviderMatrix,
  type SLPUpdateEvent,
  ScreeningType,
  ScreeningStatus,
  PlanStatus,
  SessionStatus,
  useSLPQueries,
  slpClient,
} from '@/api/slpClient'
import { ScreeningForm } from './ScreeningForm'
import { TherapyPlan } from './TherapyPlan'
import { ExerciseSession } from './ExerciseSession'

interface SLPFlowProps {
  studentId: string
  tenantId: string
  onExit: () => void
}

type FlowStep = 'overview' | 'screening' | 'plan' | 'session'

interface FlowState {
  currentStep: FlowStep
  student: SLPStudent | null
  screening: SLPScreening | null
  plan: SLPPlan | null
  currentSession: TherapySession | null
  providerMatrix: ProviderMatrix | null
  completedSessions: TherapySession[]
}

export function SLPFlow({ studentId, tenantId, onExit }: SLPFlowProps) {
  const [flowState, setFlowState] = useState<FlowState>({
    currentStep: 'overview',
    student: null,
    screening: null,
    plan: null,
    currentSession: null,
    providerMatrix: null,
    completedSessions: [],
  })
  const [selectedScreeningType, setSelectedScreeningType] =
    useState<ScreeningType>(ScreeningType.COMPREHENSIVE)
  const [subscriptionCleanup, setSubscriptionCleanup] = useState<
    (() => void) | null
  >(null)

  const { getStudent, getProviderMatrix, loading, error } = useSLPQueries()

  useEffect(() => {
    loadInitialData()

    // Set up SLP update subscription
    const cleanup = slpClient.subscribeToSLPUpdates(studentId, handleSLPUpdate)
    setSubscriptionCleanup(() => cleanup)

    return () => {
      if (subscriptionCleanup) {
        subscriptionCleanup()
      }
    }
  }, [studentId])

  const loadInitialData = async () => {
    try {
      const [studentData, matrixData] = await Promise.all([
        getStudent(studentId),
        getProviderMatrix(),
      ])

      setFlowState(prev => ({
        ...prev,
        student: studentData,
        providerMatrix: matrixData,
      }))
    } catch (err) {
      console.error('Failed to load SLP data:', err)
    }
  }

  const handleSLPUpdate = (event: SLPUpdateEvent) => {
    console.log('SLP Update received:', event)

    // Handle real-time updates based on event type
    switch (event.type) {
      case 'SCREENING_UPDATED':
        // Refresh screening data
        loadInitialData()
        break
      case 'PLAN_UPDATED':
        // Refresh plan data
        loadInitialData()
        break
      case 'SESSION_UPDATED':
        // Refresh session data
        loadInitialData()
        break
      case 'EXERCISE_COMPLETED':
        // Update session progress
        loadInitialData()
        break
    }
  }

  const handleScreeningComplete = (screening: SLPScreening) => {
    setFlowState(prev => ({
      ...prev,
      screening,
      currentStep: 'plan',
    }))
  }

  const handlePlanCreated = (plan: SLPPlan) => {
    setFlowState(prev => ({
      ...prev,
      plan,
      currentStep: 'overview',
    }))
  }

  const handleStartSession = (session: TherapySession) => {
    setFlowState(prev => ({
      ...prev,
      currentSession: session,
      currentStep: 'session',
    }))
  }

  const handleSessionComplete = (session: TherapySession) => {
    setFlowState(prev => ({
      ...prev,
      currentSession: null,
      completedSessions: [...prev.completedSessions, session],
      currentStep: 'overview',
    }))
  }

  const handleStartScreening = (type: ScreeningType) => {
    setSelectedScreeningType(type)
    setFlowState(prev => ({
      ...prev,
      currentStep: 'screening',
    }))
  }

  const renderOverview = () => {
    const { student, screening, plan, completedSessions } = flowState

    if (!student) return null

    return (
      <div className="space-y-6">
        {/* Student Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="w-5 h-5" />
              Student Information
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">Name</div>
                <div className="font-medium">
                  {student.firstName} {student.lastName}
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Grade Level</div>
                <div className="font-medium">{student.gradeLevel}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">
                  Date of Birth
                </div>
                <div className="font-medium">
                  {new Date(student.dateOfBirth).toLocaleDateString()}
                </div>
              </div>
            </div>

            {/* Consent Status */}
            <div className="mt-4 pt-4 border-t">
              <div className="text-sm text-muted-foreground mb-2">
                Consent Status
              </div>
              <div className="flex gap-2">
                <Badge
                  variant={
                    student.audioConsent.granted ? 'default' : 'destructive'
                  }
                >
                  Audio:{' '}
                  {student.audioConsent.granted ? 'Granted' : 'Not Granted'}
                </Badge>
                <Badge
                  variant={
                    student.videoConsent.granted ? 'default' : 'destructive'
                  }
                >
                  Video:{' '}
                  {student.videoConsent.granted ? 'Granted' : 'Not Granted'}
                </Badge>
                <Badge
                  variant={
                    student.parentConsent.granted ? 'default' : 'destructive'
                  }
                >
                  Parent:{' '}
                  {student.parentConsent.granted ? 'Granted' : 'Not Granted'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Flow Progress */}
        <Tabs defaultValue="progress" className="space-y-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="progress">Progress</TabsTrigger>
            <TabsTrigger value="actions">Actions</TabsTrigger>
          </TabsList>

          <TabsContent value="progress" className="space-y-4">
            {/* Screening Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <ClipboardList className="w-5 h-5" />
                    Screening
                  </span>
                  {screening ? (
                    <Badge
                      variant={
                        screening.status === ScreeningStatus.COMPLETED
                          ? 'default'
                          : 'secondary'
                      }
                    >
                      {screening.status}
                    </Badge>
                  ) : (
                    <Badge variant="outline">Not Started</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {screening ? (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Type:</span>
                      <span>{screening.screeningType.replace('_', ' ')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Score:</span>
                      <span>{screening.totalScore}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Risk Level:</span>
                      <Badge
                        variant={
                          screening.riskLevel === 'HIGH' ||
                          screening.riskLevel === 'SEVERE'
                            ? 'destructive'
                            : 'secondary'
                        }
                      >
                        {screening.riskLevel}
                      </Badge>
                    </div>
                    {screening.completedAt && (
                      <div className="flex justify-between">
                        <span>Completed:</span>
                        <span>
                          {new Date(screening.completedAt).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-muted-foreground">
                    No screening completed yet.
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Plan Status */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Target className="w-5 h-5" />
                    Therapy Plan
                  </span>
                  {plan ? (
                    <Badge
                      variant={
                        plan.status === PlanStatus.ACTIVE
                          ? 'default'
                          : 'secondary'
                      }
                    >
                      {plan.status}
                    </Badge>
                  ) : (
                    <Badge variant="outline">Not Created</Badge>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {plan ? (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Goals:</span>
                      <span>{plan.goals.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Duration:</span>
                      <span>{plan.duration} weeks</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Frequency:</span>
                      <span>{plan.frequency} sessions/week</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Total Sessions:</span>
                      <span>{plan.sessions.length}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-muted-foreground">
                    No therapy plan created yet.
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Session Progress */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="flex items-center gap-2">
                    <Play className="w-5 h-5" />
                    Sessions
                  </span>
                  <Badge variant="outline">
                    {completedSessions.length} completed
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {plan && plan.sessions.length > 0 ? (
                  <div className="space-y-3">
                    {plan.sessions.map(session => {
                      const isCompleted = completedSessions.some(
                        cs => cs.id === session.id
                      )
                      return (
                        <div
                          key={session.id}
                          className="flex items-center justify-between p-3 border rounded-lg"
                        >
                          <div>
                            <div className="font-medium">
                              Session {session.sessionNumber}
                            </div>
                            <div className="text-sm text-muted-foreground">
                              {session.exercises.length} exercises
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={isCompleted ? 'default' : 'outline'}
                            >
                              {isCompleted ? 'Completed' : session.status}
                            </Badge>
                            {!isCompleted &&
                              session.status === SessionStatus.SCHEDULED && (
                                <Button
                                  size="sm"
                                  onClick={() => handleStartSession(session)}
                                >
                                  Start
                                </Button>
                              )}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-muted-foreground">
                    No sessions available yet.
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="actions" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Screening Actions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Screening</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button
                    className="w-full"
                    onClick={() =>
                      handleStartScreening(ScreeningType.COMPREHENSIVE)
                    }
                    disabled={!!screening}
                  >
                    <ClipboardList className="w-4 h-4 mr-2" />
                    {screening
                      ? 'Screening Complete'
                      : 'Start Comprehensive Screening'}
                  </Button>
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={() =>
                      handleStartScreening(ScreeningType.ARTICULATION)
                    }
                    disabled={!!screening}
                  >
                    Articulation Only
                  </Button>
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={() => handleStartScreening(ScreeningType.LANGUAGE)}
                    disabled={!!screening}
                  >
                    Language Only
                  </Button>
                </CardContent>
              </Card>

              {/* Plan Actions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Therapy Plan</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button
                    className="w-full"
                    onClick={() =>
                      setFlowState(prev => ({ ...prev, currentStep: 'plan' }))
                    }
                    disabled={!screening || !!plan}
                  >
                    <Target className="w-4 h-4 mr-2" />
                    {plan ? 'View Plan' : 'Create Therapy Plan'}
                  </Button>
                  {plan && (
                    <div className="text-sm text-muted-foreground">
                      Plan includes {plan.goals.length} goals and{' '}
                      {plan.sessions.length} sessions
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    )
  }

  const { currentStep, student, screening, currentSession, providerMatrix } =
    flowState

  if (loading || !student || !providerMatrix) {
    return (
      <Card className="w-full max-w-2xl mx-auto">
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">SLP Therapy System</h1>
          <p className="text-muted-foreground">
            Speech-Language Pathology screening, planning, and therapy sessions
          </p>
        </div>
        <Button variant="outline" onClick={onExit}>
          Exit SLP System
        </Button>
      </div>

      {/* Error Display */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Step Content */}
      <div className="space-y-6">
        {currentStep === 'overview' && renderOverview()}

        {currentStep === 'screening' && (
          <ScreeningForm
            studentId={studentId}
            tenantId={tenantId}
            screeningType={selectedScreeningType}
            onComplete={handleScreeningComplete}
            onCancel={() =>
              setFlowState(prev => ({ ...prev, currentStep: 'overview' }))
            }
          />
        )}

        {currentStep === 'plan' && screening && (
          <TherapyPlan
            student={student}
            screening={screening}
            onPlanCreated={handlePlanCreated}
            onBack={() =>
              setFlowState(prev => ({ ...prev, currentStep: 'overview' }))
            }
          />
        )}

        {currentStep === 'session' && currentSession && (
          <ExerciseSession
            session={currentSession}
            student={student}
            providerMatrix={providerMatrix}
            onSessionComplete={handleSessionComplete}
            onBack={() =>
              setFlowState(prev => ({ ...prev, currentStep: 'overview' }))
            }
          />
        )}
      </div>
    </div>
  )
}
