import React, { useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { type Lesson } from '../../api/lessonRegistryClient'

interface AudioControlsProps {
  isPlaying: boolean
  volume: number
  onVolumeChange: (volume: number) => void
  lesson: Lesson
}

export const AudioControls: React.FC<AudioControlsProps> = ({
  isPlaying,
  volume,
  onVolumeChange,
  lesson,
}) => {
  const audioRef = useRef<HTMLAudioElement>(null)

  // Handle background audio if lesson has it
  useEffect(() => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.play().catch(console.error)
      } else {
        audioRef.current.pause()
      }
    }
  }, [isPlaying])

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume
    }
  }, [volume])

  const handleVolumeSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value)
    onVolumeChange(newVolume)
  }

  const toggleMute = () => {
    onVolumeChange(volume > 0 ? 0 : 1)
  }

  const getVolumeIcon = () => {
    if (volume === 0) {
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.816L4.89 14H2a1 1 0 01-1-1V7a1 1 0 011-1h2.89l3.493-2.816zM12.293 7.293a1 1 0 011.414 0L15 8.586l1.293-1.293a1 1 0 111.414 1.414L16.414 10l1.293 1.293a1 1 0 01-1.414 1.414L15 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L13.586 10l-1.293-1.293a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      )
    } else if (volume < 0.5) {
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.816L4.89 14H2a1 1 0 01-1-1V7a1 1 0 011-1h2.89l3.493-2.816zm2.617 5.344a1 1 0 011.414 0L15 10.006l1.586-1.586a1 1 0 111.414 1.414L16.414 11.42 18 13.006a1 1 0 01-1.414 1.414L15 12.834l-1.586 1.586a1 1 0 01-1.414-1.414L13.586 11.42 12 9.834a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      )
    } else {
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.816L4.89 14H2a1 1 0 01-1-1V7a1 1 0 011-1h2.89l3.493-2.816zM12 8a1 1 0 011-1 1 1 0 011 1v4a1 1 0 11-2 0V8zm4-1a1 1 0 011 1v4a1 1 0 11-2 0V8a1 1 0 011-1z"
            clipRule="evenodd"
          />
        </svg>
      )
    }
  }

  // Check if lesson has background audio
  const hasBackgroundAudio =
    lesson.metadata && 'backgroundAudioUrl' in lesson.metadata

  if (!hasBackgroundAudio && volume === 1) {
    // Don't show audio controls if there's no background audio and volume is at default
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white border-t border-gray-200 px-4 py-2"
    >
      <div className="flex items-center justify-between max-w-4xl mx-auto">
        {/* Left side - Background audio info */}
        <div className="flex items-center space-x-3">
          {hasBackgroundAudio && (
            <>
              <div className="text-sm text-gray-600">🎵 Background Audio</div>
              <audio
                ref={audioRef}
                loop
                preload="auto"
                src={(lesson.metadata as any).backgroundAudioUrl}
              />
            </>
          )}
        </div>

        {/* Right side - Volume controls */}
        <div className="flex items-center space-x-3">
          <span className="text-sm text-gray-600">Volume</span>

          <button
            onClick={toggleMute}
            className="p-1 text-gray-600 hover:text-gray-900 transition-colors"
            title={volume > 0 ? 'Mute' : 'Unmute'}
          >
            {getVolumeIcon()}
          </button>

          <div className="flex items-center space-x-2">
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={volume}
              onChange={handleVolumeSliderChange}
              className="w-20 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
              style={{
                background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${volume * 100}%, #E5E7EB ${volume * 100}%, #E5E7EB 100%)`,
              }}
            />
            <span className="text-xs text-gray-500 w-8 text-center">
              {Math.round(volume * 100)}%
            </span>
          </div>
        </div>
      </div>

      <style>{`
        .slider::-webkit-slider-thumb {
          appearance: none;
          height: 16px;
          width: 16px;
          border-radius: 50%;
          background: #3B82F6;
          cursor: pointer;
          border: 2px solid #ffffff;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .slider::-moz-range-thumb {
          height: 16px;
          width: 16px;
          border-radius: 50%;
          background: #3B82F6;
          cursor: pointer;
          border: 2px solid #ffffff;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
      `}</style>
    </motion.div>
  )
}
