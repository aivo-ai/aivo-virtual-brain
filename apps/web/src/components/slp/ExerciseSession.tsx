/**
 * S3-12 SLP Exercise Session Component
 * Interactive therapy exercises with TTS/ASR integration
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Alert, AlertDescription } from '../ui/Alert'
import { Progress } from '../ui/Progress'
import { Textarea } from '../ui/Textarea'
import {
  Volume2,
  VolumeX,
  MicIcon as Mic,
  MicOff,
  Play,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Target,
  Star,
  SkipForward,
} from '../ui/Icons'
import {
  type Exercise,
  type ExerciseAttempt,
  type TherapySession,
  type SLPStudent,
  type ProviderMatrix,
  ExerciseStatus,
  SessionStatus,
  useSLPMutations,
  useTTS,
  useASR,
} from '../../api/slpClient'

interface ExerciseSessionProps {
  session: TherapySession
  student: SLPStudent
  providerMatrix: ProviderMatrix
  onSessionComplete: (session: TherapySession) => void
  onBack: () => void
}

interface ExerciseState {
  exercise: Exercise
  currentPromptIndex: number
  attempts: ExerciseAttempt[]
  status: ExerciseStatus
  score: number
  feedback: string
  studentResponse: string
}

export function ExerciseSession({
  session,
  student,
  providerMatrix,
  onSessionComplete,
  onBack,
}: ExerciseSessionProps) {
  const [currentExerciseIndex, setCurrentExerciseIndex] = useState(0)
  const [exerciseStates, setExerciseStates] = useState<ExerciseState[]>([])
  const [sessionStartTime, setSessionStartTime] = useState<Date>(new Date())
  const [consentChecked, setConsentChecked] = useState(false)
  const [consentErrors, setConsentErrors] = useState<string[]>([])

  const { submitExerciseAttempt, loading, error } = useSLPMutations()
  const { speak, isPlaying } = useTTS()
  const { startRecording, stopRecording, isRecording, transcript } = useASR()

  const currentExercise = exerciseStates[currentExerciseIndex]
  const currentPrompt =
    currentExercise?.exercise.prompts[currentExercise.currentPromptIndex]
  const sessionProgress =
    ((currentExerciseIndex + 1) / session.exercises.length) * 100

  useEffect(() => {
    initializeSession()
  }, [session])

  useEffect(() => {
    checkConsent()
  }, [student, providerMatrix])

  useEffect(() => {
    if (transcript && currentExercise) {
      updateStudentResponse(transcript)
    }
  }, [transcript])

  const initializeSession = () => {
    const initialStates: ExerciseState[] = session.exercises.map(exercise => ({
      exercise,
      currentPromptIndex: 0,
      attempts: [],
      status: ExerciseStatus.NOT_STARTED,
      score: 0,
      feedback: '',
      studentResponse: '',
    }))
    setExerciseStates(initialStates)
    setSessionStartTime(new Date())
  }

  const checkConsent = () => {
    const errors: string[] = []

    // Check TTS consent
    if (providerMatrix.tts.enabled && !student.audioConsent.granted) {
      errors.push('Audio consent required for text-to-speech functionality')
    }

    // Check ASR consent
    if (providerMatrix.asr.enabled && !student.audioConsent.granted) {
      errors.push('Audio consent required for speech recognition')
    }

    // Check recording consent
    if (providerMatrix.recording.enabled && !student.videoConsent.granted) {
      errors.push('Video consent required for session recording')
    }

    setConsentErrors(errors)
    setConsentChecked(true)
  }

  const updateStudentResponse = (response: string) => {
    setExerciseStates(prev => {
      const updated = [...prev]
      if (updated[currentExerciseIndex]) {
        updated[currentExerciseIndex].studentResponse = response
      }
      return updated
    })
  }

  const handleTTS = async (text: string) => {
    if (!providerMatrix.tts.enabled || !student.audioConsent.granted) {
      setConsentErrors(['Audio consent required for text-to-speech'])
      return
    }

    await speak(text, providerMatrix.tts.config)
  }

  const handleASR = async () => {
    if (!providerMatrix.asr.enabled || !student.audioConsent.granted) {
      setConsentErrors(['Audio consent required for speech recognition'])
      return
    }

    if (isRecording) {
      const result = await stopRecording()
      updateStudentResponse(result)
    } else {
      await startRecording(providerMatrix.asr.config)
    }
  }

  const handleNextPrompt = () => {
    if (!currentExercise) return

    const nextPromptIndex = currentExercise.currentPromptIndex + 1

    if (nextPromptIndex < currentExercise.exercise.prompts.length) {
      setExerciseStates(prev => {
        const updated = [...prev]
        updated[currentExerciseIndex].currentPromptIndex = nextPromptIndex
        return updated
      })
    } else {
      // Exercise complete
      handleExerciseComplete()
    }
  }

  const handleExerciseComplete = async () => {
    if (!currentExercise) return

    try {
      const score = calculateExerciseScore(currentExercise)
      const feedback = generateFeedback(currentExercise, score)

      const attemptInput = {
        exerciseId: currentExercise.exercise.id,
        sessionId: session.id,
        studentResponse: currentExercise.studentResponse,
        metadata: {
          prompts: currentExercise.exercise.prompts.length,
          timeSpent: Date.now() - sessionStartTime.getTime(),
          ttsUsed: currentExercise.exercise.ttsEnabled,
          asrUsed: currentExercise.exercise.asrEnabled,
        },
      }

      const result = await submitExerciseAttempt(attemptInput)

      if (result.success) {
        setExerciseStates(prev => {
          const updated = [...prev]
          updated[currentExerciseIndex].status = ExerciseStatus.COMPLETED
          updated[currentExerciseIndex].score = score
          updated[currentExerciseIndex].feedback = feedback
          updated[currentExerciseIndex].attempts.push(result.attempt)
          return updated
        })

        // Move to next exercise
        if (currentExerciseIndex < session.exercises.length - 1) {
          setCurrentExerciseIndex(prev => prev + 1)
        } else {
          // Session complete
          handleSessionComplete()
        }
      }
    } catch (err) {
      console.error('Failed to submit exercise attempt:', err)
    }
  }

  const calculateExerciseScore = (exerciseState: ExerciseState): number => {
    const { exercise, studentResponse } = exerciseState

    // Basic scoring algorithm - would be more sophisticated in real implementation
    let score = 0

    if (studentResponse.trim().length > 0) {
      score += 30 // Base points for participation

      // Check for expected responses
      exercise.prompts.forEach(prompt => {
        if (
          prompt.expectedResponse &&
          studentResponse
            .toLowerCase()
            .includes(prompt.expectedResponse.toLowerCase())
        ) {
          score += 20
        }
      })

      // Length and complexity bonus
      if (studentResponse.split(' ').length >= 5) {
        score += 10
      }
    }

    return Math.min(score, 100)
  }

  const generateFeedback = (
    _exerciseState: ExerciseState,
    score: number
  ): string => {
    if (score >= 80) {
      return 'Excellent work! You completed this exercise with great accuracy.'
    } else if (score >= 60) {
      return 'Good job! Keep practicing to improve your performance.'
    } else if (score >= 40) {
      return 'Nice effort! Focus on the target behaviors we practiced.'
    } else {
      return 'Keep trying! Remember to take your time and practice the techniques we discussed.'
    }
  }

  const handleSessionComplete = () => {
    const completedSession = {
      ...session,
      status: SessionStatus.COMPLETED,
      completedAt: new Date().toISOString(),
      duration: Math.round(
        (Date.now() - sessionStartTime.getTime()) / 1000 / 60
      ), // minutes
    }

    onSessionComplete(completedSession)
  }

  const handleSkipExercise = () => {
    if (currentExerciseIndex < session.exercises.length - 1) {
      setExerciseStates(prev => {
        const updated = [...prev]
        updated[currentExerciseIndex].status = ExerciseStatus.SKIPPED
        return updated
      })
      setCurrentExerciseIndex(prev => prev + 1)
    } else {
      handleSessionComplete()
    }
  }

  const renderExerciseContent = () => {
    if (!currentExercise || !currentPrompt) return null

    const { exercise } = currentExercise

    return (
      <div className="space-y-6">
        {/* Exercise Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">{exercise.title}</h2>
            <p className="text-muted-foreground">{exercise.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{exercise.type.replace('_', ' ')}</Badge>
            <Badge variant="secondary">
              <Clock className="w-3 h-3 mr-1" />
              {exercise.estimatedDuration}min
            </Badge>
          </div>
        </div>

        {/* Instructions */}
        <Alert>
          <Target className="h-4 w-4" />
          <AlertDescription>
            <strong>Instructions:</strong> {exercise.instructions}
          </AlertDescription>
        </Alert>

        {/* Current Prompt */}
        <Card className="border-l-4 border-l-primary">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">
                Prompt {currentExercise.currentPromptIndex + 1} of{' '}
                {exercise.prompts.length}
              </CardTitle>
              <div className="flex items-center gap-2">
                {currentPrompt.ttsEnabled &&
                  providerMatrix.tts.enabled &&
                  student.audioConsent.granted && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleTTS(currentPrompt.text)}
                      disabled={isPlaying}
                    >
                      {isPlaying ? (
                        <VolumeX className="w-4 h-4" />
                      ) : (
                        <Volume2 className="w-4 h-4" />
                      )}
                    </Button>
                  )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-lg mb-4">{currentPrompt.text}</p>

            {currentPrompt.audioUrl && (
              <audio controls className="w-full mb-4">
                <source src={currentPrompt.audioUrl} type="audio/mpeg" />
                Your browser does not support the audio element.
              </audio>
            )}
          </CardContent>
        </Card>

        {/* Student Response */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              Your Response
              {exercise.recordingRequired && (
                <Badge variant="outline">Recording Required</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              value={currentExercise.studentResponse}
              onChange={e => updateStudentResponse(e.target.value)}
              placeholder="Enter your response here..."
              rows={4}
            />

            {exercise.asrEnabled &&
              providerMatrix.asr.enabled &&
              student.audioConsent.granted && (
                <div className="flex items-center gap-2">
                  <Button
                    variant={isRecording ? 'destructive' : 'outline'}
                    onClick={handleASR}
                    className="flex items-center gap-2"
                  >
                    {isRecording ? (
                      <MicOff className="w-4 h-4" />
                    ) : (
                      <Mic className="w-4 h-4" />
                    )}
                    {isRecording ? 'Stop Recording' : 'Voice Input'}
                  </Button>
                  {isRecording && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                      Recording...
                    </div>
                  )}
                </div>
              )}
          </CardContent>
        </Card>

        {/* Materials */}
        {exercise.materials.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Materials</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {exercise.materials.map(material => (
                  <div key={material.id} className="p-3 border rounded-lg">
                    <h4 className="font-medium">{material.title}</h4>
                    {material.description && (
                      <p className="text-sm text-muted-foreground">
                        {material.description}
                      </p>
                    )}
                    {material.url && (
                      <a
                        href={material.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline text-sm"
                      >
                        View Material
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    )
  }

  if (!consentChecked) {
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
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Session Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Play className="w-5 h-5" />
              Session {session.sessionNumber} - {student.firstName}{' '}
              {student.lastName}
            </CardTitle>
            <Badge variant="outline">
              Exercise {currentExerciseIndex + 1} of {session.exercises.length}
            </Badge>
          </div>
          <Progress value={sessionProgress} className="mt-2" />
        </CardHeader>
      </Card>

      {/* Consent Errors */}
      {consentErrors.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <ul className="space-y-1">
              {consentErrors.map((error, index) => (
                <li key={index}>• {error}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}

      {/* General Error */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Exercise Content */}
      {currentExercise && renderExerciseContent()}

      {/* Exercise Navigation */}
      <div className="flex justify-between items-center">
        <Button variant="outline" onClick={onBack}>
          Back to Plan
        </Button>

        <div className="flex items-center gap-2">
          {currentExercise?.studentResponse.trim() && (
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              <Star className="w-4 h-4" />
              Response recorded
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={handleSkipExercise}>
            <SkipForward className="w-4 h-4 mr-2" />
            Skip
          </Button>

          {currentExercise?.currentPromptIndex <
          currentExercise?.exercise.prompts.length - 1 ? (
            <Button
              onClick={handleNextPrompt}
              disabled={!currentExercise?.studentResponse.trim()}
            >
              Next Prompt
            </Button>
          ) : (
            <Button
              onClick={handleExerciseComplete}
              disabled={loading || !currentExercise?.studentResponse.trim()}
              className="flex items-center gap-2"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <CheckCircle2 className="w-4 h-4" />
              )}
              Complete Exercise
            </Button>
          )}
        </div>
      </div>

      {/* Exercise Summary */}
      {exerciseStates.some(
        state => state.status === ExerciseStatus.COMPLETED
      ) && (
        <Card>
          <CardHeader>
            <CardTitle>Session Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {exerciseStates.map((state, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg border text-center ${
                    state.status === ExerciseStatus.COMPLETED
                      ? 'bg-green-50 border-green-200'
                      : state.status === ExerciseStatus.SKIPPED
                        ? 'bg-gray-50 border-gray-200'
                        : index === currentExerciseIndex
                          ? 'bg-blue-50 border-blue-200'
                          : 'bg-muted'
                  }`}
                >
                  <div className="font-medium">{state.exercise.title}</div>
                  <div className="text-sm text-muted-foreground">
                    {state.status === ExerciseStatus.COMPLETED && (
                      <div className="flex items-center justify-center gap-1 text-green-600">
                        <CheckCircle2 className="w-3 h-3" />
                        {state.score}%
                      </div>
                    )}
                    {state.status === ExerciseStatus.SKIPPED && (
                      <span className="text-gray-500">Skipped</span>
                    )}
                    {state.status === ExerciseStatus.NOT_STARTED &&
                      index === currentExerciseIndex && (
                        <span className="text-blue-600">Current</span>
                      )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
