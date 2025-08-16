import React from 'react'
import {
  type Lesson,
  type LearningSession,
} from '../../api/lessonRegistryClient'

interface ToolbarProps {
  lesson: Lesson
  session: LearningSession
  isPlaying: boolean
  isPaused: boolean
  onPlay: () => void
  onPause: () => void
  onResume: () => void
  onToggleChat: () => void
  onEndSession: () => void
  isChatOpen: boolean
  timeUntilGameBreak: number
}

export const Toolbar: React.FC<ToolbarProps> = ({
  lesson,
  session,
  isPlaying,
  isPaused,
  onPlay,
  onPause,
  onResume,
  onToggleChat,
  onEndSession,
  isChatOpen,
  timeUntilGameBreak,
}) => {
  const formatTime = (milliseconds: number) => {
    const minutes = Math.floor(milliseconds / (1000 * 60))
    const seconds = Math.floor((milliseconds % (1000 * 60)) / 1000)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const formatGameBreakTime = (milliseconds: number) => {
    const minutes = Math.floor(milliseconds / (1000 * 60))
    if (minutes < 1) return 'Soon'
    return `${minutes}m`
  }

  const getPlayPauseIcon = () => {
    if (isPaused) {
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
            clipRule="evenodd"
          />
        </svg>
      )
    } else if (isPlaying) {
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
            clipRule="evenodd"
          />
        </svg>
      )
    } else {
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
            clipRule="evenodd"
          />
        </svg>
      )
    }
  }

  const handlePlayPause = () => {
    if (isPaused) {
      onResume()
    } else if (isPlaying) {
      onPause()
    } else {
      onPlay()
    }
  }

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      {/* Left side - Lesson info and controls */}
      <div className="flex items-center space-x-4">
        {/* Play/Pause button */}
        <button
          onClick={handlePlayPause}
          className="bg-blue-600 text-white p-2 rounded-full hover:bg-blue-700 transition-colors"
        >
          {getPlayPauseIcon()}
        </button>

        {/* Lesson info */}
        <div className="hidden md:block">
          <h1 className="text-lg font-semibold text-gray-900">
            {lesson.title}
          </h1>
          <div className="flex items-center space-x-3 text-sm text-gray-600">
            <span>📚 {lesson.subject}</span>
            <span>📊 {lesson.gradeLevel}</span>
            <span>⏱️ {Math.round(lesson.estimatedDuration / 60)} min</span>
          </div>
        </div>

        {/* Status indicator */}
        <div
          className={`px-3 py-1 rounded-full text-sm font-medium ${
            isPlaying && !isPaused
              ? 'bg-green-100 text-green-800'
              : 'bg-yellow-100 text-yellow-800'
          }`}
        >
          {isPlaying && !isPaused ? '▶️ Playing' : '⏸️ Paused'}
        </div>
      </div>

      {/* Center - Game break timer (if enabled) */}
      {lesson.gameBreakConfig?.enabled && timeUntilGameBreak > 0 && (
        <div className="hidden lg:flex items-center space-x-2 bg-orange-50 px-3 py-1 rounded-lg">
          <div className="text-orange-600">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
              <path
                fillRule="evenodd"
                d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <span className="text-sm text-orange-700">
            Game break in {formatGameBreakTime(timeUntilGameBreak)}
          </span>
        </div>
      )}

      {/* Right side - Action buttons */}
      <div className="flex items-center space-x-3">
        {/* Session time */}
        <div className="hidden sm:flex items-center space-x-2 text-sm text-gray-600">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
              clipRule="evenodd"
            />
          </svg>
          <span>{formatTime(session.totalTimeSpent)}</span>
        </div>

        {/* Chat toggle */}
        <button
          onClick={onToggleChat}
          className={`p-2 rounded-lg transition-colors ${
            isChatOpen
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
          title="Toggle AI Copilot Chat"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M18 5v8a2 2 0 01-2 2h-5l-5 4v-4H4a2 2 0 01-2-2V5a2 2 0 012-2h12a2 2 0 012 2zM7 8H5v2h2V8zm2 0h2v2H9V8zm6 0h-2v2h2V8z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        {/* Settings button */}
        <button
          className="p-2 rounded-lg bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors"
          title="Settings"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        {/* End session button */}
        <button
          onClick={onEndSession}
          className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
        >
          End Session
        </button>
      </div>
    </div>
  )
}
