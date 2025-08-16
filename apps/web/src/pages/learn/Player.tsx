import React, { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  lessonRegistryClient,
  type Lesson,
  type LearningSession,
} from '../../api/lessonRegistryClient'
import { inferenceClient, type ChatSession } from '../../api/inferenceClient'
import { eventCollectorClient } from '../../api/eventCollectorClient'
import { LessonPane } from '../../components/learn/LessonPane'
import { ChatPane } from '../../components/learn/ChatPane'
import { Toolbar } from '../../components/learn/Toolbar'
import { AudioControls } from '../../components/learn/AudioControls'

export const Player: React.FC = () => {
  const { lessonId } = useParams<{ lessonId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const learnerId = searchParams.get('learnerId') || 'default-learner'

  // Core state
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [learningSession, setLearningSession] =
    useState<LearningSession | null>(null)
  const [chatSession, setChatSession] = useState<ChatSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // UI state
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [volume, setVolume] = useState(1.0)
  const [currentSectionId, setCurrentSectionId] = useState<string | null>(null)
  const [currentContentId, setCurrentContentId] = useState<string | null>(null)

  // Game break state
  const [gameBreakActive, setGameBreakActive] = useState(false)
  const [gameBreakCountdown, setGameBreakCountdown] = useState<number>(0)
  const [timeUntilGameBreak, setTimeUntilGameBreak] = useState<number>(0)
  const [lastGameBreakTime, setLastGameBreakTime] = useState<number>(0)

  // Timers and refs
  const sessionStartTime = useRef<number>(Date.now())
  const gameBreakTimer = useRef<NodeJS.Timeout | null>(null)
  const progressTimer = useRef<NodeJS.Timeout | null>(null)
  const countdownTimer = useRef<NodeJS.Timeout | null>(null)

  // Initialize session
  useEffect(() => {
    if (!lessonId) {
      setError('No lesson ID provided')
      setLoading(false)
      return
    }

    initializeSession()
  }, [lessonId, learnerId])

  // Setup game break timer
  useEffect(() => {
    if (
      lesson?.gameBreakConfig?.enabled &&
      learningSession &&
      !gameBreakActive &&
      !isPaused
    ) {
      setupGameBreakTimer()
    }

    return () => {
      if (gameBreakTimer.current) {
        clearTimeout(gameBreakTimer.current)
      }
    }
  }, [lesson, learningSession, gameBreakActive, isPaused, lastGameBreakTime])

  // Progress tracking
  useEffect(() => {
    if (learningSession && isPlaying && !isPaused && !gameBreakActive) {
      progressTimer.current = setInterval(() => {
        updateProgress()
      }, 5000) // Update every 5 seconds

      return () => {
        if (progressTimer.current) {
          clearInterval(progressTimer.current)
        }
      }
    }
  }, [learningSession, isPlaying, isPaused, gameBreakActive])

  // Game break countdown
  useEffect(() => {
    if (gameBreakCountdown > 0) {
      countdownTimer.current = setInterval(() => {
        setGameBreakCountdown(prev => {
          if (prev <= 1) {
            endGameBreak()
            return 0
          }
          return prev - 1
        })
      }, 1000)

      return () => {
        if (countdownTimer.current) {
          clearInterval(countdownTimer.current)
        }
      }
    }
  }, [gameBreakCountdown])

  const initializeSession = async () => {
    try {
      setLoading(true)
      setError(null)

      // Load lesson data
      const lessonData = await lessonRegistryClient.getLesson(lessonId!)
      setLesson(lessonData)

      // Start learning session
      const session = await lessonRegistryClient.startLearningSession(
        learnerId,
        lessonId!
      )
      setLearningSession(session)

      // Initialize current position
      if (session.currentPosition) {
        setCurrentSectionId(session.currentPosition.sectionId)
        setCurrentContentId(session.currentPosition.contentId)
      } else if (lessonData.sections.length > 0) {
        const firstSection = lessonData.sections[0]
        const firstContent = firstSection.content[0]
        setCurrentSectionId(firstSection.id)
        setCurrentContentId(firstContent?.id || null)
      }

      // Start chat session
      const chatSessionData = await inferenceClient.startChatSession(
        learnerId,
        lessonId!
      )
      setChatSession(chatSessionData)

      // Track session start
      await eventCollectorClient.trackLessonStart(
        session.id,
        learnerId,
        lessonId!
      )

      // Set initial game break timer
      if (lessonData.gameBreakConfig?.enabled) {
        const intervalMs =
          lessonData.gameBreakConfig.intervalMinutes * 60 * 1000
        setTimeUntilGameBreak(intervalMs)
        setLastGameBreakTime(Date.now())
      }

      setIsPlaying(true)
    } catch (err) {
      console.error('Failed to initialize session:', err)
      setError('Failed to load lesson. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const setupGameBreakTimer = useCallback(() => {
    if (!lesson?.gameBreakConfig?.enabled || !learningSession) return

    const intervalMs = lesson.gameBreakConfig.intervalMinutes * 60 * 1000
    const timeSinceLastBreak = Date.now() - lastGameBreakTime
    const timeUntilBreak = Math.max(0, intervalMs - timeSinceLastBreak)

    setTimeUntilGameBreak(timeUntilBreak)

    if (timeUntilBreak > 0) {
      gameBreakTimer.current = setTimeout(() => {
        triggerGameBreak()
      }, timeUntilBreak)
    } else {
      triggerGameBreak()
    }
  }, [lesson, learningSession, lastGameBreakTime])

  const triggerGameBreak = async () => {
    if (!learningSession || !lesson?.gameBreakConfig) return

    try {
      setIsPlaying(false)
      setGameBreakActive(true)
      setGameBreakCountdown(lesson.gameBreakConfig.durationMinutes * 60)

      // Record game break event
      const gameBreakEvent = await lessonRegistryClient.triggerGameBreak(
        learningSession.id,
        lesson.gameBreakConfig.durationMinutes
      )

      // Track telemetry
      await eventCollectorClient.trackGameBreak(
        learningSession.id,
        learnerId,
        lesson.id,
        {
          gameBreakId: gameBreakEvent.id,
          durationMinutes: lesson.gameBreakConfig.durationMinutes,
          timeSpent: Date.now() - sessionStartTime.current,
          currentSection: currentSectionId,
          currentContent: currentContentId,
        }
      )

      // Update last game break time
      setLastGameBreakTime(Date.now())
    } catch (error) {
      console.error('Failed to trigger game break:', error)
    }
  }

  const endGameBreak = async () => {
    if (!learningSession || !gameBreakActive) return

    try {
      setGameBreakActive(false)
      setGameBreakCountdown(0)
      setIsPlaying(true)

      // Find the most recent game break and mark as completed
      const currentSession = await lessonRegistryClient.getLearningSession(
        learningSession.id
      )
      const lastGameBreak =
        currentSession.gameBreaks[currentSession.gameBreaks.length - 1]

      if (lastGameBreak) {
        await lessonRegistryClient.resumeFromGameBreak(
          learningSession.id,
          lastGameBreak.id
        )
      }

      // Track resumption
      await eventCollectorClient.sendEvent({
        sessionId: learningSession.id,
        learnerId,
        lessonId: lesson?.id,
        eventType: 'game_break_complete',
        data: {
          gameBreakId: lastGameBreak?.id,
          resumedAt: new Date().toISOString(),
        },
      })

      // Setup next game break
      if (lesson?.gameBreakConfig?.enabled) {
        setLastGameBreakTime(Date.now())
        setupGameBreakTimer()
      }
    } catch (error) {
      console.error('Failed to end game break:', error)
    }
  }

  const updateProgress = async () => {
    if (!learningSession || !currentSectionId || !currentContentId) return

    try {
      const currentTime = Date.now()
      const timeSpent = currentTime - sessionStartTime.current

      await lessonRegistryClient.updateSessionProgress(learningSession.id, {
        currentPosition: {
          sectionId: currentSectionId,
          contentId: currentContentId,
          timestamp: Date.now(),
        },
        totalTimeSpent: timeSpent,
      })

      // Record interaction
      await lessonRegistryClient.recordInteraction(learningSession.id, {
        type: 'view',
        contentId: currentContentId,
        timeSpent: 5000, // 5 seconds since last update
      })
    } catch (error) {
      console.error('Failed to update progress:', error)
    }
  }

  const handlePlay = () => {
    setIsPlaying(true)
    setIsPaused(false)
  }

  const handlePause = async () => {
    setIsPlaying(false)
    setIsPaused(true)

    if (learningSession) {
      await eventCollectorClient.sendEvent({
        sessionId: learningSession.id,
        learnerId,
        lessonId: lesson?.id,
        eventType: 'lesson_pause',
        data: {
          pausedAt: new Date().toISOString(),
          currentSection: currentSectionId,
          currentContent: currentContentId,
        },
      })
    }
  }

  const handleResume = async () => {
    setIsPlaying(true)
    setIsPaused(false)

    if (learningSession) {
      await eventCollectorClient.sendEvent({
        sessionId: learningSession.id,
        learnerId,
        lessonId: lesson?.id,
        eventType: 'lesson_resume',
        data: {
          resumedAt: new Date().toISOString(),
          currentSection: currentSectionId,
          currentContent: currentContentId,
        },
      })
    }
  }

  const handleVolumeChange = (newVolume: number) => {
    setVolume(newVolume)
  }

  const handleSectionChange = (sectionId: string, contentId?: string) => {
    setCurrentSectionId(sectionId)
    if (contentId) {
      setCurrentContentId(contentId)
    }
  }

  const handleToggleChat = () => {
    setIsChatOpen(!isChatOpen)
  }

  const handleEndSession = async () => {
    if (!learningSession) return

    try {
      const timeSpent = Date.now() - sessionStartTime.current

      await lessonRegistryClient.endLearningSession(learningSession.id)
      await eventCollectorClient.trackLessonEnd(
        learningSession.id,
        learnerId,
        lesson?.id || '',
        timeSpent
      )

      if (chatSession) {
        await inferenceClient.endChatSession(chatSession.id)
      }

      navigate('/learners')
    } catch (error) {
      console.error('Failed to end session:', error)
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (gameBreakTimer.current) clearTimeout(gameBreakTimer.current)
      if (progressTimer.current) clearInterval(progressTimer.current)
      if (countdownTimer.current) clearInterval(countdownTimer.current)
    }
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-xl text-gray-600">Loading lesson...</p>
        </div>
      </div>
    )
  }

  if (error || !lesson || !learningSession || !chatSession) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">
            Error Loading Lesson
          </h1>
          <p className="text-gray-600 mb-6">
            {error || 'Failed to load lesson data'}
          </p>
          <button
            onClick={() => navigate('/learners')}
            className="bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Toolbar */}
      <Toolbar
        lesson={lesson}
        session={learningSession}
        isPlaying={isPlaying}
        isPaused={isPaused}
        onPlay={handlePlay}
        onPause={handlePause}
        onResume={handleResume}
        onToggleChat={handleToggleChat}
        onEndSession={handleEndSession}
        isChatOpen={isChatOpen}
        timeUntilGameBreak={timeUntilGameBreak}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex">
        {/* Lesson Pane */}
        <div
          className={`transition-all duration-300 ${
            isChatOpen ? 'w-2/3' : 'w-full'
          }`}
        >
          <LessonPane
            lesson={lesson}
            currentSectionId={currentSectionId}
            currentContentId={currentContentId}
            isPlaying={isPlaying}
            volume={volume}
            onSectionChange={handleSectionChange}
            onInteraction={(type: string, element: string, data?: any) => {
              eventCollectorClient.trackInteraction(
                learningSession.id,
                learnerId,
                type,
                element,
                data
              )
            }}
          />
        </div>

        {/* Chat Pane */}
        <AnimatePresence>
          {isChatOpen && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: '33.333333%', opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              className="border-l border-gray-300 bg-white"
            >
              <ChatPane
                chatSession={chatSession}
                lesson={lesson}
                learningSession={learningSession}
                currentSectionId={currentSectionId}
                currentContentId={currentContentId}
                onChatInteraction={(
                  messageType: 'sent' | 'received',
                  data?: any
                ) => {
                  eventCollectorClient.trackChatInteraction(
                    learningSession.id,
                    learnerId,
                    lesson.id,
                    messageType,
                    data
                  )
                }}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Audio Controls */}
      <AudioControls
        isPlaying={isPlaying}
        volume={volume}
        onVolumeChange={handleVolumeChange}
        lesson={lesson}
      />

      {/* Game Break Overlay */}
      <AnimatePresence>
        {gameBreakActive && (
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
              <div className="text-6xl mb-4">🎮</div>
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Game Break Time!
              </h2>
              <p className="text-gray-600 mb-6">
                Take a break and play a quick game. You'll be back to learning
                in:
              </p>

              <div className="text-4xl font-bold text-blue-600 mb-6">
                {Math.floor(gameBreakCountdown / 60)}:
                {(gameBreakCountdown % 60).toString().padStart(2, '0')}
              </div>

              <div className="space-y-4">
                <button
                  onClick={() => {
                    // TODO: Launch selected game
                    console.log('Launch game')
                  }}
                  className="w-full bg-green-600 text-white font-bold py-3 px-6 rounded-lg hover:bg-green-700 transition-colors"
                >
                  🎯 Play Quick Game
                </button>

                <button
                  onClick={endGameBreak}
                  className="w-full bg-gray-300 text-gray-700 font-bold py-2 px-6 rounded-lg hover:bg-gray-400 transition-colors"
                >
                  Skip Break
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
