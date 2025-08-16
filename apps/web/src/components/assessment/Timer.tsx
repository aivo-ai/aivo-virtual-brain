import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface TimerProps {
  timeLimit?: number // in seconds
  onTimeUp: () => void
  isPaused?: boolean
  gradeBand: 'K-2' | '3-5' | '6-12'
}

export const Timer: React.FC<TimerProps> = ({
  timeLimit,
  onTimeUp,
  isPaused = false,
  gradeBand,
}) => {
  const [timeRemaining, setTimeRemaining] = useState(timeLimit || 0)

  useEffect(() => {
    if (!timeLimit) return
    setTimeRemaining(timeLimit)
  }, [timeLimit])

  useEffect(() => {
    if (!timeLimit || isPaused || timeRemaining <= 0) return

    const timer = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev <= 1) {
          onTimeUp()
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [timeLimit, isPaused, timeRemaining, onTimeUp])

  if (!timeLimit || gradeBand === 'K-2') {
    return null // No timer for K-2 or when no time limit
  }

  const percentage = timeLimit > 0 ? (timeRemaining / timeLimit) * 100 : 0
  const isWarning = percentage < 25
  const isCritical = percentage < 10

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        flex items-center space-x-3 px-4 py-2 rounded-lg
        ${
          isCritical
            ? 'bg-red-100 text-red-800'
            : isWarning
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-blue-100 text-blue-800'
        }
        transition-all duration-300
      `}
    >
      {/* Timer icon */}
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path
          fillRule="evenodd"
          d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
          clipRule="evenodd"
        />
      </svg>

      {/* Time display */}
      <span className="font-mono font-bold">{formatTime(timeRemaining)}</span>

      {/* Visual progress */}
      {(gradeBand === '3-5' || gradeBand === '6-12') && (
        <div className="w-16 bg-gray-200 rounded-full h-2">
          <motion.div
            initial={{ width: '100%' }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.3 }}
            className={`
              h-full rounded-full transition-colors duration-300
              ${
                isCritical
                  ? 'bg-red-500'
                  : isWarning
                    ? 'bg-yellow-500'
                    : 'bg-blue-500'
              }
            `}
          />
        </div>
      )}

      {/* Warning text */}
      {isCritical && gradeBand === '6-12' && (
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          className="text-xs font-medium"
        >
          Time running out!
        </motion.span>
      )}
    </motion.div>
  )
}
