import React from 'react'

export interface ProgressProps {
  value?: number
  max?: number
  className?: string
}

export const Progress: React.FC<ProgressProps> = ({
  value = 0,
  max = 100,
  className = '',
}) => {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  return (
    <div
      className={`w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700 ${className}`}
    >
      <div
        className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}
