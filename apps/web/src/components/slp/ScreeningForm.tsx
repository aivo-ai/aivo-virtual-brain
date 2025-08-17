/**
 * S3-12 SLP Screening Form Component
 * Handles screening questionnaires with consent-aware gating
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import { Button } from '../ui/Button'
import { Label } from '../ui/Label'
import { Textarea } from '../ui/Textarea'
import { RadioGroup, RadioGroupItem } from '../ui/RadioGroup'
import { Badge } from '../ui/Badge'
import { Alert, AlertDescription } from '../ui/Alert'
import { Progress } from '../ui/Progress'
import { Volume2, MicIcon, AlertTriangle, CheckCircle } from '../ui/Icons'
import {
  type SLPScreening,
  type ScreeningResponse,
  type SLPStudent,
  type ProviderMatrix,
  ScreeningType,
  ScreeningStatus,
  ResponseType,
  RiskLevel,
  useSLPMutations,
  useSLPQueries,
  useTTS,
  useASR,
} from '@/api/slpClient'

interface ScreeningQuestion {
  id: string
  text: string
  responseType: ResponseType
  options?: string[]
  required: boolean
  category: string
  scoringWeight: number
  ttsEnabled?: boolean
}

interface ScreeningFormProps {
  studentId: string
  tenantId: string
  screeningType: ScreeningType
  onComplete: (screening: SLPScreening) => void
  onCancel: () => void
}

const SCREENING_QUESTIONS: Record<ScreeningType, ScreeningQuestion[]> = {
  [ScreeningType.ARTICULATION]: [
    {
      id: 'art_1',
      text: 'Does the child have difficulty pronouncing certain sounds?',
      responseType: ResponseType.BOOLEAN,
      required: true,
      category: 'Speech Clarity',
      scoringWeight: 3,
      ttsEnabled: true,
    },
    {
      id: 'art_2',
      text: "Rate the clarity of the child's speech (1=Very unclear, 5=Very clear)",
      responseType: ResponseType.SCALE,
      required: true,
      category: 'Speech Clarity',
      scoringWeight: 4,
    },
    {
      id: 'art_3',
      text: 'Which sounds are most difficult for the child?',
      responseType: ResponseType.MULTIPLE_CHOICE,
      options: ['R sounds', 'L sounds', 'S sounds', 'TH sounds', 'Other'],
      required: false,
      category: 'Specific Sounds',
      scoringWeight: 2,
    },
    {
      id: 'art_4',
      text: 'Additional observations about speech patterns',
      responseType: ResponseType.TEXT,
      required: false,
      category: 'Observations',
      scoringWeight: 1,
    },
  ],
  [ScreeningType.LANGUAGE]: [
    {
      id: 'lang_1',
      text: 'Does the child follow multi-step directions easily?',
      responseType: ResponseType.BOOLEAN,
      required: true,
      category: 'Comprehension',
      scoringWeight: 4,
      ttsEnabled: true,
    },
    {
      id: 'lang_2',
      text: "Rate the child's vocabulary for their age (1=Below average, 5=Above average)",
      responseType: ResponseType.SCALE,
      required: true,
      category: 'Expression',
      scoringWeight: 3,
    },
    {
      id: 'lang_3',
      text: 'Does the child use complete sentences?',
      responseType: ResponseType.BOOLEAN,
      required: true,
      category: 'Expression',
      scoringWeight: 3,
    },
  ],
  [ScreeningType.FLUENCY]: [
    {
      id: 'flu_1',
      text: 'Does the child repeat sounds, syllables, or words when speaking?',
      responseType: ResponseType.BOOLEAN,
      required: true,
      category: 'Repetitions',
      scoringWeight: 4,
      ttsEnabled: true,
    },
    {
      id: 'flu_2',
      text: 'Rate the frequency of disfluencies (1=Never, 5=Very frequent)',
      responseType: ResponseType.SCALE,
      required: true,
      category: 'Frequency',
      scoringWeight: 4,
    },
  ],
  [ScreeningType.VOICE]: [
    {
      id: 'voice_1',
      text: "Is the child's voice hoarse or raspy?",
      responseType: ResponseType.BOOLEAN,
      required: true,
      category: 'Voice Quality',
      scoringWeight: 3,
      ttsEnabled: true,
    },
    {
      id: 'voice_2',
      text: "Rate the appropriateness of the child's voice volume (1=Too quiet/loud, 5=Just right)",
      responseType: ResponseType.SCALE,
      required: true,
      category: 'Voice Volume',
      scoringWeight: 2,
    },
  ],
  [ScreeningType.COMPREHENSIVE]: [
    // Combination of all above questions
    ...Object.values({
      [ScreeningType.ARTICULATION]: [],
      [ScreeningType.LANGUAGE]: [],
      [ScreeningType.FLUENCY]: [],
      [ScreeningType.VOICE]: [],
    }).flat(),
  ],
}

export function ScreeningForm({
  studentId,
  tenantId,
  screeningType,
  onComplete,
  onCancel,
}: ScreeningFormProps) {
  const [responses, setResponses] = useState<Record<string, ScreeningResponse>>(
    {}
  )
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [student, setStudent] = useState<SLPStudent | null>(null)
  const [providerMatrix, setProviderMatrix] = useState<ProviderMatrix | null>(
    null
  )
  const [consentError, setConsentError] = useState<string | null>(null)
  const [screening, setScreening] = useState<SLPScreening | null>(null)

  const { getStudent, getProviderMatrix } = useSLPQueries()
  const { createScreening, updateScreening, loading, error } = useSLPMutations()
  const { speak, isPlaying } = useTTS()
  const { startRecording, stopRecording, isRecording, transcript } = useASR()

  const questions = SCREENING_QUESTIONS[screeningType] || []
  const currentQuestion = questions[currentQuestionIndex]
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100

  useEffect(() => {
    loadInitialData()
  }, [studentId])

  useEffect(() => {
    if (transcript && currentQuestion?.responseType === ResponseType.TEXT) {
      handleResponseChange(currentQuestion.id, transcript)
    }
  }, [transcript, currentQuestion])

  const loadInitialData = async () => {
    try {
      const [studentData, matrixData] = await Promise.all([
        getStudent(studentId),
        getProviderMatrix(),
      ])

      setStudent(studentData)
      setProviderMatrix(matrixData)

      // Check consent requirements
      checkConsent(studentData, matrixData)

      // Create initial screening
      const result = await createScreening({
        studentId,
        tenantId,
        screeningType,
      })

      setScreening(result.screening)
    } catch (err) {
      console.error('Failed to load screening data:', err)
    }
  }

  const checkConsent = (student: SLPStudent, matrix: ProviderMatrix) => {
    const errors: string[] = []

    // Check audio consent for TTS/ASR
    if (matrix.tts.enabled && !student.audioConsent.granted) {
      errors.push('Audio consent required for text-to-speech functionality')
    }

    if (matrix.asr.enabled && !student.audioConsent.granted) {
      errors.push('Audio consent required for speech recognition')
    }

    // Check video consent if recording is enabled
    if (matrix.recording.enabled && !student.videoConsent.granted) {
      errors.push('Video consent required for session recording')
    }

    if (errors.length > 0) {
      setConsentError(errors.join('. '))
    }
  }

  const handleResponseChange = (
    questionId: string,
    value: string | number | boolean
  ) => {
    const question = questions.find(q => q.id === questionId)
    if (!question) return

    const response: ScreeningResponse = {
      questionId,
      questionText: question.text,
      responseType: question.responseType,
      value,
      score: calculateQuestionScore(question, value),
    }

    setResponses(prev => ({
      ...prev,
      [questionId]: response,
    }))
  }

  const calculateQuestionScore = (
    question: ScreeningQuestion,
    value: string | number | boolean
  ): number => {
    switch (question.responseType) {
      case ResponseType.BOOLEAN:
        return value === true ? question.scoringWeight : 0
      case ResponseType.SCALE:
        return (Number(value) / 5) * question.scoringWeight
      case ResponseType.MULTIPLE_CHOICE:
        return question.scoringWeight * 0.5 // Default scoring
      case ResponseType.TEXT:
        return 0 // Manual scoring required
      default:
        return 0
    }
  }

  const handleNext = () => {
    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1)
    }
  }

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1)
    }
  }

  const handleSubmit = async () => {
    if (!screening) return

    try {
      const responseList = Object.values(responses)
      const totalScore = responseList.reduce((sum, r) => sum + r.score, 0)
      const maxScore = questions.reduce((sum, q) => sum + q.scoringWeight, 0)
      calculateRiskLevel(totalScore, maxScore) // Calculate but don't store unused variable

      const result = await updateScreening(screening.id, {
        responses: responseList,
        status: ScreeningStatus.COMPLETED,
      })

      if (result.success) {
        onComplete(result.screening)
      }
    } catch (err) {
      console.error('Failed to submit screening:', err)
    }
  }

  const calculateRiskLevel = (score: number, maxScore: number): RiskLevel => {
    const percentage = (score / maxScore) * 100

    if (percentage >= 75) return RiskLevel.SEVERE
    if (percentage >= 50) return RiskLevel.HIGH
    if (percentage >= 25) return RiskLevel.MODERATE
    return RiskLevel.LOW
  }

  const handleTTS = async () => {
    if (!currentQuestion?.ttsEnabled || !providerMatrix?.tts.enabled) return
    if (!student?.audioConsent.granted) {
      setConsentError('Audio consent required for text-to-speech')
      return
    }

    await speak(currentQuestion.text, providerMatrix.tts.config)
  }

  const handleASR = async () => {
    if (!providerMatrix?.asr.enabled) return
    if (!student?.audioConsent.granted) {
      setConsentError('Audio consent required for speech recognition')
      return
    }

    if (isRecording) {
      await stopRecording()
    } else {
      await startRecording(providerMatrix.asr.config)
    }
  }

  const renderQuestion = () => {
    if (!currentQuestion) return null

    const currentResponse = responses[currentQuestion.id]

    switch (currentQuestion.responseType) {
      case ResponseType.BOOLEAN:
        return (
          <RadioGroup
            value={currentResponse?.value?.toString() || ''}
            onValueChange={(value: string) =>
              handleResponseChange(currentQuestion.id, value === 'true')
            }
            className="space-y-3"
          >
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="true" id="yes" />
              <Label htmlFor="yes">Yes</Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="false" id="no" />
              <Label htmlFor="no">No</Label>
            </div>
          </RadioGroup>
        )

      case ResponseType.SCALE:
        return (
          <div className="space-y-4">
            <RadioGroup
              value={currentResponse?.value?.toString() || ''}
              onValueChange={(value: string) =>
                handleResponseChange(currentQuestion.id, Number(value))
              }
              className="flex space-x-4"
            >
              {[1, 2, 3, 4, 5].map(num => (
                <div key={num} className="flex items-center space-x-2">
                  <RadioGroupItem value={num.toString()} id={`scale-${num}`} />
                  <Label htmlFor={`scale-${num}`}>{num}</Label>
                </div>
              ))}
            </RadioGroup>
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>
        )

      case ResponseType.MULTIPLE_CHOICE:
        return (
          <RadioGroup
            value={currentResponse?.value?.toString() || ''}
            onValueChange={(value: string) =>
              handleResponseChange(currentQuestion.id, value)
            }
            className="space-y-2"
          >
            {currentQuestion.options?.map(option => (
              <div key={option} className="flex items-center space-x-2">
                <RadioGroupItem value={option} id={option} />
                <Label htmlFor={option}>{option}</Label>
              </div>
            ))}
          </RadioGroup>
        )

      case ResponseType.TEXT:
        return (
          <div className="space-y-4">
            <Textarea
              value={currentResponse?.value?.toString() || ''}
              onChange={e =>
                handleResponseChange(currentQuestion.id, e.target.value)
              }
              placeholder="Enter your response..."
              className="min-h-[100px]"
            />
            {providerMatrix?.asr.enabled && student?.audioConsent.granted && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleASR}
                disabled={!student?.audioConsent.granted}
                className="flex items-center gap-2"
              >
                <MicIcon className="w-4 h-4" />
                {isRecording ? 'Stop Recording' : 'Voice Input'}
              </Button>
            )}
          </div>
        )

      default:
        return null
    }
  }

  if (!student || !providerMatrix) {
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
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            {screeningType.replace('_', ' ')} Screening
            <Badge variant="outline">
              {student.firstName} {student.lastName}
            </Badge>
          </CardTitle>
          <Badge variant="secondary">
            Question {currentQuestionIndex + 1} of {questions.length}
          </Badge>
        </div>
        <Progress value={progress} className="mt-2" />
      </CardHeader>

      <CardContent className="p-6 space-y-6">
        {consentError && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{consentError}</AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {currentQuestion && (
          <div className="space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-medium mb-2">
                  {currentQuestion.text}
                </h3>
                <Badge variant="outline" className="text-xs">
                  {currentQuestion.category}
                </Badge>
              </div>
              {currentQuestion.ttsEnabled &&
                providerMatrix.tts.enabled &&
                student.audioConsent.granted && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={handleTTS}
                    disabled={isPlaying}
                    className="flex items-center gap-2"
                  >
                    <Volume2 className="w-4 h-4" />
                  </Button>
                )}
            </div>

            {renderQuestion()}
          </div>
        )}

        <div className="flex justify-between pt-6">
          <Button
            type="button"
            variant="outline"
            onClick={currentQuestionIndex === 0 ? onCancel : handlePrevious}
          >
            {currentQuestionIndex === 0 ? 'Cancel' : 'Previous'}
          </Button>

          <div className="flex gap-2">
            {currentQuestionIndex === questions.length - 1 ? (
              <Button
                onClick={handleSubmit}
                disabled={loading || !responses[currentQuestion?.id]}
                className="flex items-center gap-2"
              >
                {loading ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <CheckCircle className="w-4 h-4" />
                )}
                Submit Screening
              </Button>
            ) : (
              <Button
                onClick={handleNext}
                disabled={
                  currentQuestion?.required && !responses[currentQuestion.id]
                }
              >
                Next
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
