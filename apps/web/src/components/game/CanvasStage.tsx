import React, { useEffect, useRef, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  type GameScene,
  type GameManifest,
  type GameProgress,
  type GameInteraction,
  type GameAsset,
  type UIElement,
} from '../../api/gameClient'

interface CanvasStageProps {
  scene: GameScene
  gameManifest: GameManifest
  gameProgress: GameProgress
  isPaused: boolean
  onSceneComplete: (sceneId: string, results: any) => void
  onInteraction: (interactionType: string, data?: any) => void
  onError: (error: string) => void
}

interface InteractionState {
  selectedItems: string[]
  draggedItem: string | null
  inputValues: Record<string, string>
  completedInteractions: string[]
}

export const CanvasStage: React.FC<CanvasStageProps> = ({
  scene,
  gameManifest,
  gameProgress: _gameProgress,
  isPaused,
  onSceneComplete,
  onInteraction,
  onError: _onError,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [interactionState, setInteractionState] = useState<InteractionState>({
    selectedItems: [],
    draggedItem: null,
    inputValues: {},
    completedInteractions: [],
  })
  const [sceneStartTime] = useState<number>(Date.now())
  const [sceneScore, setSceneScore] = useState<number>(0)
  const [interactionCount, setInteractionCount] = useState<number>(0)
  const [correctAnswers, setCorrectAnswers] = useState<number>(0)
  const [showFeedback, setShowFeedback] = useState<string | null>(null)

  // Initialize scene
  useEffect(() => {
    if (!isPaused) {
      initializeScene()
    }
  }, [scene.id, isPaused])

  // Handle keyboard interactions
  useEffect(() => {
    if (!gameManifest.game_rules.keyboard_navigation || isPaused) return

    const handleKeyPress = (event: KeyboardEvent) => {
      // Find interactions with keyboard shortcuts
      const keyboardInteraction = scene.interactions.find(
        interaction => interaction.keyboard_shortcut === event.key.toLowerCase()
      )

      if (keyboardInteraction) {
        event.preventDefault()
        handleInteractionClick(keyboardInteraction)
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [
    scene.interactions,
    isPaused,
    gameManifest.game_rules.keyboard_navigation,
  ])

  const initializeScene = () => {
    setInteractionState({
      selectedItems: [],
      draggedItem: null,
      inputValues: {},
      completedInteractions: [],
    })
    setSceneScore(0)
    setInteractionCount(0)
    setCorrectAnswers(0)
    setShowFeedback(null)

    // Initialize canvas if needed
    if (canvasRef.current && scene.type === 'gameplay') {
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (ctx) {
        // Set canvas size
        canvas.width = 800
        canvas.height = 600

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height)

        // Draw background if specified
        if (scene.background) {
          const img = new Image()
          img.onload = () => {
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
          }
          img.onerror = () => {
            console.warn('Failed to load scene background:', scene.background)
          }
          img.src = scene.background
        }
      }
    }
  }

  const handleInteractionClick = useCallback(
    (interaction: GameInteraction) => {
      if (
        isPaused ||
        interactionState.completedInteractions.includes(interaction.id)
      ) {
        return
      }

      setInteractionCount(prev => prev + 1)

      switch (interaction.type) {
        case 'click':
          handleClickInteraction(interaction)
          break
        case 'select':
          handleSelectInteraction(interaction)
          break
        case 'drag':
          handleDragInteraction(interaction)
          break
        default:
          console.warn('Unsupported interaction type:', interaction.type)
      }

      // Notify parent of interaction
      onInteraction(interaction.type, {
        interaction_id: interaction.id,
        action: interaction.action,
        timestamp: Date.now(),
      })
    },
    [isPaused, interactionState.completedInteractions, onInteraction]
  )

  const handleClickInteraction = (interaction: GameInteraction) => {
    const isCorrect = Math.random() > 0.3 // Simulate correctness based on game logic

    if (isCorrect) {
      setCorrectAnswers(prev => prev + 1)
      setSceneScore(prev => prev + (interaction.points || 10))
      setShowFeedback(interaction.feedback || 'Correct!')
    } else {
      setShowFeedback('Try again!')
      onInteraction('mistake', { interaction_id: interaction.id })
    }

    // Mark interaction as completed if correct
    if (isCorrect) {
      setInteractionState(prev => ({
        ...prev,
        completedInteractions: [...prev.completedInteractions, interaction.id],
      }))
    }

    // Clear feedback after delay
    setTimeout(() => setShowFeedback(null), 2000)

    // Check if scene is complete
    checkSceneCompletion()
  }

  const handleSelectInteraction = (interaction: GameInteraction) => {
    setInteractionState(prev => ({
      ...prev,
      selectedItems: prev.selectedItems.includes(interaction.target)
        ? prev.selectedItems.filter(item => item !== interaction.target)
        : [...prev.selectedItems, interaction.target],
    }))

    // Auto-complete selection interactions
    setTimeout(() => {
      setInteractionState(prev => ({
        ...prev,
        completedInteractions: [...prev.completedInteractions, interaction.id],
      }))
      setSceneScore(prev => prev + (interaction.points || 5))
      checkSceneCompletion()
    }, 500)
  }

  const handleDragInteraction = (interaction: GameInteraction) => {
    // Simplified drag handling - mark as completed immediately
    setInteractionState(prev => ({
      ...prev,
      draggedItem: interaction.target,
      completedInteractions: [...prev.completedInteractions, interaction.id],
    }))

    setSceneScore(prev => prev + (interaction.points || 15))
    setShowFeedback('Great move!')
    setTimeout(() => setShowFeedback(null), 2000)

    checkSceneCompletion()
  }

  const handleInputChange = (inputId: string, value: string) => {
    setInteractionState(prev => ({
      ...prev,
      inputValues: {
        ...prev.inputValues,
        [inputId]: value,
      },
    }))
  }

  const handleInputSubmit = (interaction: GameInteraction) => {
    const inputValue = interactionState.inputValues[interaction.target] || ''
    const isCorrect =
      inputValue.toLowerCase().trim() ===
      (interaction.action || '').toLowerCase().trim()

    if (isCorrect) {
      setCorrectAnswers(prev => prev + 1)
      setSceneScore(prev => prev + (interaction.points || 20))
      setShowFeedback(interaction.feedback || 'Correct answer!')

      setInteractionState(prev => ({
        ...prev,
        completedInteractions: [...prev.completedInteractions, interaction.id],
      }))
    } else {
      setShowFeedback('Incorrect. Try again!')
      onInteraction('mistake', {
        interaction_id: interaction.id,
        attempted_answer: inputValue,
      })
    }

    setTimeout(() => setShowFeedback(null), 2000)
    checkSceneCompletion()
  }

  const checkSceneCompletion = () => {
    const requiredInteractions = scene.interactions.filter(
      i => i.required !== false
    )
    const completedRequired = requiredInteractions.filter(i =>
      interactionState.completedInteractions.includes(i.id)
    ).length

    // Check if scene completion criteria is met
    if (scene.success_criteria) {
      const { type, target_value, operator } = scene.success_criteria
      let criteriaMet = false

      switch (type) {
        case 'completion':
          criteriaMet = completedRequired >= target_value
          break
        case 'score':
          criteriaMet =
            operator === 'gte'
              ? sceneScore >= target_value
              : sceneScore === target_value
          break
        case 'accuracy':
          const accuracy =
            interactionCount > 0 ? (correctAnswers / interactionCount) * 100 : 0
          criteriaMet = accuracy >= target_value
          break
        case 'time':
          const elapsedSeconds = Math.floor(
            (Date.now() - sceneStartTime) / 1000
          )
          criteriaMet =
            operator === 'lte'
              ? elapsedSeconds <= target_value
              : elapsedSeconds >= target_value
          break
      }

      if (criteriaMet) {
        completeScene()
      }
    } else if (completedRequired === requiredInteractions.length) {
      // Default: complete when all required interactions are done
      completeScene()
    }
  }

  const completeScene = () => {
    const sceneDuration = Math.floor((Date.now() - sceneStartTime) / 1000)
    const accuracy =
      interactionCount > 0 ? (correctAnswers / interactionCount) * 100 : 100

    const sceneResults = {
      scene_id: scene.id,
      score: sceneScore,
      duration_seconds: sceneDuration,
      interactions: interactionCount,
      accuracy,
      correct_answers: correctAnswers,
      completed_at: new Date().toISOString(),
    }

    onSceneComplete(scene.id, sceneResults)
  }

  const renderAsset = (asset: GameAsset, index: number) => {
    switch (asset.type) {
      case 'image':
        return (
          <img
            key={asset.id}
            src={asset.url}
            alt={asset.metadata?.alt || `Asset ${index + 1}`}
            className="max-w-full h-auto rounded-lg shadow-md"
            style={{
              width: asset.metadata?.width || 'auto',
              height: asset.metadata?.height || 'auto',
            }}
          />
        )
      case 'text':
        return (
          <div
            key={asset.id}
            className="text-white p-4 rounded-lg bg-black bg-opacity-50"
            style={{
              fontSize: asset.metadata?.fontSize || '1rem',
              color: asset.metadata?.color || 'white',
            }}
          >
            {asset.content}
          </div>
        )
      case 'audio':
        return (
          <audio
            key={asset.id}
            controls
            className="w-full"
            autoPlay={asset.metadata?.autoplay}
          >
            <source src={asset.url} type="audio/mpeg" />
            Your browser does not support audio playback.
          </audio>
        )
      case 'video':
        return (
          <video
            key={asset.id}
            controls
            className="w-full rounded-lg"
            autoPlay={asset.metadata?.autoplay}
            muted={asset.metadata?.muted}
          >
            <source src={asset.url} type="video/mp4" />
            Your browser does not support video playback.
          </video>
        )
      default:
        return null
    }
  }

  const renderInteraction = (interaction: GameInteraction) => {
    const isCompleted = interactionState.completedInteractions.includes(
      interaction.id
    )
    const isSelected = interactionState.selectedItems.includes(
      interaction.target
    )

    switch (interaction.type) {
      case 'click':
        return (
          <button
            key={interaction.id}
            onClick={() => handleInteractionClick(interaction)}
            disabled={isCompleted || isPaused}
            className={`
              px-4 py-2 rounded-lg transition-all duration-200
              ${
                isCompleted
                  ? 'bg-green-600 text-white cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white hover:scale-105'
              }
              ${isPaused ? 'opacity-50 cursor-not-allowed' : ''}
            `}
            data-testid={`interaction-${interaction.id}`}
          >
            {interaction.action}
            {interaction.keyboard_shortcut && (
              <span className="ml-2 text-xs opacity-75">
                [{interaction.keyboard_shortcut.toUpperCase()}]
              </span>
            )}
          </button>
        )

      case 'select':
        return (
          <button
            key={interaction.id}
            onClick={() => handleInteractionClick(interaction)}
            disabled={isCompleted || isPaused}
            className={`
              px-3 py-2 border-2 rounded-lg transition-all duration-200
              ${
                isSelected
                  ? 'border-yellow-400 bg-yellow-100 text-yellow-800'
                  : 'border-gray-400 text-white hover:border-yellow-300'
              }
              ${isCompleted ? 'border-green-400 bg-green-100 text-green-800' : ''}
              ${isPaused ? 'opacity-50 cursor-not-allowed' : ''}
            `}
            data-testid={`interaction-${interaction.id}`}
          >
            {interaction.action}
          </button>
        )

      case 'type':
        return (
          <div key={interaction.id} className="flex flex-col space-y-2">
            <label className="text-white text-sm">{interaction.action}</label>
            <div className="flex space-x-2">
              <input
                type="text"
                value={interactionState.inputValues[interaction.target] || ''}
                onChange={e =>
                  handleInputChange(interaction.target, e.target.value)
                }
                disabled={isCompleted || isPaused}
                placeholder="Type your answer..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                data-testid={`input-${interaction.id}`}
              />
              <button
                onClick={() => handleInputSubmit(interaction)}
                disabled={isCompleted || isPaused}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md transition-colors"
              >
                Submit
              </button>
            </div>
          </div>
        )

      case 'drag':
        return (
          <div
            key={interaction.id}
            draggable={!isCompleted && !isPaused}
            onDragStart={() => handleInteractionClick(interaction)}
            className={`
              px-4 py-2 rounded-lg cursor-move transition-all duration-200
              ${
                isCompleted
                  ? 'bg-green-600 text-white'
                  : 'bg-purple-600 hover:bg-purple-700 text-white hover:scale-105'
              }
              ${isPaused ? 'opacity-50 cursor-not-allowed' : ''}
            `}
            data-testid={`interaction-${interaction.id}`}
          >
            {interaction.action}
            <span className="ml-2 text-xs">📌</span>
          </div>
        )

      default:
        return null
    }
  }

  const renderUIElement = (element: UIElement) => {
    const style = {
      position: 'absolute' as const,
      left: element.position.x,
      top: element.position.y,
      width: element.size?.width || 'auto',
      height: element.size?.height || 'auto',
      ...element.properties.style,
    }

    switch (element.type) {
      case 'button':
        return (
          <button
            key={element.id}
            style={style}
            className={
              element.properties.className ||
              'px-4 py-2 bg-blue-600 text-white rounded-lg'
            }
            onClick={element.properties.onClick}
          >
            {element.properties.text}
          </button>
        )
      case 'text':
        return (
          <div
            key={element.id}
            style={style}
            className={element.properties.className || 'text-white'}
          >
            {element.properties.text}
          </div>
        )
      case 'progress':
        return (
          <div
            key={element.id}
            style={style}
            className="bg-gray-700 rounded-full"
          >
            <div
              className="bg-blue-600 rounded-full h-full transition-all duration-300"
              style={{ width: `${element.properties.value || 0}%` }}
            />
          </div>
        )
      default:
        return null
    }
  }

  if (isPaused) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-white">
          <div className="text-4xl mb-4">⏸️</div>
          <h3 className="text-xl font-semibold mb-2">Scene Paused</h3>
          <p className="text-gray-300">Resume the game to continue</p>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-hidden"
      data-testid="canvas-stage"
    >
      {/* Scene Header */}
      <div className="absolute top-4 left-4 right-4 z-20">
        <div className="bg-black bg-opacity-50 rounded-lg p-4">
          <h2 className="text-xl font-bold text-white mb-2">{scene.title}</h2>
          {scene.description && (
            <p className="text-gray-300 text-sm">{scene.description}</p>
          )}
        </div>
      </div>

      {/* Main Canvas/Content Area */}
      <div className="h-full flex flex-col items-center justify-center pt-20 pb-20">
        {scene.type === 'gameplay' && (
          <canvas
            ref={canvasRef}
            className="border border-gray-600 rounded-lg bg-gray-800"
            style={{ maxWidth: '100%', maxHeight: '60%' }}
          />
        )}

        {/* Scene Assets */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 max-w-6xl">
          {scene.assets.map((asset, index) => renderAsset(asset, index))}
        </div>

        {/* Scene Interactions */}
        <div className="flex flex-wrap gap-4 p-4 justify-center max-w-4xl">
          {scene.interactions.map(interaction =>
            renderInteraction(interaction)
          )}
        </div>
      </div>

      {/* UI Elements */}
      {scene.ui_elements?.map(renderUIElement)}

      {/* Feedback Display */}
      <AnimatePresence>
        {showFeedback && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="absolute top-1/4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-6 py-3 rounded-lg shadow-lg z-30"
          >
            {showFeedback}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Scene Progress */}
      <div className="absolute bottom-4 left-4 right-4 z-20">
        <div className="bg-black bg-opacity-50 rounded-lg p-3">
          <div className="flex justify-between items-center text-white text-sm">
            <span>Score: {sceneScore}</span>
            <span>Interactions: {interactionCount}</span>
            <span>
              Progress: {interactionState.completedInteractions.length}/
              {scene.interactions.length}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
