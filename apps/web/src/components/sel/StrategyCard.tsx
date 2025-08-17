/**
 * S3-13 StrategyCard Component
 * Interactive card for SEL strategies with effectiveness tracking
 */

import { useState, useCallback } from 'react'
import {
  SELStrategy,
  StrategyCategory,
  useSELMutations,
} from '../../api/selClient'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Progress } from '../ui/Progress'
import { Play, Clock, Star, CheckCircle, Heart } from '../ui/Icons'

interface StrategyCardProps {
  strategy: SELStrategy
  studentId: string
  onUse?: (strategy: SELStrategy) => void
  className?: string
}

const getCategoryIcon = (category: StrategyCategory) => {
  switch (category) {
    case StrategyCategory.MINDFULNESS:
      return '🧘'
    case StrategyCategory.BREATHING:
      return '💨'
    case StrategyCategory.MOVEMENT:
      return '🏃'
    case StrategyCategory.COGNITIVE:
      return '🧠'
    case StrategyCategory.SOCIAL:
      return '👥'
    case StrategyCategory.CREATIVE:
      return '🎨'
    default:
      return '✨'
  }
}

const getCategoryColor = (category: StrategyCategory) => {
  switch (category) {
    case StrategyCategory.MINDFULNESS:
      return 'bg-purple-100 text-purple-800 border-purple-200'
    case StrategyCategory.BREATHING:
      return 'bg-blue-100 text-blue-800 border-blue-200'
    case StrategyCategory.MOVEMENT:
      return 'bg-green-100 text-green-800 border-green-200'
    case StrategyCategory.COGNITIVE:
      return 'bg-orange-100 text-orange-800 border-orange-200'
    case StrategyCategory.SOCIAL:
      return 'bg-pink-100 text-pink-800 border-pink-200'
    case StrategyCategory.CREATIVE:
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200'
  }
}

export function StrategyCard({
  strategy,
  studentId,
  onUse,
  className = '',
}: StrategyCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isUsing, setIsUsing] = useState(false)
  const [showEffectivenessRating, setShowEffectivenessRating] = useState(false)
  const [effectivenessRating, setEffectivenessRating] = useState(0)

  const { useStrategy: useStrategyMutation, loading } = useSELMutations()

  const handleUseStrategy = useCallback(async () => {
    setIsUsing(true)
    try {
      await useStrategyMutation(strategy.id, studentId)
      setShowEffectivenessRating(true)
      onUse?.(strategy)
    } catch (error) {
      console.error('Failed to use strategy:', error)
    } finally {
      setIsUsing(false)
    }
  }, [useStrategyMutation, strategy.id, studentId, onUse, strategy])

  const handleEffectivenessRating = useCallback(
    async (rating: number) => {
      try {
        await useStrategyMutation(strategy.id, studentId, rating)
        setEffectivenessRating(rating)
        setShowEffectivenessRating(false)
      } catch (error) {
        console.error('Failed to rate effectiveness:', error)
      }
    },
    [useStrategyMutation, strategy.id, studentId]
  )

  const formatDuration = (minutes: number) => {
    if (minutes < 60) {
      return `${minutes}m`
    }
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`
  }

  return (
    <Card
      className={`transition-all duration-200 hover:shadow-md ${className} ${
        strategy.isRecommended ? 'ring-2 ring-blue-500 ring-opacity-50' : ''
      }`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2 text-lg">
              <span className="text-2xl">
                {getCategoryIcon(strategy.category)}
              </span>
              {strategy.title}
              {strategy.isRecommended && (
                <Badge variant="default" className="bg-blue-100 text-blue-800">
                  Recommended
                </Badge>
              )}
            </CardTitle>
            <div className="flex items-center gap-2 mt-2">
              <Badge className={getCategoryColor(strategy.category)}>
                {strategy.category.replace('_', ' ')}
              </Badge>
              <div className="flex items-center gap-1 text-sm text-gray-500">
                <Clock className="w-3 h-3" />
                {formatDuration(strategy.estimatedDuration)}
              </div>
              <div className="flex items-center gap-1 text-sm text-gray-500">
                <Star className="w-3 h-3" />
                {strategy.effectiveness.toFixed(1)}
              </div>
            </div>
          </div>

          {strategy.iconUrl && (
            <img
              src={strategy.iconUrl}
              alt={strategy.title}
              className="w-12 h-12 rounded-lg object-cover"
            />
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <p className="text-gray-600">{strategy.description}</p>

        {/* Tags */}
        {strategy.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {strategy.tags.map(tag => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Usage Stats */}
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>Used {strategy.timesUsed} times</span>
          {strategy.lastUsed && (
            <span>
              Last used: {new Date(strategy.lastUsed).toLocaleDateString()}
            </span>
          )}
        </div>

        {/* Effectiveness Progress */}
        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">Effectiveness</span>
            <span className="font-medium">{strategy.effectiveness}/5</span>
          </div>
          <Progress
            value={(strategy.effectiveness / 5) * 100}
            className="h-2"
          />
        </div>

        {/* Instructions (Expandable) */}
        {strategy.instructions.length > 0 && (
          <div className="space-y-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              {isExpanded ? 'Hide' : 'Show'} Instructions
            </button>

            {isExpanded && (
              <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                <ol className="list-decimal list-inside space-y-1 text-sm">
                  {strategy.instructions.map((instruction, index) => (
                    <li key={index} className="text-gray-700">
                      {instruction}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )}

        {/* Media */}
        {(strategy.videoUrl || strategy.audioUrl) && (
          <div className="flex gap-2">
            {strategy.videoUrl && (
              <a
                href={strategy.videoUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
              >
                <Play className="w-4 h-4" />
                Watch Video
              </a>
            )}
            {strategy.audioUrl && (
              <a
                href={strategy.audioUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800"
              >
                <Play className="w-4 h-4" />
                Listen
              </a>
            )}
          </div>
        )}

        {/* Effectiveness Rating */}
        {showEffectivenessRating && (
          <div className="bg-blue-50 rounded-lg p-4 space-y-3">
            <p className="text-sm font-medium text-blue-900">
              How helpful was this strategy?
            </p>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map(rating => (
                <button
                  key={rating}
                  onClick={() => handleEffectivenessRating(rating)}
                  className="flex items-center justify-center w-8 h-8 rounded-full border-2 border-blue-500 hover:bg-blue-100 transition-colors"
                >
                  <Heart
                    className={`w-4 h-4 ${
                      rating <= effectivenessRating
                        ? 'text-red-500 fill-current'
                        : 'text-gray-400'
                    }`}
                  />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          <Button
            onClick={handleUseStrategy}
            disabled={loading || isUsing}
            className="flex-1 flex items-center justify-center gap-2"
          >
            {isUsing ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <CheckCircle className="w-4 h-4" />
            )}
            Try This Strategy
          </Button>

          {isExpanded && (
            <Button
              variant="outline"
              onClick={() => setIsExpanded(false)}
              className="px-3"
            >
              <span className="sr-only">Collapse</span>↑
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
