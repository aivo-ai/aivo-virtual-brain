/**
 * S3-13 SEL Check-in Page
 * Daily mood and emotional state check-in with grade-band visuals
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Textarea } from '../../components/ui/Textarea'
import { Alert, AlertDescription } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { MoodDial } from '../../components/sel/MoodDial'
import {
  SELStudent,
  MoodCheckIn,
  useSELQueries,
  useSELMutations,
  getLocalizedCopy,
} from '../../api/selClient'
import {
  Heart,
  Zap,
  Brain,
  User,
  BookOpen,
  AlertTriangle,
  CheckCircle,
  MapPin,
} from '../../components/ui/Icons'

export function Checkin() {
  const { studentId } = useParams<{ studentId: string }>()
  const navigate = useNavigate()

  const [student, setStudent] = useState<SELStudent | null>(null)
  const [checkInData, setCheckInData] = useState({
    moodLevel: 5,
    energyLevel: 5,
    stressLevel: 5,
    socialConnectedness: 5,
    academicConfidence: 5,
    notes: '',
    tags: [] as string[],
    location: '',
  })
  const [recentCheckIns, setRecentCheckIns] = useState<MoodCheckIn[]>([])
  const [selectedTags, setSelectedTags] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [consentError, setConsentError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const { getStudent, getRecentCheckIns, loading, error } = useSELQueries()
  const { createCheckIn } = useSELMutations()

  const commonTags = [
    'happy',
    'sad',
    'anxious',
    'excited',
    'tired',
    'focused',
    'overwhelmed',
    'calm',
    'frustrated',
    'grateful',
    'lonely',
    'confident',
  ]

  useEffect(() => {
    if (studentId) {
      loadStudentData()
    }
  }, [studentId])

  useEffect(() => {
    // Listen for SEL alerts
    const handleSELAlert = (event: CustomEvent) => {
      console.log('SEL Alert received:', event.detail)
      // Could show toast notification here
    }

    window.addEventListener('SEL_ALERT', handleSELAlert as EventListener)
    return () =>
      window.removeEventListener('SEL_ALERT', handleSELAlert as EventListener)
  }, [])

  const loadStudentData = async () => {
    if (!studentId) return

    try {
      const [studentData, checkInsData] = await Promise.all([
        getStudent(studentId),
        getRecentCheckIns(studentId, 5),
      ])

      setStudent(studentData)
      setRecentCheckIns(checkInsData)

      // Check consent
      if (!studentData.selConsent.granted) {
        setConsentError(getLocalizedCopy('consent.required'))
      }
    } catch (err) {
      console.error('Failed to load student data:', err)
    }
  }

  const handleTagToggle = (tag: string) => {
    setSelectedTags(prev =>
      prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
    )
  }

  const handleSubmit = async () => {
    if (!student || !student.selConsent.granted) {
      setConsentError(getLocalizedCopy('consent.required'))
      return
    }

    setIsSubmitting(true)
    setSuccessMessage(null)

    try {
      const input = {
        studentId: student.id,
        mood: getMoodFromLevel(checkInData.moodLevel),
        energy: checkInData.energyLevel,
        stress: checkInData.stressLevel,
        tags: selectedTags,
        notes: checkInData.notes || undefined,
      }

      const result = await createCheckIn(input)

      if (result) {
        setSuccessMessage('Check-in submitted successfully!')

        // Reset form
        setCheckInData({
          moodLevel: 5,
          energyLevel: 5,
          stressLevel: 5,
          socialConnectedness: 5,
          academicConfidence: 5,
          notes: '',
          tags: [],
          location: '',
        })
        setSelectedTags([])

        // Refresh recent check-ins
        const updatedCheckIns = await getRecentCheckIns(studentId!, 5)
        setRecentCheckIns(updatedCheckIns)

        // Show any alerts that were triggered
        if (result.alerts && result.alerts.length > 0) {
          result.alerts.forEach((alert: any) => {
            // Show alert notification
            console.log('Alert triggered:', alert)
          })
        }
      }
    } catch (err) {
      console.error('Failed to submit check-in:', err)
    } finally {
      setIsSubmitting(false)
    }
  }

  const getMoodFromLevel = (level: number): string => {
    if (level <= 2) return 'very-sad'
    if (level <= 4) return 'sad'
    if (level === 5) return 'neutral'
    if (level <= 7) return 'happy'
    return 'very-happy'
  }

  const getMoodTrend = () => {
    if (recentCheckIns.length < 2) return null

    const current = recentCheckIns[0]?.moodLevel || 0
    const previous = recentCheckIns[1]?.moodLevel || 0

    if (current > previous) return { direction: 'up', color: 'text-green-600' }
    if (current < previous) return { direction: 'down', color: 'text-red-600' }
    return { direction: 'stable', color: 'text-gray-600' }
  }

  if (loading || !student) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  const trend = getMoodTrend()

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold text-gray-900">Daily Check-in</h1>
        <p className="text-gray-600">
          Hi {student.firstName}! How are you feeling today?
        </p>
        {trend && (
          <Badge variant="outline" className={trend.color}>
            Mood trend: {trend.direction}
          </Badge>
        )}
      </div>

      {/* Consent Error */}
      {consentError && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {consentError}
            <Button
              variant="outline"
              size="sm"
              className="ml-2"
              onClick={() => navigate(`/consent/${studentId}`)}
            >
              Update Consent
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Success Message */}
      {successMessage && (
        <Alert>
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>{successMessage}</AlertDescription>
        </Alert>
      )}

      {/* Error Message */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Check-in Form */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Heart className="w-5 h-5 text-red-500" />
                {getLocalizedCopy('mood.question')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <MoodDial
                value={checkInData.moodLevel}
                onChange={value =>
                  setCheckInData(prev => ({ ...prev, moodLevel: value }))
                }
                gradeLevel={student.gradeLevel}
                label=""
                max={10}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-yellow-500" />
                {getLocalizedCopy('energy.question')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <MoodDial
                value={checkInData.energyLevel}
                onChange={value =>
                  setCheckInData(prev => ({ ...prev, energyLevel: value }))
                }
                gradeLevel={student.gradeLevel}
                label=""
                max={10}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-purple-500" />
                {getLocalizedCopy('stress.question')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <MoodDial
                value={checkInData.stressLevel}
                onChange={value =>
                  setCheckInData(prev => ({ ...prev, stressLevel: value }))
                }
                gradeLevel={student.gradeLevel}
                label=""
                max={10}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5 text-blue-500" />
                {getLocalizedCopy('social.question')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <MoodDial
                value={checkInData.socialConnectedness}
                onChange={value =>
                  setCheckInData(prev => ({
                    ...prev,
                    socialConnectedness: value,
                  }))
                }
                gradeLevel={student.gradeLevel}
                label=""
                max={10}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-green-500" />
                {getLocalizedCopy('academic.question')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <MoodDial
                value={checkInData.academicConfidence}
                onChange={value =>
                  setCheckInData(prev => ({
                    ...prev,
                    academicConfidence: value,
                  }))
                }
                gradeLevel={student.gradeLevel}
                label=""
                max={10}
              />
            </CardContent>
          </Card>

          {/* Tags */}
          <Card>
            <CardHeader>
              <CardTitle>What words describe how you're feeling?</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {commonTags.map(tag => (
                  <button
                    key={tag}
                    onClick={() => handleTagToggle(tag)}
                    className={`px-3 py-1 rounded-full border transition-colors ${
                      selectedTags.includes(tag)
                        ? 'bg-blue-100 border-blue-500 text-blue-700'
                        : 'bg-gray-50 border-gray-300 text-gray-600 hover:border-gray-400'
                    }`}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          <Card>
            <CardHeader>
              <CardTitle>Anything else you'd like to share?</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                value={checkInData.notes}
                onChange={e =>
                  setCheckInData(prev => ({ ...prev, notes: e.target.value }))
                }
                placeholder="Tell us more about how you're feeling today..."
                rows={4}
              />
            </CardContent>
          </Card>

          {/* Location */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-gray-500" />
                Where are you right now?
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {[
                  'Classroom',
                  'Library',
                  'Cafeteria',
                  'Home',
                  'Playground',
                  'Other',
                ].map(location => (
                  <button
                    key={location}
                    onClick={() =>
                      setCheckInData(prev => ({ ...prev, location }))
                    }
                    className={`px-3 py-1 rounded-full border transition-colors ${
                      checkInData.location === location
                        ? 'bg-green-100 border-green-500 text-green-700'
                        : 'bg-gray-50 border-gray-300 text-gray-600 hover:border-gray-400'
                    }`}
                  >
                    {location}
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Submit Button */}
          <Button
            onClick={handleSubmit}
            disabled={isSubmitting || !student.selConsent.granted}
            className="w-full py-3 text-lg"
          >
            {isSubmitting ? (
              <div className="flex items-center gap-2">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Submitting...
              </div>
            ) : (
              getLocalizedCopy('checkin.submit')
            )}
          </Button>
        </div>

        {/* Sidebar - Recent Check-ins */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Check-ins</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentCheckIns.length === 0 ? (
                <p className="text-gray-500 text-sm">No recent check-ins</p>
              ) : (
                recentCheckIns.map(checkIn => (
                  <div
                    key={checkIn.id}
                    className="border-l-4 border-blue-200 pl-3 py-2"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium">
                          Mood: {checkIn.moodLevel}/10
                        </div>
                        <div className="text-sm text-gray-500">
                          {new Date(checkIn.timestamp).toLocaleDateString()}
                        </div>
                      </div>
                      <div className="text-2xl">
                        {checkIn.moodLevel >= 8
                          ? '😄'
                          : checkIn.moodLevel >= 6
                            ? '😊'
                            : checkIn.moodLevel >= 4
                              ? '😐'
                              : '😟'}
                      </div>
                    </div>
                    {checkIn.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {checkIn.tags.slice(0, 3).map(tag => (
                          <Badge
                            key={tag}
                            variant="outline"
                            className="text-xs"
                          >
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => navigate(`/sel/strategies/${studentId}`)}
              >
                View Helpful Strategies
              </Button>
              <Button
                variant="outline"
                className="w-full justify-start"
                onClick={() => navigate(`/dashboard/${studentId}`)}
              >
                Back to Dashboard
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
