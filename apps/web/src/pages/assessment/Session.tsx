import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  assessmentClient,
  type AssessmentSession,
  type AssessmentItem,
  type SubmitResponseRequest,
} from '../../api/assessmentClient'

export const Session: React.FC = () => {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const sessionId = searchParams.get('sessionId')

  // State management
  const [session, setSession] = useState<AssessmentSession | null>(null)
  const [currentItem, setCurrentItem] = useState<AssessmentItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null)
  const [isPaused, setIsPaused] = useState(false)

  // Audio state for K-2 grade band
  const [audioPlaying, setAudioPlaying] = useState(false)
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(
    null
  )

  // Get grade band for adaptive UI
  const gradeBand = session?.gradeBand || 'K-2'
  const adaptiveSettings = session?.adaptiveSettings || {
    audioFirst: false,
    largeTargets: false,
    simplifiedInterface: false,
  }

  // Initialize session and first item
  useEffect(() => {
    if (!sessionId) {
      setError('No session ID provided')
      setLoading(false)
      return
    }

    loadSession()
  }, [sessionId])

  // Timer effect
  useEffect(() => {
    if (
      !session?.adaptiveSettings?.timeLimit ||
      isPaused ||
      timeRemaining === null
    )
      return

    const timer = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev === null || prev <= 1) {
          handleTimeUp()
          return null
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [session, isPaused, timeRemaining])

  // Auto-save effect
  useEffect(() => {
    if (!session || isPaused) return

    const interval = setInterval(() => {
      autoSaveSession()
    }, 30000) // Auto-save every 30 seconds

    return () => {
      clearInterval(interval)
    }
  }, [session, isPaused])

  // Audio cleanup
  useEffect(() => {
    return () => {
      if (audioElement) {
        audioElement.pause()
        audioElement.src = ''
      }
    }
  }, [audioElement])

  const loadSession = async () => {
    try {
      setLoading(true)
      setError(null)

      // Get session details first
      const sessionData = await assessmentClient.getSession(sessionId!)
      setSession(sessionData)

      // Get current item
      const nextItemResponse = await assessmentClient.getNextItem(sessionId!)
      if (nextItemResponse.item) {
        setCurrentItem(nextItemResponse.item)

        // Set initial time if there's a time limit from adaptive settings
        if (sessionData.adaptiveSettings.timeLimit) {
          setTimeRemaining(sessionData.adaptiveSettings.timeLimit)
        }

        // Auto-play audio for K-2 if enabled
        if (
          sessionData.gradeBand === 'K-2' &&
          sessionData.adaptiveSettings.audioFirst &&
          nextItemResponse.item.audioUrl
        ) {
          playAudio(nextItemResponse.item.audioUrl)
        }
      } else if (nextItemResponse.isComplete) {
        // Assessment is already complete
        navigate(`/assessment/report?sessionId=${sessionId}`)
        return
      }
    } catch (err) {
      console.error('Error loading session:', err)
      setError('Failed to load assessment session')
    } finally {
      setLoading(false)
    }
  }

  const playAudio = (audioUrl: string) => {
    if (audioElement) {
      audioElement.pause()
    }

    const audio = new Audio(audioUrl)
    audio.onplay = () => setAudioPlaying(true)
    audio.onended = () => setAudioPlaying(false)
    audio.onerror = () => {
      setAudioPlaying(false)
      console.error('Error playing audio')
    }

    setAudioElement(audio)
    audio.play().catch(console.error)
  }

  const handleSubmitResponse = async (response: any) => {
    if (!currentItem || !session) return

    try {
      setSubmitting(true)
      setError(null)

      const timeSpent =
        session.adaptiveSettings.timeLimit && timeRemaining !== null
          ? (session.adaptiveSettings.timeLimit - timeRemaining) * 1000 // Convert to milliseconds
          : 0

      const request: SubmitResponseRequest = {
        sessionId: session.id,
        itemId: currentItem.id,
        response: response.value,
        timeSpent,
        attempts: 1, // For now, assume single attempt
      }

      const nextItemResponse =
        await assessmentClient.submitResponseAndGetNext(request)

      if (nextItemResponse.item) {
        // Continue with next item
        setCurrentItem(nextItemResponse.item)
        if (session.adaptiveSettings.timeLimit) {
          setTimeRemaining(session.adaptiveSettings.timeLimit)
        } else {
          setTimeRemaining(null)
        }

        // Auto-play audio for K-2 if enabled
        if (
          gradeBand === 'K-2' &&
          adaptiveSettings.audioFirst &&
          nextItemResponse.item.audioUrl
        ) {
          playAudio(nextItemResponse.item.audioUrl)
        }
      } else {
        // Assessment complete
        await assessmentClient.completeAssessment(session.id)
        navigate(`/assessment/report?sessionId=${session.id}`)
      }
    } catch (err) {
      console.error('Error submitting response:', err)
      setError('Failed to submit response. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleTimeUp = useCallback(() => {
    if (!currentItem) return

    // Auto-submit with timeout indicator
    handleSubmitResponse({ type: 'timeout', value: null })
  }, [currentItem])

  const handlePauseResume = async () => {
    if (!session) return

    try {
      if (isPaused) {
        await assessmentClient.resumeSession(session.id)
        setIsPaused(false)
      } else {
        await assessmentClient.pauseSession(session.id)
        setIsPaused(true)
      }
    } catch (err) {
      console.error('Error pausing/resuming session:', err)
      setError('Failed to pause/resume session')
    }
  }

  const autoSaveSession = async () => {
    if (!session) return

    try {
      await assessmentClient.autoSaveSession(session.id, {
        currentItemIndex: session.currentItemIndex,
        status: session.status,
      })
    } catch (err) {
      console.error('Auto-save failed:', err)
      // Don't show error to user for auto-save failures
    }
  }

  // Grade band specific styling
  const getGradeBandStyles = () => {
    switch (gradeBand) {
      case 'K-2':
        return {
          buttonSize: adaptiveSettings.largeTargets
            ? 'text-2xl px-8 py-6 min-h-[80px]'
            : 'text-xl px-6 py-4',
          fontSize: 'text-2xl',
          spacing: 'space-y-6',
          colors: 'bg-gradient-to-br from-blue-400 to-purple-500',
          cardPadding: 'p-8',
        }
      case '3-5':
        return {
          buttonSize: 'text-lg px-6 py-4',
          fontSize: 'text-xl',
          spacing: 'space-y-5',
          colors: 'bg-gradient-to-br from-green-400 to-blue-500',
          cardPadding: 'p-6',
        }
      case '6-12':
        return {
          buttonSize: 'text-base px-4 py-3',
          fontSize: 'text-lg',
          spacing: 'space-y-4',
          colors: 'bg-gradient-to-br from-purple-400 to-pink-500',
          cardPadding: 'p-6',
        }
    }
  }

  const styles = getGradeBandStyles()

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-xl text-gray-600">
            {gradeBand === 'K-2'
              ? 'Getting your game ready...'
              : 'Loading assessment...'}
          </p>
        </div>
      </div>
    )
  }

  if (error && !session) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">
            Assessment Error
          </h1>
          <p className="text-gray-600 mb-6">{error}</p>
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

  if (!currentItem) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            {gradeBand === 'K-2' ? '🎉 Great Job!' : 'Assessment Complete'}
          </h1>
          <p className="text-gray-600 mb-6">
            {gradeBand === 'K-2'
              ? "You finished all the games! Let's see how you did!"
              : 'You have completed all assessment items.'}
          </p>
          <button
            onClick={() =>
              navigate(`/assessment/report?sessionId=${session?.id}`)
            }
            className="bg-green-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-green-700 transition-colors"
          >
            {gradeBand === 'K-2' ? '🏆 See Results' : 'View Report'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className={`min-h-screen ${styles.colors} p-4`}>
      {/* Header with progress and controls */}
      <div className="max-w-4xl mx-auto mb-6">
        <div className="bg-white rounded-lg shadow-lg p-4 flex items-center justify-between">
          {/* Progress indicator */}
          <div className="flex items-center space-x-4">
            <div className={`${styles.fontSize} font-bold text-gray-900`}>
              {gradeBand === 'K-2' ? '🌟' : '📝'} Question{' '}
              {session?.currentItemIndex || 1}
            </div>
            {session?.totalItems && (
              <div className="flex items-center space-x-2">
                <div className="bg-gray-200 rounded-full h-2 w-32">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${((session.currentItemIndex || 1) / session.totalItems) * 100}%`,
                    }}
                  ></div>
                </div>
                <span className="text-sm text-gray-600">
                  {session.currentItemIndex || 1} of {session.totalItems}
                </span>
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center space-x-4">
            {/* Timer */}
            {timeRemaining !== null && (
              <div
                className={`flex items-center space-x-2 ${
                  timeRemaining < 30 ? 'text-red-600' : 'text-gray-600'
                }`}
              >
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="font-mono">
                  {Math.floor(timeRemaining / 60)}:
                  {(timeRemaining % 60).toString().padStart(2, '0')}
                </span>
              </div>
            )}

            {/* Audio button for K-2 */}
            {gradeBand === 'K-2' && currentItem.audioUrl && (
              <button
                onClick={() => playAudio(currentItem.audioUrl!)}
                disabled={audioPlaying}
                className="flex items-center space-x-2 bg-blue-100 text-blue-800 px-3 py-2 rounded-lg hover:bg-blue-200 transition-colors disabled:opacity-50"
              >
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.816L4.89 14H2a1 1 0 01-1-1V7a1 1 0 011-1h2.89l3.493-2.816z"
                    clipRule="evenodd"
                  />
                  <path d="M12.293 7.293a1 1 0 011.414 0L15 8.586l1.293-1.293a1 1 0 111.414 1.414L16.414 10l1.293 1.293a1 1 0 01-1.414 1.414L15 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L13.586 10l-1.293-1.293a1 1 0 010-1.414z" />
                </svg>
                <span>{audioPlaying ? 'Playing...' : '🔊 Listen'}</span>
              </button>
            )}

            {/* Pause/Resume button */}
            <button
              onClick={handlePauseResume}
              className="flex items-center space-x-2 bg-yellow-100 text-yellow-800 px-3 py-2 rounded-lg hover:bg-yellow-200 transition-colors"
            >
              {isPaused ? (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>{gradeBand === 'K-2' ? 'Continue' : 'Resume'}</span>
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <span>{gradeBand === 'K-2' ? 'Take a Break' : 'Pause'}</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Pause overlay */}
      <AnimatePresence>
        {isPaused && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          >
            <motion.div
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.9 }}
              className="bg-white rounded-xl shadow-2xl p-8 max-w-md w-full mx-4 text-center"
            >
              <h2
                className={`font-bold text-gray-900 mb-4 ${
                  gradeBand === 'K-2' ? 'text-2xl' : 'text-xl'
                }`}
              >
                {gradeBand === 'K-2'
                  ? '⏸️ Taking a Break'
                  : '⏸️ Assessment Paused'}
              </h2>
              <p className="text-gray-600 mb-6">
                {gradeBand === 'K-2'
                  ? "Take your time! Click continue when you're ready to keep playing."
                  : "Your progress has been saved. Click resume when you're ready to continue."}
              </p>
              <button
                onClick={handlePauseResume}
                className={`${styles.buttonSize} bg-blue-600 text-white font-bold rounded-lg hover:bg-blue-700 transition-colors`}
              >
                {gradeBand === 'K-2'
                  ? '▶️ Continue Playing'
                  : '▶️ Resume Assessment'}
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main assessment content */}
      <div className="max-w-4xl mx-auto">
        <motion.div
          key={currentItem.id}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          className={`bg-white rounded-xl shadow-2xl ${styles.cardPadding}`}
        >
          {/* Item Renderer Component will go here */}
          <div className="text-center">
            <h2 className={`font-bold text-gray-900 mb-6 ${styles.fontSize}`}>
              {currentItem.question}
            </h2>

            {/* Image if present */}
            {currentItem.imageUrl && (
              <div className="mb-6">
                <img
                  src={currentItem.imageUrl}
                  alt="Question illustration"
                  className="max-w-full h-auto mx-auto rounded-lg shadow-md"
                  style={{ maxHeight: '300px' }}
                />
              </div>
            )}

            {/* Options rendering based on item type */}
            <div className={`${styles.spacing}`}>
              {currentItem.type === 'multiple-choice' &&
                currentItem.options &&
                currentItem.options.length > 2 && (
                  <div
                    className={`grid gap-4 ${
                      gradeBand === 'K-2'
                        ? 'grid-cols-1'
                        : currentItem.options.length <= 2
                          ? 'grid-cols-2'
                          : 'grid-cols-2 md:grid-cols-3'
                    }`}
                  >
                    {currentItem.options.map((option, index) => (
                      <motion.button
                        key={index}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() =>
                          handleSubmitResponse({
                            type: 'multiple-choice',
                            value: option.id,
                          })
                        }
                        disabled={submitting}
                        className={`
                        ${styles.buttonSize}
                        bg-blue-100 text-blue-900 border-2 border-blue-200
                        hover:bg-blue-200 hover:border-blue-300
                        disabled:opacity-50 disabled:cursor-not-allowed
                        rounded-lg transition-all duration-200
                        ${adaptiveSettings.largeTargets ? 'min-h-[100px]' : 'min-h-[60px]'}
                        flex items-center justify-center text-center
                      `}
                      >
                        {gradeBand === 'K-2' && (
                          <span className="text-2xl mr-2">
                            {String.fromCharCode(65 + index)} {/* A, B, C, D */}
                          </span>
                        )}
                        {option.text}
                      </motion.button>
                    ))}
                  </div>
                )}

              {/* True/False questions can be handled as multiple choice with two options */}
              {currentItem.type === 'multiple-choice' &&
                currentItem.options &&
                currentItem.options.length === 2 && (
                  <div className={`grid grid-cols-2 gap-6 max-w-md mx-auto`}>
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() =>
                        handleSubmitResponse({
                          type: 'multiple-choice',
                          value: currentItem.options![0].id,
                        })
                      }
                      disabled={submitting}
                      className={`
                      ${styles.buttonSize}
                      bg-green-100 text-green-900 border-2 border-green-200
                      hover:bg-green-200 hover:border-green-300
                      disabled:opacity-50 disabled:cursor-not-allowed
                      rounded-lg transition-all duration-200
                      ${adaptiveSettings.largeTargets ? 'min-h-[100px]' : 'min-h-[80px]'}
                      flex items-center justify-center
                    `}
                    >
                      {gradeBand === 'K-2' ? '✅' : ''}{' '}
                      {currentItem.options[0].text}
                    </motion.button>

                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() =>
                        handleSubmitResponse({
                          type: 'multiple-choice',
                          value: currentItem.options![1].id,
                        })
                      }
                      disabled={submitting}
                      className={`
                      ${styles.buttonSize}
                      bg-red-100 text-red-900 border-2 border-red-200
                      hover:bg-red-200 hover:border-red-300
                      disabled:opacity-50 disabled:cursor-not-allowed
                      rounded-lg transition-all duration-200
                      ${adaptiveSettings.largeTargets ? 'min-h-[100px]' : 'min-h-[80px]'}
                      flex items-center justify-center
                    `}
                    >
                      {gradeBand === 'K-2' ? '❌' : ''}{' '}
                      {currentItem.options[1].text}
                    </motion.button>
                  </div>
                )}

              {currentItem.type === 'text-input' && (
                <div className="max-w-lg mx-auto">
                  <textarea
                    placeholder={
                      gradeBand === 'K-2'
                        ? 'Type your answer here...'
                        : 'Enter your answer...'
                    }
                    className={`
                      w-full p-4 border-2 border-gray-300 rounded-lg 
                      focus:border-blue-500 focus:ring-blue-500
                      ${styles.fontSize}
                      ${gradeBand === 'K-2' ? 'min-h-[120px]' : 'min-h-[100px]'}
                    `}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && e.ctrlKey) {
                        const value = (e.target as HTMLTextAreaElement).value
                        if (value.trim()) {
                          handleSubmitResponse({
                            type: 'text-input',
                            value: value.trim(),
                          })
                        }
                      }
                    }}
                  />
                  <div className="mt-4 text-center">
                    <button
                      onClick={e => {
                        const textarea =
                          e.currentTarget.parentElement?.querySelector(
                            'textarea'
                          ) as HTMLTextAreaElement
                        const value = textarea?.value
                        if (value?.trim()) {
                          handleSubmitResponse({
                            type: 'text-input',
                            value: value.trim(),
                          })
                        }
                      }}
                      disabled={submitting}
                      className={`
                        ${styles.buttonSize}
                        bg-blue-600 text-white font-bold rounded-lg
                        hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                        transition-all duration-200
                      `}
                    >
                      {submitting ? (
                        <div className="flex items-center space-x-2">
                          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                          <span>Submitting...</span>
                        </div>
                      ) : gradeBand === 'K-2' ? (
                        '📤 Submit Answer'
                      ) : (
                        '➤ Submit'
                      )}
                    </button>
                  </div>
                  {gradeBand !== 'K-2' && (
                    <p className="text-sm text-gray-500 mt-2 text-center">
                      Press Ctrl+Enter to submit quickly
                    </p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Error display */}
          {error && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-6 bg-red-50 border border-red-200 rounded-lg p-4"
            >
              <p className="text-red-700 text-center">{error}</p>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  )
}
