import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  assessmentClient,
  type StartAssessmentRequest,
} from '../../api/assessmentClient'

interface AssessmentStartProps {
  learnerId?: string
}

export const Start: React.FC<AssessmentStartProps> = ({ learnerId }) => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Get params from URL or props
  const learnerIdFromParams = searchParams.get('learnerId') || learnerId
  const gradeBand =
    (searchParams.get('gradeBand') as 'K-2' | '3-5' | '6-12') || 'K-2'

  // Adaptive settings based on grade band
  const [adaptiveSettings, setAdaptiveSettings] = useState({
    audioFirst: gradeBand === 'K-2', // Default to audio-first for K-2
    largeTargets: gradeBand === 'K-2', // Large touch targets for K-2
    simplifiedInterface: gradeBand === 'K-2' || gradeBand === '3-5', // Simplified for K-5
    timeLimit: gradeBand === 'K-2' ? undefined : 60, // No time limit for K-2
  })

  // Auto-start if we have all required params
  useEffect(() => {
    const autoStart = searchParams.get('autoStart')
    if (autoStart === 'true' && learnerIdFromParams && gradeBand) {
      handleStartAssessment()
    }
  }, [learnerIdFromParams, gradeBand, searchParams])

  const handleStartAssessment = async () => {
    if (!learnerIdFromParams) {
      setError('Learner ID is required to start assessment')
      return
    }

    try {
      setLoading(true)
      setError(null)

      const request: StartAssessmentRequest = {
        learnerId: learnerIdFromParams,
        type: 'baseline',
        gradeBand,
        adaptiveSettings,
      }

      const session = await assessmentClient.startAssessment(request)

      // Navigate to session page
      navigate(`/assessment/session?sessionId=${session.id}`)
    } catch (err) {
      console.error('Error starting assessment:', err)
      setError('Failed to start assessment. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleSettingChange = (
    setting: keyof typeof adaptiveSettings,
    value: boolean | number | undefined
  ) => {
    setAdaptiveSettings(prev => ({
      ...prev,
      [setting]: value,
    }))
  }

  // Grade band specific styling
  const getGradeBandStyles = () => {
    switch (gradeBand) {
      case 'K-2':
        return {
          buttonSize: 'text-2xl px-8 py-6',
          fontSize: 'text-xl',
          spacing: 'space-y-8',
          colors: 'bg-gradient-to-br from-blue-400 to-purple-500',
        }
      case '3-5':
        return {
          buttonSize: 'text-xl px-6 py-4',
          fontSize: 'text-lg',
          spacing: 'space-y-6',
          colors: 'bg-gradient-to-br from-green-400 to-blue-500',
        }
      case '6-12':
        return {
          buttonSize: 'text-lg px-4 py-3',
          fontSize: 'text-base',
          spacing: 'space-y-4',
          colors: 'bg-gradient-to-br from-purple-400 to-pink-500',
        }
    }
  }

  const styles = getGradeBandStyles()

  if (!learnerIdFromParams) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Assessment Setup Required
          </h1>
          <p className="text-gray-600 mb-4">
            A learner ID is required to start the assessment. Please ensure
            you're accessing this page through the proper navigation flow.
          </p>
          <button
            onClick={() => navigate('/learners')}
            className="w-full bg-blue-600 text-white font-semibold py-3 px-4 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Go to Learners
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`min-h-screen ${styles.colors} flex items-center justify-center p-4`}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white rounded-xl shadow-2xl p-8 max-w-2xl w-full"
      >
        <div className={`text-center ${styles.spacing}`}>
          {/* Title - Grade appropriate */}
          <h1
            className={`font-bold text-gray-900 mb-4 ${
              gradeBand === 'K-2'
                ? 'text-3xl'
                : gradeBand === '3-5'
                  ? 'text-2xl'
                  : 'text-xl'
            }`}
          >
            {gradeBand === 'K-2' && "🌟 Let's Play and Learn! 🌟"}
            {gradeBand === '3-5' && '🎯 Ready for Your Assessment? 🎯'}
            {gradeBand === '6-12' && '📝 Baseline Assessment'}
          </h1>

          {/* Description - Grade appropriate */}
          <p className={`text-gray-600 mb-8 ${styles.fontSize}`}>
            {gradeBand === 'K-2' &&
              "We're going to play some fun games to see what you know! There are no wrong answers - just do your best!"}
            {gradeBand === '3-5' &&
              'This assessment helps us understand what you know so we can create the best learning experience for you.'}
            {gradeBand === '6-12' &&
              'This baseline assessment will help us understand your current knowledge level and create a personalized learning path.'}
          </p>

          {/* Adaptive Settings */}
          <div className="bg-gray-50 rounded-lg p-6 mb-8">
            <h2
              className={`font-semibold text-gray-900 mb-4 ${
                gradeBand === 'K-2' ? 'text-xl' : 'text-lg'
              }`}
            >
              {gradeBand === 'K-2'
                ? '🎮 How would you like to play?'
                : '⚙️ Assessment Preferences'}
            </h2>

            <div className={`${styles.spacing}`}>
              {/* Audio First Option */}
              <label className="flex items-center justify-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={adaptiveSettings.audioFirst}
                  onChange={e =>
                    handleSettingChange('audioFirst', e.target.checked)
                  }
                  className={`${gradeBand === 'K-2' ? 'w-6 h-6' : 'w-5 h-5'} text-blue-600 rounded focus:ring-blue-500`}
                />
                <span className={`${styles.fontSize} text-gray-700`}>
                  {gradeBand === 'K-2'
                    ? '🔊 Listen to questions first'
                    : '🎧 Audio-first mode'}
                </span>
              </label>

              {/* Large Targets (K-2 only) */}
              {gradeBand === 'K-2' && (
                <label className="flex items-center justify-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={adaptiveSettings.largeTargets}
                    onChange={e =>
                      handleSettingChange('largeTargets', e.target.checked)
                    }
                    className="w-6 h-6 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <span className={`${styles.fontSize} text-gray-700`}>
                    🎯 Big buttons (easier to tap)
                  </span>
                </label>
              )}

              {/* Simplified Interface */}
              {(gradeBand === 'K-2' || gradeBand === '3-5') && (
                <label className="flex items-center justify-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={adaptiveSettings.simplifiedInterface}
                    onChange={e =>
                      handleSettingChange(
                        'simplifiedInterface',
                        e.target.checked
                      )
                    }
                    className={`${gradeBand === 'K-2' ? 'w-6 h-6' : 'w-5 h-5'} text-blue-600 rounded focus:ring-blue-500`}
                  />
                  <span className={`${styles.fontSize} text-gray-700`}>
                    {gradeBand === 'K-2'
                      ? '🌈 Simple, colorful design'
                      : '🎨 Simplified interface'}
                  </span>
                </label>
              )}

              {/* Time Limit (6-12 only) */}
              {gradeBand === '6-12' && (
                <div className="flex items-center justify-center space-x-3">
                  <label className="text-gray-700">
                    ⏱️ Time limit per question:
                  </label>
                  <select
                    value={adaptiveSettings.timeLimit || 60}
                    onChange={e =>
                      handleSettingChange('timeLimit', parseInt(e.target.value))
                    }
                    className="border border-gray-300 rounded px-3 py-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value={60}>1 minute</option>
                    <option value={90}>1.5 minutes</option>
                    <option value={120}>2 minutes</option>
                    <option value={0}>No limit</option>
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6"
            >
              <p className="text-red-700">{error}</p>
            </motion.div>
          )}

          {/* Start Button */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleStartAssessment}
            disabled={loading}
            className={`
              ${styles.buttonSize} 
              bg-gradient-to-r from-blue-500 to-purple-600 
              text-white font-bold rounded-xl shadow-lg 
              hover:from-blue-600 hover:to-purple-700 
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-all duration-200
              ${adaptiveSettings.largeTargets ? 'min-h-[80px]' : 'min-h-[60px]'}
            `}
          >
            {loading ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                <span>Starting...</span>
              </div>
            ) : (
              <>
                {gradeBand === 'K-2' && "🚀 Let's Start Playing!"}
                {gradeBand === '3-5' && '🎯 Begin Assessment'}
                {gradeBand === '6-12' && '📝 Start Assessment'}
              </>
            )}
          </motion.button>

          {/* Help Text */}
          <p
            className={`text-gray-500 mt-4 ${
              gradeBand === 'K-2' ? 'text-lg' : 'text-sm'
            }`}
          >
            {gradeBand === 'K-2'
              ? 'Ask a grown-up if you need help! 👨‍👩‍👧‍👦'
              : 'Take your time and do your best!'}
          </p>
        </div>
      </motion.div>
    </div>
  )
}
