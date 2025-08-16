import React from 'react'
import { motion } from 'framer-motion'
import { type AssessmentItem } from '../../api/assessmentClient'

interface ItemRendererProps {
  item: AssessmentItem
  onSubmit: (response: any) => void
  gradeBand: 'K-2' | '3-5' | '6-12'
  adaptiveSettings: {
    audioFirst: boolean
    largeTargets: boolean
    simplifiedInterface: boolean
    timeLimit?: number
  }
  isSubmitting?: boolean
}

export const ItemRenderer: React.FC<ItemRendererProps> = ({
  item,
  onSubmit,
  gradeBand,
  adaptiveSettings,
  isSubmitting = false,
}) => {
  // Grade band specific styling
  const getGradeBandStyles = () => {
    switch (gradeBand) {
      case 'K-2':
        return {
          buttonSize: adaptiveSettings.largeTargets
            ? 'text-2xl px-8 py-6 min-h-[80px]'
            : 'text-xl px-6 py-4',
          fontSize: 'text-2xl',
          spacing: 'space-y-6',
        }
      case '3-5':
        return {
          buttonSize: 'text-lg px-6 py-4',
          fontSize: 'text-xl',
          spacing: 'space-y-5',
        }
      case '6-12':
        return {
          buttonSize: 'text-base px-4 py-3',
          fontSize: 'text-lg',
          spacing: 'space-y-4',
        }
    }
  }

  const styles = getGradeBandStyles()

  const playAudio = (audioUrl: string) => {
    const audio = new Audio(audioUrl)
    audio.play().catch(console.error)
  }

  const renderMultipleChoice = () => {
    if (!item.options) return null

    // Handle true/false as special case of multiple choice with 2 options
    const isTrueFalse =
      item.options.length === 2 &&
      (item.options.some(opt => opt.text.toLowerCase().includes('true')) ||
        item.options.some(opt => opt.text.toLowerCase().includes('false')))

    if (isTrueFalse) {
      return (
        <div className="grid grid-cols-2 gap-6 max-w-md mx-auto">
          {item.options.map((option, index) => (
            <motion.button
              key={option.id}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() =>
                onSubmit({ type: 'multiple-choice', value: option.id })
              }
              disabled={isSubmitting}
              className={`
                ${styles.buttonSize}
                ${
                  index === 0
                    ? 'bg-green-100 text-green-900 border-2 border-green-200 hover:bg-green-200 hover:border-green-300'
                    : 'bg-red-100 text-red-900 border-2 border-red-200 hover:bg-red-200 hover:border-red-300'
                }
                disabled:opacity-50 disabled:cursor-not-allowed
                rounded-lg transition-all duration-200
                ${adaptiveSettings.largeTargets ? 'min-h-[100px]' : 'min-h-[80px]'}
                flex items-center justify-center
              `}
            >
              {gradeBand === 'K-2' && (index === 0 ? '✅ ' : '❌ ')}
              {option.text}
            </motion.button>
          ))}
        </div>
      )
    }

    // Regular multiple choice
    return (
      <div
        className={`grid gap-4 ${
          gradeBand === 'K-2'
            ? 'grid-cols-1'
            : item.options.length <= 2
              ? 'grid-cols-2'
              : 'grid-cols-2 md:grid-cols-3'
        }`}
      >
        {item.options.map((option, index) => (
          <motion.button
            key={option.id}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() =>
              onSubmit({ type: 'multiple-choice', value: option.id })
            }
            disabled={isSubmitting}
            className={`
              ${styles.buttonSize}
              bg-blue-100 text-blue-900 border-2 border-blue-200
              hover:bg-blue-200 hover:border-blue-300
              disabled:opacity-50 disabled:cursor-not-allowed
              rounded-lg transition-all duration-200
              ${adaptiveSettings.largeTargets ? 'min-h-[100px]' : 'min-h-[60px]'}
              flex items-center justify-center text-center
            `}
          >
            {gradeBand === 'K-2' && (
              <span className="text-2xl mr-2">
                {String.fromCharCode(65 + index)} {/* A, B, C, D */}
              </span>
            )}
            {option.text}
          </motion.button>
        ))}
      </div>
    )
  }

  const renderTextInput = () => {
    return (
      <div className="max-w-lg mx-auto">
        <textarea
          placeholder={
            gradeBand === 'K-2'
              ? 'Type your answer here...'
              : 'Enter your answer...'
          }
          className={`
            w-full p-4 border-2 border-gray-300 rounded-lg 
            focus:border-blue-500 focus:ring-blue-500
            ${styles.fontSize}
            ${gradeBand === 'K-2' ? 'min-h-[120px]' : 'min-h-[100px]'}
          `}
          onKeyDown={e => {
            if (e.key === 'Enter' && e.ctrlKey) {
              const value = (e.target as HTMLTextAreaElement).value
              if (value.trim()) {
                onSubmit({ type: 'text-input', value: value.trim() })
              }
            }
          }}
        />
        <div className="mt-4 text-center">
          <button
            onClick={e => {
              const textarea = e.currentTarget.parentElement?.querySelector(
                'textarea'
              ) as HTMLTextAreaElement
              const value = textarea?.value
              if (value?.trim()) {
                onSubmit({ type: 'text-input', value: value.trim() })
              }
            }}
            disabled={isSubmitting}
            className={`
              ${styles.buttonSize}
              bg-blue-600 text-white font-bold rounded-lg
              hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
              transition-all duration-200
            `}
          >
            {isSubmitting ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Submitting...</span>
              </div>
            ) : gradeBand === 'K-2' ? (
              '📤 Submit Answer'
            ) : (
              '➤ Submit'
            )}
          </button>
        </div>
        {gradeBand !== 'K-2' && (
          <p className="text-sm text-gray-500 mt-2 text-center">
            Press Ctrl+Enter to submit quickly
          </p>
        )}
      </div>
    )
  }

  const renderDragDrop = () => {
    // Placeholder for drag & drop implementation
    return (
      <div className="text-center p-8 border-2 border-dashed border-gray-300 rounded-lg">
        <p className="text-gray-600">
          {gradeBand === 'K-2'
            ? '🎯 Drag and Drop Coming Soon!'
            : 'Drag & Drop interaction not yet implemented'}
        </p>
      </div>
    )
  }

  const renderAudioResponse = () => {
    // Placeholder for audio response implementation
    return (
      <div className="text-center p-8 border-2 border-dashed border-gray-300 rounded-lg">
        <p className="text-gray-600">
          {gradeBand === 'K-2'
            ? '🎤 Voice Recording Coming Soon!'
            : 'Audio response not yet implemented'}
        </p>
      </div>
    )
  }

  const renderDrawing = () => {
    // Placeholder for drawing implementation
    return (
      <div className="text-center p-8 border-2 border-dashed border-gray-300 rounded-lg">
        <p className="text-gray-600">
          {gradeBand === 'K-2'
            ? '🎨 Drawing Tool Coming Soon!'
            : 'Drawing interface not yet implemented'}
        </p>
      </div>
    )
  }

  const renderItemContent = () => {
    switch (item.type) {
      case 'multiple-choice':
        return renderMultipleChoice()
      case 'text-input':
        return renderTextInput()
      case 'drag-drop':
        return renderDragDrop()
      case 'audio-response':
        return renderAudioResponse()
      case 'drawing':
        return renderDrawing()
      default:
        return (
          <div className="text-center p-8">
            <p className="text-gray-600">Unknown item type: {item.type}</p>
          </div>
        )
    }
  }

  return (
    <div className="text-center">
      {/* Question text */}
      <h2 className={`font-bold text-gray-900 mb-6 ${styles.fontSize}`}>
        {item.question}
      </h2>

      {/* Audio button for question if available */}
      {item.audioUrl && (
        <div className="mb-6">
          <button
            onClick={() => playAudio(item.audioUrl!)}
            className="flex items-center space-x-2 bg-blue-100 text-blue-800 px-4 py-2 rounded-lg hover:bg-blue-200 transition-colors mx-auto"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.816L4.89 14H2a1 1 0 01-1-1V7a1 1 0 011-1h2.89l3.493-2.816z"
                clipRule="evenodd"
              />
              <path d="M12.293 7.293a1 1 0 011.414 0L15 8.586l1.293-1.293a1 1 0 111.414 1.414L16.414 10l1.293 1.293a1 1 0 01-1.414 1.414L15 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L13.586 10l-1.293-1.293a1 1 0 010-1.414z" />
            </svg>
            <span>
              {gradeBand === 'K-2' ? '🔊 Listen to Question' : '🎧 Play Audio'}
            </span>
          </button>
        </div>
      )}

      {/* Image if present */}
      {item.imageUrl && (
        <div className="mb-6">
          <img
            src={item.imageUrl}
            alt="Question illustration"
            className="max-w-full h-auto mx-auto rounded-lg shadow-md"
            style={{ maxHeight: '300px' }}
          />
        </div>
      )}

      {/* Item interaction */}
      <div className={styles.spacing}>{renderItemContent()}</div>
    </div>
  )
}
