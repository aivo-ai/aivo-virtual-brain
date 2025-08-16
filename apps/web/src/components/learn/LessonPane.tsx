import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  type Lesson,
  type LessonSection,
  type LessonContent,
} from '../../api/lessonRegistryClient'

interface LessonPaneProps {
  lesson: Lesson
  currentSectionId: string | null
  currentContentId: string | null
  isPlaying: boolean
  volume: number
  onSectionChange: (sectionId: string, contentId?: string) => void
  onInteraction: (type: string, element: string, data?: any) => void
}

export const LessonPane: React.FC<LessonPaneProps> = ({
  lesson,
  currentSectionId,
  currentContentId,
  isPlaying,
  volume,
  onSectionChange,
  onInteraction,
}) => {
  const [expandedSection, setExpandedSection] = useState<string | null>(
    currentSectionId
  )

  const currentSection = lesson.sections.find(s => s.id === currentSectionId)
  const currentContent = currentSection?.content.find(
    c => c.id === currentContentId
  )

  useEffect(() => {
    if (currentSectionId && !expandedSection) {
      setExpandedSection(currentSectionId)
    }
  }, [currentSectionId, expandedSection])

  const handleSectionClick = (section: LessonSection) => {
    const newExpanded = expandedSection === section.id ? null : section.id
    setExpandedSection(newExpanded)

    if (newExpanded && section.content.length > 0) {
      onSectionChange(section.id, section.content[0].id)
    }

    onInteraction('click', 'section', {
      sectionId: section.id,
      expanded: newExpanded !== null,
    })
  }

  const handleContentClick = (content: LessonContent) => {
    if (currentSectionId) {
      onSectionChange(currentSectionId, content.id)
    }

    onInteraction('click', 'content', {
      contentId: content.id,
      contentType: content.type,
    })
  }

  const renderContent = (content: LessonContent) => {
    switch (content.type) {
      case 'video':
        return (
          <div className="aspect-video bg-black rounded-lg overflow-hidden">
            <video
              controls
              className="w-full h-full"
              autoPlay={isPlaying}
              onLoadedMetadata={e => {
                const video = e.target as HTMLVideoElement
                video.volume = volume
              }}
              onPlay={() =>
                onInteraction('play', 'video', { contentId: content.id })
              }
              onPause={() =>
                onInteraction('pause', 'video', { contentId: content.id })
              }
              onTimeUpdate={e => {
                const video = e.target as HTMLVideoElement
                video.volume = volume
                onInteraction('timeupdate', 'video', {
                  contentId: content.id,
                  currentTime: video.currentTime,
                  duration: video.duration,
                })
              }}
            >
              <source src={content.content.url} type="video/mp4" />
              Your browser does not support the video tag.
            </video>
          </div>
        )

      case 'audio':
        return (
          <div className="bg-blue-50 rounded-lg p-6">
            <div className="flex items-center space-x-4">
              <div className="flex-shrink-0">
                <svg
                  className="w-12 h-12 text-blue-600"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.617.816L4.89 14H2a1 1 0 01-1-1V7a1 1 0 011-1h2.89l3.493-2.816z" />
                  <path d="M12.293 7.293a1 1 0 011.414 0L15 8.586l1.293-1.293a1 1 0 111.414 1.414L16.414 10l1.293 1.293a1 1 0 01-1.414 1.414L15 11.414l-1.293 1.293a1 1 0 01-1.414-1.414L13.586 10l-1.293-1.293a1 1 0 010-1.414z" />
                </svg>
              </div>
              <div className="flex-1">
                <audio
                  controls
                  className="w-full"
                  autoPlay={isPlaying}
                  onLoadedMetadata={e => {
                    const audio = e.target as HTMLAudioElement
                    audio.volume = volume
                  }}
                  onPlay={() => {
                    const audio = document.querySelector(
                      'audio'
                    ) as HTMLAudioElement
                    if (audio) audio.volume = volume
                    onInteraction('play', 'audio', { contentId: content.id })
                  }}
                  onPause={() =>
                    onInteraction('pause', 'audio', { contentId: content.id })
                  }
                >
                  <source src={content.content.url} type="audio/mp3" />
                  Your browser does not support the audio element.
                </audio>
              </div>
            </div>
          </div>
        )

      case 'text':
        return (
          <div className="prose max-w-none">
            <div
              dangerouslySetInnerHTML={{
                __html: content.content.html || content.content.text,
              }}
              onClick={e => {
                const target = e.target as HTMLElement
                onInteraction('click', 'text', {
                  contentId: content.id,
                  elementType: target.tagName,
                  elementText: target.textContent?.substring(0, 100),
                })
              }}
            />
          </div>
        )

      case 'interactive':
        return (
          <div className="bg-green-50 rounded-lg p-6 border-2 border-dashed border-green-200">
            <div className="text-center">
              <div className="text-4xl mb-4">🎮</div>
              <h3 className="text-lg font-semibold text-green-800 mb-2">
                Interactive Content
              </h3>
              <p className="text-green-600 mb-4">{content.description}</p>
              <button
                onClick={() => {
                  onInteraction('click', 'interactive', {
                    contentId: content.id,
                  })
                  // TODO: Launch interactive content
                }}
                className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
              >
                Start Interactive
              </button>
            </div>
          </div>
        )

      case 'simulation':
        return (
          <div className="bg-purple-50 rounded-lg p-6 border-2 border-dashed border-purple-200">
            <div className="text-center">
              <div className="text-4xl mb-4">🔬</div>
              <h3 className="text-lg font-semibold text-purple-800 mb-2">
                Simulation
              </h3>
              <p className="text-purple-600 mb-4">{content.description}</p>
              <button
                onClick={() => {
                  onInteraction('click', 'simulation', {
                    contentId: content.id,
                  })
                  // TODO: Launch simulation
                }}
                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 transition-colors"
              >
                Start Simulation
              </button>
            </div>
          </div>
        )

      case 'game':
        return (
          <div className="bg-orange-50 rounded-lg p-6 border-2 border-dashed border-orange-200">
            <div className="text-center">
              <div className="text-4xl mb-4">🎯</div>
              <h3 className="text-lg font-semibold text-orange-800 mb-2">
                Learning Game
              </h3>
              <p className="text-orange-600 mb-4">{content.description}</p>
              <button
                onClick={() => {
                  onInteraction('click', 'game', { contentId: content.id })
                  // TODO: Launch game
                }}
                className="bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700 transition-colors"
              >
                Play Game
              </button>
            </div>
          </div>
        )

      default:
        return (
          <div className="bg-gray-50 rounded-lg p-6">
            <p className="text-gray-600">
              Content type "{content.type}" not yet supported
            </p>
          </div>
        )
    }
  }

  return (
    <div className="h-full flex">
      {/* Sidebar with lesson structure */}
      <div className="w-80 bg-white border-r border-gray-200 overflow-y-auto">
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">
            {lesson.title}
          </h2>
          <p className="text-sm text-gray-600">{lesson.description}</p>
          <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
            <span>📚 {lesson.subject}</span>
            <span>⏱️ {Math.round(lesson.estimatedDuration / 60)} min</span>
            <span>📊 {lesson.difficulty}</span>
          </div>
        </div>

        <div className="p-4">
          <h3 className="text-sm font-medium text-gray-900 mb-3">
            Lesson Sections
          </h3>
          <div className="space-y-2">
            {lesson.sections.map((section, sectionIndex) => (
              <div key={section.id}>
                <button
                  onClick={() => handleSectionClick(section)}
                  className={`w-full text-left p-3 rounded-lg transition-colors ${
                    currentSectionId === section.id
                      ? 'bg-blue-100 text-blue-900'
                      : 'hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
                        {sectionIndex + 1}
                      </span>
                      <span className="font-medium">{section.title}</span>
                    </div>
                    <svg
                      className={`w-4 h-4 transition-transform ${
                        expandedSection === section.id ? 'rotate-90' : ''
                      }`}
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" />
                    </svg>
                  </div>
                </button>

                {/* Section content list */}
                {expandedSection === section.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="ml-4 mt-2 space-y-1"
                  >
                    {section.content.map((content, contentIndex) => (
                      <button
                        key={content.id}
                        onClick={() => handleContentClick(content)}
                        className={`w-full text-left p-2 rounded text-sm transition-colors ${
                          currentContentId === content.id
                            ? 'bg-blue-50 text-blue-700 border border-blue-200'
                            : 'hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          <span className="text-xs text-gray-500">
                            {sectionIndex + 1}.{contentIndex + 1}
                          </span>
                          <span>{content.title}</span>
                          <span className="text-xs text-gray-400">
                            ({content.type})
                          </span>
                        </div>
                      </button>
                    ))}
                  </motion.div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 p-6 overflow-y-auto">
        {currentContent && (
          <div className="max-w-4xl">
            <div className="mb-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">
                {currentContent.title}
              </h1>
              {currentContent.description && (
                <p className="text-gray-600 mb-4">
                  {currentContent.description}
                </p>
              )}
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <span>📖 {currentContent.type}</span>
                {currentContent.duration && (
                  <span>⏱️ {Math.round(currentContent.duration / 60)} min</span>
                )}
                {currentContent.metadata?.difficulty && (
                  <span>📊 {currentContent.metadata.difficulty}</span>
                )}
              </div>
            </div>

            {renderContent(currentContent)}
          </div>
        )}

        {!currentContent && (
          <div className="flex items-center justify-center h-64 text-gray-500">
            <div className="text-center">
              <div className="text-6xl mb-4">📚</div>
              <p className="text-lg">Select a section to begin learning</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
