import React from 'react'
import { motion } from 'framer-motion'
import {
  type PerformanceMetrics,
  type GameProgress,
} from '../../api/gameClient'

interface ResultSheetProps {
  gameTitle: string
  finalScore: number
  totalTime: number
  performanceMetrics: PerformanceMetrics
  gameProgress: GameProgress
  onPlayAgain: () => void
  onExit: () => void
}

export const ResultSheet: React.FC<ResultSheetProps> = ({
  gameTitle,
  finalScore,
  totalTime,
  performanceMetrics,
  gameProgress,
  onPlayAgain,
  onExit,
}) => {
  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60

    if (hours > 0) {
      return `${hours}h ${mins}m ${secs}s`
    }
    return `${mins}m ${secs}s`
  }

  const getGrade = (percentage: number): { letter: string; color: string } => {
    if (percentage >= 90) return { letter: 'A', color: 'text-green-500' }
    if (percentage >= 80) return { letter: 'B', color: 'text-blue-500' }
    if (percentage >= 70) return { letter: 'C', color: 'text-yellow-500' }
    if (percentage >= 60) return { letter: 'D', color: 'text-orange-500' }
    return { letter: 'F', color: 'text-red-500' }
  }

  const getPerformanceLevel = (
    score: number
  ): { level: string; color: string } => {
    if (score >= 90) return { level: 'Excellent', color: 'text-green-500' }
    if (score >= 80) return { level: 'Great', color: 'text-blue-500' }
    if (score >= 70) return { level: 'Good', color: 'text-yellow-500' }
    if (score >= 60) return { level: 'Fair', color: 'text-orange-500' }
    return { level: 'Needs Improvement', color: 'text-red-500' }
  }

  const overallGrade = getGrade(performanceMetrics.completion_rate)
  const accuracyLevel = getPerformanceLevel(
    performanceMetrics.accuracy_percentage
  )
  const speedLevel = getPerformanceLevel(performanceMetrics.speed_score)
  const efficiencyLevel = getPerformanceLevel(
    performanceMetrics.learning_efficiency
  )

  const achievements = []
  if (performanceMetrics.accuracy_percentage === 100)
    achievements.push('🎯 Perfect Accuracy')
  if (performanceMetrics.completion_rate === 100)
    achievements.push('✅ Completed All Tasks')
  if (gameProgress.hints_used === 0) achievements.push('🧠 No Hints Needed')
  if (gameProgress.mistakes_made === 0)
    achievements.push('💎 Flawless Execution')
  if (performanceMetrics.retry_attempts === 0)
    achievements.push('🚀 First Try Success')

  const stats = [
    {
      label: 'Final Score',
      value: finalScore.toLocaleString(),
      icon: '🏆',
      color: 'text-yellow-500',
    },
    {
      label: 'Accuracy',
      value: `${Math.round(performanceMetrics.accuracy_percentage)}%`,
      icon: '🎯',
      color: accuracyLevel.color,
    },
    {
      label: 'Speed Score',
      value: `${Math.round(performanceMetrics.speed_score)}%`,
      icon: '⚡',
      color: speedLevel.color,
    },
    {
      label: 'Efficiency',
      value: `${Math.round(performanceMetrics.learning_efficiency)}%`,
      icon: '🧠',
      color: efficiencyLevel.color,
    },
    {
      label: 'Completion',
      value: `${Math.round(performanceMetrics.completion_rate)}%`,
      icon: '📊',
      color: overallGrade.color,
    },
    {
      label: 'Time Taken',
      value: formatTime(totalTime),
      icon: '⏱️',
      color: 'text-blue-500',
    },
  ]

  const detailedStats = [
    {
      label: 'Interactions Completed',
      value: gameProgress.interactions_completed,
    },
    {
      label: 'Correct Answers',
      value: gameProgress.interactions_completed - gameProgress.mistakes_made,
    },
    { label: 'Mistakes Made', value: gameProgress.mistakes_made },
    { label: 'Hints Used', value: gameProgress.hints_used },
    { label: 'Retry Attempts', value: performanceMetrics.retry_attempts },
    { label: 'Help Requests', value: performanceMetrics.help_requests },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl w-full bg-white rounded-xl shadow-2xl overflow-hidden"
        data-testid="result-sheet"
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-8 py-6 text-white">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-center"
          >
            <h1 className="text-3xl font-bold mb-2">🎉 Game Complete!</h1>
            <h2 className="text-xl opacity-90">{gameTitle}</h2>
          </motion.div>
        </div>

        {/* Overall Grade */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center py-8 bg-gray-50"
        >
          <div className={`text-6xl font-bold ${overallGrade.color} mb-2`}>
            {overallGrade.letter}
          </div>
          <p className="text-lg text-gray-700">Overall Grade</p>
          <p className="text-sm text-gray-500 mt-1">
            Based on completion rate of{' '}
            {Math.round(performanceMetrics.completion_rate)}%
          </p>
        </motion.div>

        <div className="p-8 space-y-8">
          {/* Main Stats Grid */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <h3 className="text-xl font-semibold text-gray-800 mb-4">
              Performance Summary
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {stats.map((stat, index) => (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + index * 0.1 }}
                  className="bg-white border border-gray-200 rounded-lg p-4 text-center shadow-sm"
                >
                  <div className="text-2xl mb-2">{stat.icon}</div>
                  <div className={`text-lg font-bold ${stat.color}`}>
                    {stat.value}
                  </div>
                  <div className="text-sm text-gray-600">{stat.label}</div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          {/* Achievements */}
          {achievements.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.8 }}
            >
              <h3 className="text-xl font-semibold text-gray-800 mb-4">
                🏅 Achievements
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {achievements.map((achievement, index) => (
                  <motion.div
                    key={achievement}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.9 + index * 0.1 }}
                    className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 text-yellow-800"
                  >
                    {achievement}
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Detailed Statistics */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.0 }}
            className="bg-gray-50 rounded-lg p-6"
          >
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              📈 Detailed Statistics
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {detailedStats.map(stat => (
                <div key={stat.label} className="text-center">
                  <div className="text-xl font-bold text-gray-700">
                    {stat.value}
                  </div>
                  <div className="text-sm text-gray-500">{stat.label}</div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Performance Insights */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.1 }}
          >
            <h3 className="text-lg font-semibold text-gray-800 mb-4">
              💡 Performance Insights
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                <span className="text-blue-800">Accuracy Level</span>
                <span className={`font-semibold ${accuracyLevel.color}`}>
                  {accuracyLevel.level}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                <span className="text-green-800">Speed Performance</span>
                <span className={`font-semibold ${speedLevel.color}`}>
                  {speedLevel.level}
                </span>
              </div>
              <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
                <span className="text-purple-800">Learning Efficiency</span>
                <span className={`font-semibold ${efficiencyLevel.color}`}>
                  {efficiencyLevel.level}
                </span>
              </div>
            </div>
          </motion.div>

          {/* Action Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2 }}
            className="flex flex-col sm:flex-row gap-4 pt-4"
          >
            <button
              onClick={onPlayAgain}
              className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
              data-testid="play-again-button"
            >
              <span>🔄</span>
              <span>Play Again</span>
            </button>
            <button
              onClick={onExit}
              className="flex-1 bg-gray-600 hover:bg-gray-700 text-white px-6 py-3 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2"
              data-testid="exit-result-button"
            >
              <span>🏠</span>
              <span>Back to Games</span>
            </button>
          </motion.div>

          {/* Footer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.3 }}
            className="text-center text-gray-500 text-sm pt-4 border-t border-gray-200"
          >
            Game completed on {new Date().toLocaleDateString()} at{' '}
            {new Date().toLocaleTimeString()}
          </motion.div>
        </div>
      </motion.div>
    </div>
  )
}
