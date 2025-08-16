import React from 'react'
import { motion } from 'framer-motion'

interface ProgressDotsProps {
  currentItem: number
  totalItems: number
  gradeBand: 'K-2' | '3-5' | '6-12'
}

export const ProgressDots: React.FC<ProgressDotsProps> = ({
  currentItem,
  totalItems,
  gradeBand,
}) => {
  // Show dots for smaller assessments, progress bar for larger ones
  const showDots = totalItems <= 10 && gradeBand === 'K-2'

  if (showDots) {
    return (
      <div className="flex items-center justify-center space-x-2 mb-6">
        {Array.from({ length: totalItems }, (_, index) => (
          <motion.div
            key={index}
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: index * 0.1 }}
            className={`
              w-3 h-3 rounded-full transition-all duration-300
              ${
                index < currentItem
                  ? 'bg-green-500'
                  : index === currentItem - 1
                    ? 'bg-blue-500'
                    : 'bg-gray-300'
              }
            `}
          />
        ))}
      </div>
    )
  }

  // Progress bar for older grades or longer assessments
  const percentage = (currentItem / totalItems) * 100

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-gray-700">
          Question {currentItem} of {totalItems}
        </span>
        <span className="text-sm font-medium text-gray-700">
          {Math.round(percentage)}%
        </span>
      </div>
      <div className="bg-gray-200 rounded-full h-2 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5 }}
          className="h-full bg-gradient-to-r from-blue-500 to-purple-600 rounded-full"
        />
      </div>
    </div>
  )
}
