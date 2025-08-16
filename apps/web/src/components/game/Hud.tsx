import React from 'react'
import { motion } from 'framer-motion'

interface HudProps {
  gameTitle: string
  currentScore: number
  timeRemaining: number
  elapsedTime: number
  gamePaused: boolean
  gameCompleted: boolean
  progress: {
    current: number
    total: number
  }
  onPause: () => void
  onResume: () => void
  onExit: () => void
  hintsUsed: number
  maxHints?: number
  keyboardControlsEnabled: boolean
}

export const Hud: React.FC<HudProps> = ({
  gameTitle,
  currentScore,
  timeRemaining,
  elapsedTime,
  gamePaused,
  gameCompleted,
  progress,
  onPause,
  onResume,
  onExit,
  hintsUsed,
  maxHints,
  keyboardControlsEnabled,
}) => {
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const progressPercentage =
    progress.total > 0 ? (progress.current / progress.total) * 100 : 0

  const getTimeColor = (): string => {
    if (timeRemaining > 300) return 'text-green-400' // > 5 minutes
    if (timeRemaining > 60) return 'text-yellow-400' // > 1 minute
    return 'text-red-400' // < 1 minute - urgent
  }

  return (
    <motion.div
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className="fixed top-0 left-0 right-0 z-40 bg-gray-900 bg-opacity-95 backdrop-blur-sm border-b border-gray-700"
      data-testid="game-hud"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left side - Game info */}
          <div className="flex items-center space-x-6">
            <div className="text-white">
              <h1
                className="text-lg font-bold truncate max-w-xs"
                title={gameTitle}
              >
                {gameTitle}
              </h1>
            </div>

            {/* Score */}
            <div className="text-center">
              <div
                className="text-yellow-400 text-xl font-bold"
                data-testid="current-score"
              >
                {currentScore.toLocaleString()}
              </div>
              <div className="text-xs text-gray-400">Score</div>
            </div>

            {/* Progress */}
            <div className="hidden sm:flex items-center space-x-3">
              <div className="text-center">
                <div className="text-blue-400 text-sm font-semibold">
                  {progress.current}/{progress.total}
                </div>
                <div className="text-xs text-gray-400">Progress</div>
              </div>
              <div className="w-24 bg-gray-700 rounded-full h-2">
                <motion.div
                  className="bg-blue-500 h-2 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${progressPercentage}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </div>
          </div>

          {/* Center - Timer */}
          <div className="flex items-center space-x-4">
            <div className="text-center">
              <div
                className={`text-xl font-mono font-bold ${getTimeColor()}`}
                data-testid="time-remaining"
              >
                {formatTime(timeRemaining)}
              </div>
              <div className="text-xs text-gray-400">Remaining</div>
            </div>

            <div className="hidden md:block text-center">
              <div className="text-gray-300 text-sm font-mono">
                {formatTime(elapsedTime)}
              </div>
              <div className="text-xs text-gray-400">Elapsed</div>
            </div>
          </div>

          {/* Right side - Controls */}
          <div className="flex items-center space-x-3">
            {/* Hints indicator */}
            {maxHints && maxHints > 0 && (
              <div className="hidden sm:flex items-center text-center">
                <div className="text-purple-400 text-sm">
                  {hintsUsed}/{maxHints}
                </div>
                <div className="text-xs text-gray-400 ml-1">Hints</div>
              </div>
            )}

            {/* Keyboard controls indicator */}
            {keyboardControlsEnabled && (
              <div className="hidden lg:flex items-center text-xs text-gray-400 space-x-1">
                <span>⌨️</span>
                <span>Space: Pause</span>
              </div>
            )}

            {/* Pause/Resume button */}
            {!gameCompleted && (
              <button
                onClick={gamePaused ? onResume : onPause}
                className={`
                  px-4 py-2 rounded-md font-medium transition-colors
                  ${
                    gamePaused
                      ? 'bg-green-600 hover:bg-green-700 text-white'
                      : 'bg-yellow-600 hover:bg-yellow-700 text-white'
                  }
                `}
                data-testid={gamePaused ? 'resume-button' : 'pause-button'}
              >
                {gamePaused ? (
                  <span className="flex items-center space-x-1">
                    <span>▶️</span>
                    <span className="hidden sm:inline">Resume</span>
                  </span>
                ) : (
                  <span className="flex items-center space-x-1">
                    <span>⏸️</span>
                    <span className="hidden sm:inline">Pause</span>
                  </span>
                )}
              </button>
            )}

            {/* Exit button */}
            <button
              onClick={onExit}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md font-medium transition-colors"
              data-testid="exit-button"
            >
              <span className="flex items-center space-x-1">
                <span>🚪</span>
                <span className="hidden sm:inline">Exit</span>
              </span>
            </button>
          </div>
        </div>

        {/* Mobile progress bar */}
        <div className="sm:hidden pb-2">
          <div className="flex items-center justify-between text-sm text-gray-400 mb-1">
            <span>
              Progress: {progress.current}/{progress.total}
            </span>
            <span>{Math.round(progressPercentage)}%</span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <motion.div
              className="bg-blue-500 h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progressPercentage}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>
      </div>

      {/* Status indicators */}
      <div className="absolute top-full left-0 right-0 pointer-events-none">
        {/* Paused indicator */}
        {gamePaused && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-yellow-500 text-yellow-900 text-center py-1 text-sm font-medium"
          >
            ⏸️ Game Paused - Press Space or click Resume to continue
          </motion.div>
        )}

        {/* Low time warning */}
        {timeRemaining <= 60 && timeRemaining > 0 && !gamePaused && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: [0, 1, 0] }}
            transition={{ duration: 1, repeat: Infinity }}
            className="bg-red-500 text-white text-center py-1 text-sm font-medium"
          >
            ⚠️ Less than 1 minute remaining!
          </motion.div>
        )}

        {/* Time expired */}
        {timeRemaining === 0 && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-red-600 text-white text-center py-2 text-sm font-bold"
          >
            ⏰ Time's Up! Game will complete shortly...
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}
