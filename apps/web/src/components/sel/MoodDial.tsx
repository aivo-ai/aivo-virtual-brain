/**
 * S3-13 MoodDial Component
 * Interactive mood selection dial with grade-band visuals
 */

import { useState, useEffect } from 'react'
import { GradeBandVisuals, getGradeBandVisuals } from '../../api/selClient'

interface MoodDialProps {
  value: number
  onChange: (value: number) => void
  gradeLevel: string
  label: string
  min?: number
  max?: number
  className?: string
}

const MOOD_LABELS = {
  elementary: ['😢', '😟', '😐', '😊', '😄'],
  middle: ['Terrible', 'Bad', 'Okay', 'Good', 'Great'],
  high: ['Very Low', 'Low', 'Neutral', 'High', 'Very High'],
}

export function MoodDial({
  value,
  onChange,
  gradeLevel,
  label,
  min = 1,
  max = 10,
  className = '',
}: MoodDialProps) {
  const [visuals, setVisuals] = useState<GradeBandVisuals | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  useEffect(() => {
    setVisuals(getGradeBandVisuals(gradeLevel))
  }, [gradeLevel])

  const getAngle = (value: number) => {
    const percentage = (value - min) / (max - min)
    return percentage * 180 - 90 // -90 to 90 degrees
  }

  const getColorForValue = (value: number) => {
    if (!visuals) return '#6B7280'

    const percentage = (value - min) / (max - min)
    const colorIndex = Math.floor(percentage * (visuals.colors.length - 1))
    return visuals.colors[colorIndex] || visuals.colors[0]
  }

  const getMoodLabel = (value: number) => {
    if (!visuals) return value.toString()

    const labels = MOOD_LABELS[visuals.theme]
    if (visuals.theme === 'elementary') {
      // Map 1-10 to emoji scale
      const emojiIndex = Math.min(
        Math.floor((value - 1) / 2),
        labels.length - 1
      )
      return labels[emojiIndex]
    } else {
      // Map 1-10 to text scale
      const labelIndex = Math.min(
        Math.floor((value - 1) / 2),
        labels.length - 1
      )
      return labels[labelIndex]
    }
  }

  const handleMouseDown = (event: React.MouseEvent) => {
    setIsDragging(true)
    updateValueFromEvent(event)
  }

  const handleMouseMove = (event: React.MouseEvent) => {
    if (isDragging) {
      updateValueFromEvent(event)
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  const updateValueFromEvent = (event: React.MouseEvent) => {
    const rect = event.currentTarget.getBoundingClientRect()
    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2

    const angle = Math.atan2(event.clientY - centerY, event.clientX - centerX)
    const degrees = (angle * 180) / Math.PI

    // Convert angle to value (180 degree range from -90 to 90)
    let normalizedAngle = degrees + 90
    if (normalizedAngle < 0) normalizedAngle = 0
    if (normalizedAngle > 180) normalizedAngle = 180

    const percentage = normalizedAngle / 180
    const newValue = Math.round(min + percentage * (max - min))

    onChange(Math.max(min, Math.min(max, newValue)))
  }

  useEffect(() => {
    const handleGlobalMouseUp = () => setIsDragging(false)
    const handleGlobalMouseMove = (event: MouseEvent) => {
      if (isDragging) {
        // Convert MouseEvent to React.MouseEvent for compatibility
        updateValueFromEvent(event as any)
      }
    }

    if (isDragging) {
      document.addEventListener('mouseup', handleGlobalMouseUp)
      document.addEventListener('mousemove', handleGlobalMouseMove)
    }

    return () => {
      document.removeEventListener('mouseup', handleGlobalMouseUp)
      document.removeEventListener('mousemove', handleGlobalMouseMove)
    }
  }, [isDragging])

  if (!visuals) {
    return (
      <div className="animate-pulse w-48 h-24 bg-gray-200 rounded-lg"></div>
    )
  }

  return (
    <div className={`flex flex-col items-center space-y-4 ${className}`}>
      <label className="text-lg font-medium text-gray-700">{label}</label>

      <div className="relative">
        {/* Dial Background */}
        <div
          className="relative w-48 h-24 overflow-hidden cursor-pointer select-none"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{
            background: `linear-gradient(90deg, ${visuals.colors.join(', ')})`,
          }}
        >
          {/* Dial Container */}
          <div className="absolute inset-0 rounded-full border-8 border-gray-200">
            {/* Value Indicators */}
            {Array.from({ length: max - min + 1 }, (_, i) => {
              const tickValue = min + i
              const tickAngle = getAngle(tickValue)
              return (
                <div
                  key={tickValue}
                  className="absolute w-1 h-4 bg-gray-400"
                  style={{
                    bottom: '50%',
                    left: '50%',
                    transformOrigin: 'bottom center',
                    transform: `translateX(-50%) rotate(${tickAngle}deg)`,
                  }}
                />
              )
            })}

            {/* Dial Pointer */}
            <div
              className="absolute w-2 h-16 bg-white border-2 border-gray-800 rounded-full shadow-lg transition-transform duration-200"
              style={{
                bottom: '50%',
                left: '50%',
                transformOrigin: 'bottom center',
                transform: `translateX(-50%) rotate(${getAngle(value)}deg)`,
                backgroundColor: getColorForValue(value),
              }}
            >
              {/* Pointer Tip */}
              <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 w-4 h-4 bg-white border-2 border-gray-800 rounded-full shadow-lg" />
            </div>
          </div>
        </div>

        {/* Value Display */}
        <div className="absolute -bottom-12 left-1/2 transform -translate-x-1/2 text-center">
          <div
            className={`text-2xl font-bold mb-1 ${visuals.theme === 'elementary' ? 'text-4xl' : ''}`}
            style={{ color: getColorForValue(value) }}
          >
            {getMoodLabel(value)}
          </div>
          <div className="text-sm text-gray-500">
            {value}/{max}
          </div>
        </div>
      </div>

      {/* Quick Select Buttons */}
      <div className="flex space-x-2 mt-8">
        {visuals.theme === 'elementary'
          ? // Emoji buttons for elementary
            MOOD_LABELS.elementary.map((emoji, index) => {
              const buttonValue = (index + 1) * 2
              return (
                <button
                  key={index}
                  className={`text-2xl p-2 rounded-lg border-2 transition-all ${
                    Math.abs(value - buttonValue) <= 1
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onClick={() => onChange(buttonValue)}
                >
                  {emoji}
                </button>
              )
            })
          : // Number buttons for middle/high school
            Array.from({ length: 5 }, (_, i) => {
              const buttonValue = (i + 1) * 2
              return (
                <button
                  key={i}
                  className={`w-8 h-8 rounded-full font-semibold transition-all ${
                    Math.abs(value - buttonValue) <= 1
                      ? 'text-white'
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                  style={{
                    backgroundColor:
                      Math.abs(value - buttonValue) <= 1
                        ? getColorForValue(buttonValue)
                        : 'transparent',
                    border: `2px solid ${getColorForValue(buttonValue)}`,
                  }}
                  onClick={() => onChange(buttonValue)}
                >
                  {buttonValue}
                </button>
              )
            })}
      </div>
    </div>
  )
}
