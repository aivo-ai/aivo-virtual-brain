import React, { useState, useEffect, useRef } from 'react'
import { useParams, useSearchParams, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  gameClient,
  type GameManifest,
  type GameSession,
  type GameScene,
  type GameProgress,
  type PerformanceMetrics,
  type GameEvent,
} from '../../api/gameClient'
import { CanvasStage } from '../../components/game/CanvasStage.tsx'
import { Hud } from '../../components/game/Hud.tsx'
import { ResultSheet } from '../../components/game/ResultSheet.tsx'

export const Play: React.FC = () => {
  const { gameId } = useParams<{ gameId: string }>()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const learnerId = searchParams.get('learnerId') || 'default-learner'

  // Core state
  const [gameManifest, setGameManifest] = useState<GameManifest | null>(null)
  const [gameSession, setGameSession] = useState<GameSession | null>(null)
  const [currentScene, setCurrentScene] = useState<GameScene | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Game state
  const [gameStarted, setGameStarted] = useState(false)
  const [gameCompleted, setGameCompleted] = useState(false)
  const [gamePaused, setGamePaused] = useState(false)
  const [gameProgress, setGameProgress] = useState<GameProgress>({
    current_scene_id: '',
    completed_scenes: [],
    current_score: 0,
    interactions_completed: 0,
    hints_used: 0,
    mistakes_made: 0,
    time_spent_seconds: 0,
  })

  // Performance tracking
  const [performanceMetrics, setPerformanceMetrics] =
    useState<PerformanceMetrics>({
      accuracy_percentage: 100,
      speed_score: 0,
      consistency_score: 100,
      learning_efficiency: 0,
      engagement_level: 100,
      completion_rate: 0,
      retry_attempts: 0,
      help_requests: 0,
    })

  // Timing and controls
  const [timeRemaining, setTimeRemaining] = useState<number>(0)
  const [elapsedTime, setElapsedTime] = useState<number>(0)
  const gameStartTime = useRef<number | null>(null)
  const pauseStartTime = useRef<number | null>(null)
  const totalPauseTime = useRef<number>(0)
  const gameTimer = useRef<NodeJS.Timeout | null>(null)
  const progressSaveTimer = useRef<NodeJS.Timeout | null>(null)

  // Initialize game
  useEffect(() => {
    if (!gameId) {
      setError('No game ID provided')
      setLoading(false)
      return
    }

    initializeGame()
  }, [gameId, learnerId])

  // Keyboard controls
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      // Only handle if keyboard navigation is enabled
      if (!gameManifest?.game_rules?.keyboard_navigation) return

      switch (event.key) {
        case ' ': // Spacebar - pause/resume
          event.preventDefault()
          handlePauseResume()
          break
        case 'Escape': // ESC - pause game
          event.preventDefault()
          if (!gamePaused && gameStarted && !gameCompleted) {
            handlePause()
          }
          break
        case 'h': // H - request hint
        case 'H':
          if (event.ctrlKey) {
            event.preventDefault()
            handleHintRequest()
          }
          break
        case 'r': // R - restart scene
        case 'R':
          if (event.ctrlKey && event.shiftKey) {
            event.preventDefault()
            handleSceneRestart()
          }
          break
      }
    }

    if (gameStarted && !gameCompleted) {
      window.addEventListener('keydown', handleKeyPress)
      return () => window.removeEventListener('keydown', handleKeyPress)
    }
  }, [gameStarted, gameCompleted, gamePaused, gameManifest])

  // Game timer
  useEffect(() => {
    if (gameStarted && !gamePaused && !gameCompleted && timeRemaining > 0) {
      gameTimer.current = setInterval(() => {
        setElapsedTime(prev => {
          const newElapsed = prev + 1
          setTimeRemaining(
            Math.max(
              0,
              (gameManifest?.target_duration_minutes || 0) * 60 - newElapsed
            )
          )

          // Auto-complete if time runs out
          if (newElapsed >= (gameManifest?.target_duration_minutes || 0) * 60) {
            handleTimeExpired()
          }

          return newElapsed
        })

        // Update progress periodically
        setGameProgress(prev => ({
          ...prev,
          time_spent_seconds: prev.time_spent_seconds + 1,
        }))
      }, 1000)

      return () => {
        if (gameTimer.current) {
          clearInterval(gameTimer.current)
        }
      }
    }
  }, [gameStarted, gamePaused, gameCompleted, timeRemaining, gameManifest])

  // Auto-save progress
  useEffect(() => {
    if (gameSession && gameStarted && !gameCompleted) {
      progressSaveTimer.current = setInterval(() => {
        saveProgress()
      }, 10000) // Save every 10 seconds

      return () => {
        if (progressSaveTimer.current) {
          clearInterval(progressSaveTimer.current)
        }
      }
    }
  }, [gameSession, gameStarted, gameCompleted])

  const initializeGame = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch game manifest
      const manifest = await gameClient.getGameManifest(gameId!)
      setGameManifest(manifest)

      // Validate game is ready
      if (manifest.status !== 'ready') {
        throw new Error(`Game is not ready. Current status: ${manifest.status}`)
      }

      // Check if game has expired
      if (manifest.expires_at && new Date(manifest.expires_at) < new Date()) {
        throw new Error('Game has expired. Please generate a new game.')
      }

      // Create game session
      const session = await gameClient.createGameSession(
        gameId!,
        learnerId,
        manifest.target_duration_minutes
      )
      setGameSession(session)

      // Set initial scene
      const firstScene =
        manifest.game_scenes.find(scene => scene.type === 'intro') ||
        manifest.game_scenes[0]
      if (firstScene) {
        setCurrentScene(firstScene)
        setGameProgress(prev => ({
          ...prev,
          current_scene_id: firstScene.id,
        }))
      }

      // Initialize timing
      setTimeRemaining(manifest.target_duration_minutes * 60)

      setLoading(false)
    } catch (err) {
      console.error('Failed to initialize game:', err)
      setError(err instanceof Error ? err.message : 'Failed to load game')
      setLoading(false)
    }
  }

  const handleStartGame = async () => {
    if (!gameSession || !currentScene) return

    try {
      setGameStarted(true)
      gameStartTime.current = Date.now()

      // Send game started event
      await sendGameEvent('GAME_STARTED', {
        scene_id: currentScene.id,
        timestamp: new Date().toISOString(),
      })

      // Update session status
      await gameClient.updateGameSession(gameSession.id, {
        status: 'in_progress',
        started_at: new Date().toISOString(),
      })
    } catch (err) {
      console.error('Failed to start game:', err)
      setError('Failed to start game')
    }
  }

  const handlePauseResume = () => {
    if (gamePaused) {
      handleResume()
    } else {
      handlePause()
    }
  }

  const handlePause = async () => {
    if (!gameSession || gamePaused) return

    try {
      setGamePaused(true)
      pauseStartTime.current = Date.now()

      // Send pause event
      await sendGameEvent('GAME_PAUSED', {
        scene_id: currentScene?.id,
        elapsed_time: elapsedTime,
        timestamp: new Date().toISOString(),
      })

      // Update session
      await gameClient.pauseGame(gameSession.id)
    } catch (err) {
      console.error('Failed to pause game:', err)
    }
  }

  const handleResume = async () => {
    if (!gameSession || !gamePaused) return

    try {
      const pauseDuration = pauseStartTime.current
        ? Math.floor((Date.now() - pauseStartTime.current) / 1000)
        : 0

      totalPauseTime.current += pauseDuration
      setGamePaused(false)
      pauseStartTime.current = null

      // Send resume event
      await sendGameEvent('GAME_RESUMED', {
        scene_id: currentScene?.id,
        pause_duration: pauseDuration,
        timestamp: new Date().toISOString(),
      })

      // Update session
      await gameClient.resumeGame(gameSession.id, pauseDuration)
    } catch (err) {
      console.error('Failed to resume game:', err)
    }
  }

  const handleSceneComplete = async (sceneId: string, sceneResults: any) => {
    if (!gameSession || !gameManifest) return

    try {
      // Update progress
      const newProgress = {
        ...gameProgress,
        completed_scenes: [...gameProgress.completed_scenes, sceneId],
        current_score: sceneResults.score || gameProgress.current_score,
        interactions_completed:
          gameProgress.interactions_completed +
          (sceneResults.interactions || 0),
      }
      setGameProgress(newProgress)

      // Update performance metrics
      const newMetrics = {
        ...performanceMetrics,
        accuracy_percentage:
          sceneResults.accuracy || performanceMetrics.accuracy_percentage,
        completion_rate:
          (newProgress.completed_scenes.length /
            gameManifest.game_scenes.length) *
          100,
      }
      setPerformanceMetrics(newMetrics)

      // Send scene completion event
      await sendGameEvent('SCENE_COMPLETED', {
        scene_id: sceneId,
        results: sceneResults,
        progress: newProgress,
      })

      // Find next scene
      const currentSceneIndex = gameManifest.game_scenes.findIndex(
        s => s.id === sceneId
      )
      const nextScene = gameManifest.game_scenes[currentSceneIndex + 1]

      if (nextScene) {
        // Move to next scene
        setCurrentScene(nextScene)
        setGameProgress(prev => ({
          ...prev,
          current_scene_id: nextScene.id,
        }))
      } else {
        // Game completed
        await handleGameComplete()
      }
    } catch (err) {
      console.error('Failed to complete scene:', err)
    }
  }

  const handleGameComplete = async () => {
    if (!gameSession) return

    try {
      setGameCompleted(true)
      const endTime = Date.now()
      const totalDuration = gameStartTime.current
        ? Math.floor(
            (endTime - gameStartTime.current - totalPauseTime.current) / 1000
          )
        : elapsedTime

      // Calculate final metrics
      const finalMetrics: PerformanceMetrics = {
        ...performanceMetrics,
        completion_rate: 100,
        learning_efficiency: Math.max(
          0,
          100 - performanceMetrics.retry_attempts * 10
        ),
        speed_score: Math.max(0, 100 - Math.floor((totalDuration / 60) * 2)), // Penalty for longer time
      }
      setPerformanceMetrics(finalMetrics)

      // Complete game session
      await gameClient.completeGame(gameSession.id, finalMetrics)

      // Send completion event
      await sendGameEvent('GAME_COMPLETED', {
        total_duration: totalDuration,
        final_score: gameProgress.current_score,
        final_metrics: finalMetrics,
        completion_timestamp: new Date().toISOString(),
      })
    } catch (err) {
      console.error('Failed to complete game:', err)
    }
  }

  const handleTimeExpired = async () => {
    if (gameCompleted) return

    try {
      // Force completion due to time limit
      await handleGameComplete()
    } catch (err) {
      console.error('Failed to handle time expiration:', err)
    }
  }

  const handleHintRequest = async () => {
    if (!gameSession || !currentScene) return

    try {
      setGameProgress(prev => ({
        ...prev,
        hints_used: prev.hints_used + 1,
      }))

      setPerformanceMetrics(prev => ({
        ...prev,
        help_requests: prev.help_requests + 1,
      }))

      await sendGameEvent('INTERACTION_COMPLETED', {
        interaction_type: 'hint_request',
        scene_id: currentScene.id,
      })
    } catch (err) {
      console.error('Failed to request hint:', err)
    }
  }

  const handleSceneRestart = async () => {
    if (!currentScene) return

    try {
      setPerformanceMetrics(prev => ({
        ...prev,
        retry_attempts: prev.retry_attempts + 1,
      }))

      await sendGameEvent('INTERACTION_COMPLETED', {
        interaction_type: 'scene_restart',
        scene_id: currentScene.id,
      })
    } catch (err) {
      console.error('Failed to restart scene:', err)
    }
  }

  const handleInteraction = async (interactionType: string, data?: any) => {
    if (!currentScene || !gameSession) return

    try {
      // Update progress
      setGameProgress(prev => ({
        ...prev,
        interactions_completed: prev.interactions_completed + 1,
      }))

      // Update performance based on interaction
      if (data?.correct === false) {
        setGameProgress(prev => ({
          ...prev,
          mistakes_made: prev.mistakes_made + 1,
        }))
        setPerformanceMetrics(prev => ({
          ...prev,
          accuracy_percentage: Math.max(0, prev.accuracy_percentage - 5),
        }))
      }

      // Send interaction event
      await sendGameEvent('INTERACTION_COMPLETED', {
        interaction_type: interactionType,
        scene_id: currentScene.id,
        data,
      })
    } catch (err) {
      console.error('Failed to handle interaction:', err)
    }
  }

  const saveProgress = async () => {
    if (!gameSession) return

    try {
      await gameClient.updateGameSession(gameSession.id, {
        progress_data: gameProgress,
        performance_metrics: performanceMetrics,
        completion_percentage: performanceMetrics.completion_rate,
      })
    } catch (err) {
      console.error('Failed to save progress:', err)
    }
  }

  const sendGameEvent = async (
    eventType: GameEvent['event_type'],
    data?: any
  ) => {
    if (!gameSession || !gameManifest) return

    await gameClient.sendGameEvent({
      event_type: eventType,
      session_id: gameSession.id,
      learner_id: learnerId,
      game_id: gameManifest.id,
      timestamp: new Date().toISOString(),
      data,
    })
  }

  const handleExitGame = () => {
    if (gameStarted && !gameCompleted) {
      const confirmed = window.confirm(
        'Are you sure you want to exit? Your progress will be saved.'
      )
      if (!confirmed) return
    }

    // Save final progress
    if (gameSession) {
      saveProgress()
    }

    navigate('/games')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-white mb-2">
            Loading Game...
          </h2>
          <p className="text-gray-400">
            Please wait while we prepare your game
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-white mb-2">Game Error</h2>
          <p className="text-gray-400 mb-4">{error}</p>
          <button
            onClick={() => navigate('/games')}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors"
          >
            Back to Games
          </button>
        </div>
      </div>
    )
  }

  if (!gameManifest || !currentScene) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">
            Game Not Found
          </h2>
          <p className="text-gray-400">
            The requested game could not be loaded
          </p>
        </div>
      </div>
    )
  }

  return (
    <div
      className="min-h-screen bg-gray-900 relative overflow-hidden"
      data-testid="game-player"
    >
      {/* Background */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: currentScene.background
            ? `url(${currentScene.background})`
            : 'none',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />

      {/* Game HUD */}
      <Hud
        gameTitle={gameManifest.game_title}
        currentScore={gameProgress.current_score}
        timeRemaining={timeRemaining}
        elapsedTime={elapsedTime}
        gamePaused={gamePaused}
        gameCompleted={gameCompleted}
        progress={{
          current: gameProgress.completed_scenes.length,
          total: gameManifest.game_scenes.length,
        }}
        onPause={handlePause}
        onResume={handleResume}
        onExit={handleExitGame}
        hintsUsed={gameProgress.hints_used}
        maxHints={gameManifest.game_rules.hint_system?.max_hints}
        keyboardControlsEnabled={gameManifest.game_rules.keyboard_navigation}
      />

      {/* Main Game Area */}
      <div className="relative z-10 h-screen pt-16">
        {' '}
        {/* Account for HUD height */}
        <AnimatePresence mode="wait">
          {!gameStarted ? (
            // Game Start Screen
            <motion.div
              key="start-screen"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.1 }}
              className="h-full flex items-center justify-center"
            >
              <div className="text-center max-w-2xl mx-auto p-8 bg-black bg-opacity-50 rounded-lg">
                <h1
                  className="text-4xl font-bold text-white mb-4"
                  data-testid="game-title"
                >
                  {gameManifest.game_title}
                </h1>
                <p className="text-xl text-gray-300 mb-6">
                  {gameManifest.game_description}
                </p>
                <div className="text-gray-400 mb-8 space-y-2">
                  <p>
                    Duration: {gameManifest.target_duration_minutes} minutes
                  </p>
                  <p>Difficulty: {gameManifest.difficulty_level}</p>
                  <p>Subject: {gameManifest.subject_area}</p>
                  {gameManifest.game_rules.keyboard_navigation && (
                    <p className="text-sm">
                      💡 Keyboard controls: Space (pause), H (hint), Esc (menu)
                    </p>
                  )}
                </div>
                <button
                  onClick={handleStartGame}
                  className="bg-green-600 hover:bg-green-700 text-white text-xl px-8 py-4 rounded-lg transition-colors"
                  data-testid="start-game-button"
                >
                  Start Game
                </button>
              </div>
            </motion.div>
          ) : gameCompleted ? (
            // Game Results Screen
            <motion.div
              key="results-screen"
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              className="h-full"
            >
              <ResultSheet
                gameTitle={gameManifest.game_title}
                finalScore={gameProgress.current_score}
                totalTime={elapsedTime}
                performanceMetrics={performanceMetrics}
                gameProgress={gameProgress}
                onPlayAgain={() => window.location.reload()}
                onExit={handleExitGame}
              />
            </motion.div>
          ) : (
            // Active Game Canvas
            <motion.div
              key="game-canvas"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="h-full"
            >
              <CanvasStage
                scene={currentScene}
                gameManifest={gameManifest}
                gameProgress={gameProgress}
                isPaused={gamePaused}
                onSceneComplete={handleSceneComplete}
                onInteraction={handleInteraction}
                onError={error => setError(error)}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Pause Overlay */}
      <AnimatePresence>
        {gamePaused && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
          >
            <div className="text-center">
              <h2 className="text-3xl font-bold text-white mb-4">
                Game Paused
              </h2>
              <p className="text-gray-300 mb-8">
                Press space or click resume to continue
              </p>
              <div className="space-x-4">
                <button
                  onClick={handleResume}
                  className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-lg transition-colors"
                  data-testid="resume-button"
                >
                  Resume Game
                </button>
                <button
                  onClick={handleExitGame}
                  className="bg-red-600 hover:bg-red-700 text-white px-6 py-3 rounded-lg transition-colors"
                >
                  Exit Game
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default Play
