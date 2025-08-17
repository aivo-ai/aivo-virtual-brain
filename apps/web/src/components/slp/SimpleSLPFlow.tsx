/**
 * S3-12 Simple SLP Flow Component
 * Main orchestrator for SLP screening, planning, and sessions using basic HTML
 */

import { useState, useEffect } from 'react'
import { Button } from '../ui/Button'
import {
  type SLPStudent,
  type SLPScreening,
  type SLPPlan,
  type TherapySession,
  type ProviderMatrix,
  ScreeningType,
  useSLPQueries,
} from '../../api/slpClient'

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

export function SimpleSLPFlow({
  studentId,
  onExit,
}: Omit<SLPFlowProps, 'tenantId'>) {
  const [flowState, setFlowState] = useState<FlowState>({
    currentStep: 'overview',
    student: null,
    screening: null,
    plan: null,
    currentSession: null,
    providerMatrix: null,
    completedSessions: [],
  })

  const { getStudent, getProviderMatrix, loading, error } = useSLPQueries()

  useEffect(() => {
    loadInitialData()
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

  const renderOverview = () => {
    const { student, screening, plan, completedSessions } = flowState

    if (!student) return null

    return (
      <div className="space-y-6">
        {/* Student Info */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-4">Student Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-gray-500">Name</div>
              <div className="font-medium">
                {student.firstName} {student.lastName}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Grade Level</div>
              <div className="font-medium">{student.gradeLevel}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Date of Birth</div>
              <div className="font-medium">
                {new Date(student.dateOfBirth).toLocaleDateString()}
              </div>
            </div>
          </div>

          {/* Consent Status */}
          <div className="mt-4 pt-4 border-t">
            <div className="text-sm text-gray-500 mb-2">Consent Status</div>
            <div className="flex gap-2">
              <span
                className={`px-2 py-1 rounded text-sm ${
                  student.audioConsent.granted
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                Audio:{' '}
                {student.audioConsent.granted ? 'Granted' : 'Not Granted'}
              </span>
              <span
                className={`px-2 py-1 rounded text-sm ${
                  student.videoConsent.granted
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                Video:{' '}
                {student.videoConsent.granted ? 'Granted' : 'Not Granted'}
              </span>
              <span
                className={`px-2 py-1 rounded text-sm ${
                  student.parentConsent.granted
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                Parent:{' '}
                {student.parentConsent.granted ? 'Granted' : 'Not Granted'}
              </span>
            </div>
          </div>
        </div>

        {/* Screening Status */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-bold mb-4">Screening</h3>
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
                <span
                  className={`px-2 py-1 rounded text-sm ${
                    screening.riskLevel === 'HIGH' ||
                    screening.riskLevel === 'SEVERE'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                >
                  {screening.riskLevel}
                </span>
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
            <div>
              <p className="text-gray-500 mb-4">No screening completed yet.</p>
              <Button
                onClick={() =>
                  setFlowState(prev => ({ ...prev, currentStep: 'screening' }))
                }
              >
                Start Comprehensive Screening
              </Button>
            </div>
          )}
        </div>

        {/* Plan Status */}
        {screening && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-bold mb-4">Therapy Plan</h3>
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
              <div>
                <p className="text-gray-500 mb-4">
                  No therapy plan created yet.
                </p>
                <Button
                  onClick={() =>
                    setFlowState(prev => ({ ...prev, currentStep: 'plan' }))
                  }
                >
                  Create Therapy Plan
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Sessions */}
        {plan && plan.sessions.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-bold mb-4">
              Sessions ({completedSessions.length} completed)
            </h3>
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
                      <div className="text-sm text-gray-500">
                        {session.exercises.length} exercises
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-1 rounded text-sm ${
                          isCompleted
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {isCompleted ? 'Completed' : session.status}
                      </span>
                      {!isCompleted && (
                        <Button
                          variant="primary"
                          onClick={() =>
                            setFlowState(prev => ({
                              ...prev,
                              currentSession: session,
                              currentStep: 'session',
                            }))
                          }
                        >
                          Start
                        </Button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    )
  }

  const { currentStep, student, screening, currentSession, providerMatrix } =
    flowState

  if (loading || !student || !providerMatrix) {
    return (
      <div className="w-full max-w-2xl mx-auto p-6">
        <div className="bg-white rounded-lg shadow p-8">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">SLP Therapy System</h1>
          <p className="text-gray-600">
            Speech-Language Pathology screening, planning, and therapy sessions
          </p>
        </div>
        <Button variant="outline" onClick={onExit}>
          Exit SLP System
        </Button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex">
            <div className="text-red-400">⚠</div>
            <div className="ml-3 text-red-700">{error}</div>
          </div>
        </div>
      )}

      {/* Step Content */}
      <div className="space-y-6">
        {currentStep === 'overview' && renderOverview()}

        {currentStep === 'screening' && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold mb-4">Screening Assessment</h2>
            <p className="text-gray-600 mb-6">
              Please complete the comprehensive screening assessment for{' '}
              {student.firstName} {student.lastName}.
            </p>
            {/* Mock screening form */}
            <div className="space-y-4">
              <div className="p-4 border rounded-lg">
                <h3 className="font-medium mb-2">Sample Question 1</h3>
                <p className="text-sm text-gray-600 mb-3">
                  Does the child have difficulty pronouncing certain sounds?
                </p>
                <div className="space-y-2">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="q1"
                      value="yes"
                      className="mr-2"
                    />
                    Yes
                  </label>
                  <label className="flex items-center">
                    <input type="radio" name="q1" value="no" className="mr-2" />
                    No
                  </label>
                </div>
              </div>
              <div className="flex justify-between">
                <Button
                  variant="outline"
                  onClick={() =>
                    setFlowState(prev => ({ ...prev, currentStep: 'overview' }))
                  }
                >
                  Back
                </Button>
                <Button
                  onClick={() => {
                    // Mock screening completion
                    const mockScreening: SLPScreening = {
                      id: 'screening-1',
                      studentId: student.id,
                      tenantId: student.tenantId,
                      screeningType: ScreeningType.COMPREHENSIVE,
                      status: 'COMPLETED' as any,
                      responses: [],
                      totalScore: 75,
                      riskLevel: 'HIGH' as any,
                      recommendations: ['Consider articulation therapy'],
                      completedAt: new Date().toISOString(),
                      createdBy: 'therapist@example.com',
                      createdAt: new Date().toISOString(),
                      updatedAt: new Date().toISOString(),
                    }
                    setFlowState(prev => ({
                      ...prev,
                      screening: mockScreening,
                      currentStep: 'overview',
                    }))
                  }}
                >
                  Complete Screening
                </Button>
              </div>
            </div>
          </div>
        )}

        {currentStep === 'plan' && screening && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold mb-4">Create Therapy Plan</h2>
            <p className="text-gray-600 mb-6">
              Based on the screening results, create a therapy plan for{' '}
              {student.firstName} {student.lastName}.
            </p>
            {/* Mock plan creation */}
            <div className="space-y-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <h3 className="font-medium mb-2">Recommended Goals</h3>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Improve speech sound production accuracy</li>
                  <li>• Enhance expressive language skills</li>
                  <li>• Increase speech fluency</li>
                </ul>
              </div>
              <div className="flex justify-between">
                <Button
                  variant="outline"
                  onClick={() =>
                    setFlowState(prev => ({ ...prev, currentStep: 'overview' }))
                  }
                >
                  Back
                </Button>
                <Button
                  onClick={() => {
                    // Mock plan creation
                    const mockPlan: SLPPlan = {
                      id: 'plan-1',
                      studentId: student.id,
                      tenantId: student.tenantId,
                      screeningId: screening.id,
                      goals: [
                        {
                          id: 'goal-1',
                          category: 'ARTICULATION' as any,
                          description:
                            'Improve speech sound production accuracy',
                          targetBehavior: 'Produce target sounds correctly',
                          measurableOutcome: '80% accuracy',
                          timeframe: '12 weeks',
                          priority: 'HIGH' as any,
                          status: 'NOT_STARTED' as any,
                        },
                      ],
                      sessions: [
                        {
                          id: 'session-1',
                          planId: 'plan-1',
                          sessionNumber: 1,
                          scheduledDate: new Date().toISOString(),
                          status: 'SCHEDULED' as any,
                          exercises: [],
                          createdAt: new Date().toISOString(),
                          updatedAt: new Date().toISOString(),
                        },
                      ],
                      duration: 12,
                      frequency: 2,
                      status: 'APPROVED' as any,
                      createdBy: 'therapist@example.com',
                      createdAt: new Date().toISOString(),
                      updatedAt: new Date().toISOString(),
                    }
                    setFlowState(prev => ({
                      ...prev,
                      plan: mockPlan,
                      currentStep: 'overview',
                    }))
                  }}
                >
                  Create Plan
                </Button>
              </div>
            </div>
          </div>
        )}

        {currentStep === 'session' && currentSession && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-2xl font-bold mb-4">
              Session {currentSession.sessionNumber} - {student.firstName}{' '}
              {student.lastName}
            </h2>
            <p className="text-gray-600 mb-6">
              Complete the therapy exercises for this session.
            </p>
            {/* Mock session interface */}
            <div className="space-y-4">
              <div className="p-4 border rounded-lg">
                <h3 className="font-medium mb-2">
                  Exercise 1: Articulation Practice
                </h3>
                <p className="text-sm text-gray-600 mb-3">
                  Practice saying "red" clearly
                </p>
                <textarea
                  className="w-full p-2 border rounded-md"
                  placeholder="Enter your response..."
                  rows={3}
                />
              </div>
              <div className="flex justify-between">
                <Button
                  variant="outline"
                  onClick={() =>
                    setFlowState(prev => ({
                      ...prev,
                      currentSession: null,
                      currentStep: 'overview',
                    }))
                  }
                >
                  Back to Plan
                </Button>
                <Button
                  onClick={() => {
                    // Mock session completion
                    const completedSession = { ...currentSession }
                    setFlowState(prev => ({
                      ...prev,
                      currentSession: null,
                      completedSessions: [
                        ...prev.completedSessions,
                        completedSession,
                      ],
                      currentStep: 'overview',
                    }))
                  }}
                >
                  Complete Session
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
