import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  assessmentClient,
  type AssessmentReport,
  type AssessmentSession,
} from '../../api/assessmentClient'

export const Report: React.FC = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const sessionId = searchParams.get('sessionId')

  // State management
  const [report, setReport] = useState<AssessmentReport | null>(null)
  const [session, setSession] = useState<AssessmentSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) {
      setError('No session ID provided')
      setLoading(false)
      return
    }

    loadReport()
  }, [sessionId])

  const loadReport = async () => {
    try {
      setLoading(true)
      setError(null)

      const [reportData, sessionData] = await Promise.all([
        assessmentClient.getReport(sessionId!),
        assessmentClient.getSession(sessionId!),
      ])

      setReport(reportData)
      setSession(sessionData)
    } catch (err) {
      console.error('Error loading report:', err)
      setError('Failed to load assessment report')
    } finally {
      setLoading(false)
    }
  }

  // Grade band for adaptive UI
  const gradeBand = session?.gradeBand || 'K-2'

  // Grade band specific styling
  const getGradeBandStyles = () => {
    switch (gradeBand) {
      case 'K-2':
        return {
          buttonSize: 'text-xl px-6 py-4',
          fontSize: 'text-2xl',
          headerSize: 'text-3xl',
          spacing: 'space-y-8',
          colors: 'bg-gradient-to-br from-blue-400 to-purple-500',
          cardPadding: 'p-8',
        }
      case '3-5':
        return {
          buttonSize: 'text-lg px-5 py-3',
          fontSize: 'text-xl',
          headerSize: 'text-2xl',
          spacing: 'space-y-6',
          colors: 'bg-gradient-to-br from-green-400 to-blue-500',
          cardPadding: 'p-6',
        }
      case '6-12':
        return {
          buttonSize: 'text-base px-4 py-2',
          fontSize: 'text-lg',
          headerSize: 'text-xl',
          spacing: 'space-y-4',
          colors: 'bg-gradient-to-br from-purple-400 to-pink-500',
          cardPadding: 'p-6',
        }
    }
  }

  const styles = getGradeBandStyles()

  const getGradeAppropriateMessages = () => {
    if (!report) return {}

    const accuracy = report.accuracyPercentage

    switch (gradeBand) {
      case 'K-2':
        return {
          title:
            accuracy >= 80
              ? '🌟 Amazing Job!'
              : accuracy >= 60
                ? '🎉 Great Work!'
                : '💪 Keep Learning!',
          subtitle: "You did your best and that's what matters!",
          encouragement:
            accuracy >= 80
              ? "You're a superstar learner! Keep being curious!"
              : accuracy >= 60
                ? "You're doing great! Learning is an adventure!"
                : 'Every day you learn something new. Keep trying!',
        }
      case '3-5':
        return {
          title:
            accuracy >= 80
              ? '🏆 Excellent Work!'
              : accuracy >= 60
                ? '👍 Good Job!'
                : '📚 Ready to Learn More!',
          subtitle: 'Your assessment results show your learning progress',
          encouragement:
            accuracy >= 80
              ? 'You have a strong foundation in these skills!'
              : accuracy >= 60
                ? "You're making good progress in your learning!"
                : 'These results help us create the perfect learning plan for you!',
        }
      case '6-12':
        return {
          title: '📊 Assessment Complete',
          subtitle: 'Baseline Assessment Results',
          encouragement:
            'These results will help personalize your learning experience.',
        }
    }
  }

  const getPerformanceColor = (percentage: number) => {
    if (percentage >= 80) return 'text-green-600'
    if (percentage >= 60) return 'text-yellow-600'
    return 'text-blue-600' // Encouraging blue instead of red
  }

  const getSkillMasteryColor = (mastery: string) => {
    switch (mastery) {
      case 'advanced':
        return 'bg-green-100 text-green-800'
      case 'proficient':
        return 'bg-blue-100 text-blue-800'
      case 'developing':
        return 'bg-yellow-100 text-yellow-800'
      case 'emerging':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getSkillMasteryEmoji = (mastery: string) => {
    switch (mastery) {
      case 'advanced':
        return '🌟'
      case 'proficient':
        return '✅'
      case 'developing':
        return '📈'
      case 'emerging':
        return '🌱'
      default:
        return '📝'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-xl text-gray-600">
            {gradeBand === 'K-2'
              ? 'Creating your special report...'
              : 'Generating your assessment report...'}
          </p>
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Report Error</h1>
          <p className="text-gray-600 mb-6">{error || 'Report not found'}</p>
          <button
            onClick={() => navigate('/assessment')}
            className="bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Return to Assessment
          </button>
        </div>
      </div>
    )
  }

  const messages = getGradeAppropriateMessages()

  return (
    <div className={`min-h-screen ${styles.colors} p-4`}>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <h1 className={`font-bold text-white mb-4 ${styles.headerSize}`}>
            {messages.title}
          </h1>
          <p className={`text-white/90 ${styles.fontSize}`}>
            {messages.subtitle}
          </p>
        </motion.div>

        {/* Main Results Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className={`bg-white rounded-xl shadow-2xl ${styles.cardPadding} mb-8`}
        >
          {/* Overall Performance */}
          <div className="text-center mb-8">
            <div className="flex items-center justify-center space-x-4 mb-6">
              <div className="text-center">
                <div
                  className={`text-6xl font-bold ${getPerformanceColor(report.accuracyPercentage)}`}
                >
                  {Math.round(report.accuracyPercentage)}%
                </div>
                <div className="text-gray-600">Accuracy</div>
              </div>

              <div className="text-center">
                <div className="text-4xl font-bold text-blue-600">
                  {report.correctAnswers}/{report.totalItems}
                </div>
                <div className="text-gray-600">Correct</div>
              </div>

              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {report.surfaceLevel}
                </div>
                <div className="text-gray-600">Level</div>
              </div>
            </div>

            <p className={`${styles.fontSize} text-gray-700 font-medium`}>
              {messages.encouragement}
            </p>
          </div>

          {/* Progress Bar */}
          <div className="mb-8">
            <div className="bg-gray-200 rounded-full h-4 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${report.accuracyPercentage}%` }}
                transition={{ duration: 1.5, delay: 0.5 }}
                className={`h-full rounded-full ${
                  report.accuracyPercentage >= 80
                    ? 'bg-green-500'
                    : report.accuracyPercentage >= 60
                      ? 'bg-yellow-500'
                      : 'bg-blue-500'
                }`}
              />
            </div>
          </div>

          {/* Skills Assessment */}
          {report.skillsAssessed && report.skillsAssessed.length > 0 && (
            <div className="mb-8">
              <h2 className={`font-bold text-gray-900 mb-6 ${styles.fontSize}`}>
                {gradeBand === 'K-2'
                  ? '🎯 What You Learned About'
                  : '📚 Skills Assessed'}
              </h2>

              <div
                className={`grid gap-4 ${
                  gradeBand === 'K-2'
                    ? 'grid-cols-1'
                    : 'grid-cols-1 md:grid-cols-2'
                }`}
              >
                {report.skillsAssessed.map((skill, index) => (
                  <motion.div
                    key={skill.skillId}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="bg-gray-50 rounded-lg p-4"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold text-gray-900">
                        {gradeBand === 'K-2' &&
                          getSkillMasteryEmoji(skill.mastery)}{' '}
                        {skill.skillName}
                      </h3>
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-medium ${getSkillMasteryColor(skill.mastery)}`}
                      >
                        {skill.mastery}
                      </span>
                    </div>

                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <span>Level: {skill.level}</span>
                      <span>•</span>
                      <span>
                        Confidence: {Math.round(skill.confidence * 100)}%
                      </span>
                      <span>•</span>
                      <span>{skill.itemsAssessed} items</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {report.recommendations && report.recommendations.length > 0 && (
            <div className="mb-8">
              <h2 className={`font-bold text-gray-900 mb-6 ${styles.fontSize}`}>
                {gradeBand === 'K-2' ? "🚀 What's Next?" : '💡 Recommendations'}
              </h2>

              <div className={`${styles.spacing}`}>
                {report.recommendations.map((recommendation, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-start space-x-3 bg-blue-50 rounded-lg p-4"
                  >
                    <div className="text-blue-600 mt-1">
                      {gradeBand === 'K-2' ? '🌟' : '💡'}
                    </div>
                    <p className="text-gray-700 flex-1">{recommendation}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {/* Next Steps */}
          {report.nextSteps && report.nextSteps.length > 0 && (
            <div className="mb-8">
              <h2 className={`font-bold text-gray-900 mb-6 ${styles.fontSize}`}>
                {gradeBand === 'K-2'
                  ? '🎮 Ready to Learn More?'
                  : '🎯 Next Steps'}
              </h2>

              <div className={`${styles.spacing}`}>
                {report.nextSteps.map((step, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-start space-x-3 bg-green-50 rounded-lg p-4"
                  >
                    <div className="text-green-600 mt-1">
                      {gradeBand === 'K-2' ? '🎯' : '➡️'}
                    </div>
                    <p className="text-gray-700 flex-1">{step}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <button
            onClick={() => navigate('/learners')}
            className={`
              ${styles.buttonSize}
              bg-white text-gray-900 font-bold rounded-lg shadow-lg
              hover:bg-gray-50 transition-all duration-200
              border-2 border-white/20
            `}
          >
            {gradeBand === 'K-2' ? '🏠 Go Home' : '👤 Back to Profile'}
          </button>

          <button
            onClick={() => navigate('/assessment/start?retake=true')}
            className={`
              ${styles.buttonSize}
              bg-blue-600 text-white font-bold rounded-lg shadow-lg
              hover:bg-blue-700 transition-all duration-200
            `}
          >
            {gradeBand === 'K-2' ? '🔄 Play Again?' : '🔄 Retake Assessment'}
          </button>

          <button
            onClick={() => {
              // TODO: Implement print/share functionality
              window.print()
            }}
            className={`
              ${styles.buttonSize}
              bg-purple-600 text-white font-bold rounded-lg shadow-lg
              hover:bg-purple-700 transition-all duration-200
            `}
          >
            {gradeBand === 'K-2' ? '🖨️ Print My Report' : '📄 Print Report'}
          </button>
        </motion.div>

        {/* Session Details (for 6-12 only) */}
        {gradeBand === '6-12' && session && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
            className="mt-8 bg-white/10 backdrop-blur-sm rounded-lg p-6 text-white/80 text-sm"
          >
            <h3 className="font-semibold mb-4">Session Details</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="font-medium">Started</div>
                <div>
                  {session.startedAt
                    ? new Date(session.startedAt).toLocaleString()
                    : 'N/A'}
                </div>
              </div>
              <div>
                <div className="font-medium">Completed</div>
                <div>
                  {session.completedAt
                    ? new Date(session.completedAt).toLocaleString()
                    : 'N/A'}
                </div>
              </div>
              <div>
                <div className="font-medium">Average Time</div>
                <div>
                  {Math.round(report.averageResponseTime / 1000)}s per question
                </div>
              </div>
              <div>
                <div className="font-medium">Session ID</div>
                <div className="font-mono text-xs">{session.id}</div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}
