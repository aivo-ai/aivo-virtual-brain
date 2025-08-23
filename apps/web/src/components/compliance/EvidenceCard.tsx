/**
 * EvidenceCard Component (S5-09)
 *
 * Reusable card component for displaying compliance evidence metrics
 * with optional progress bars and status indicators.
 */

import React from 'react'
import { Card } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EvidenceCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: React.ReactNode
  color?: 'primary' | 'secondary' | 'success' | 'warning' | 'error' | 'info'
  progress?: number // 0-100
  trend?: 'up' | 'down' | 'flat'
  trendValue?: string
  onClick?: () => void
  loading?: boolean
  size?: 'small' | 'medium' | 'large'
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  color = 'primary',
  progress,
  trend,
  trendValue,
  onClick,
  loading = false,
  size = 'medium',
}) => {
  // Get size-based styling
  const getSizeClasses = () => {
    switch (size) {
      case 'small':
        return 'p-4'
      case 'large':
        return 'p-8'
      default:
        return 'p-6'
    }
  }

  // Get color classes
  const getColorClasses = () => {
    const colorMap = {
      primary: 'border-blue-200 bg-blue-50',
      secondary: 'border-gray-200 bg-gray-50',
      success: 'border-green-200 bg-green-50',
      warning: 'border-yellow-200 bg-yellow-50',
      error: 'border-red-200 bg-red-50',
      info: 'border-blue-200 bg-blue-50',
    }
    return colorMap[color]
  }

  // Get trend icon
  const getTrendIcon = () => {
    if (!trend) return null

    const trendConfig = {
      up: { icon: TrendingUp, color: 'text-green-600' },
      down: { icon: TrendingDown, color: 'text-red-600' },
      flat: { icon: Minus, color: 'text-gray-600' },
    }

    const config = trendConfig[trend]
    const TrendIcon = config.icon

    return (
      <div className={cn('flex items-center gap-1', config.color)}>
        <TrendIcon className="h-4 w-4" />
        {trendValue && (
          <span className="text-sm font-medium">{trendValue}</span>
        )}
      </div>
    )
  }

  const valueTextSize =
    size === 'large' ? 'text-3xl' : size === 'small' ? 'text-xl' : 'text-2xl'

  return (
    <div
      className={cn(
        'transition-all duration-200 hover:shadow-md',
        onClick && 'cursor-pointer hover:scale-105'
      )}
      onClick={onClick}
    >
      <Card className={cn(getSizeClasses(), getColorClasses())}>
        {/* Color accent bar */}
        <div
          className={cn(
            'absolute top-0 left-0 right-0 h-1 rounded-t-lg',
            color === 'success'
              ? 'bg-green-500'
              : color === 'warning'
                ? 'bg-yellow-500'
                : color === 'error'
                  ? 'bg-red-500'
                  : color === 'info'
                    ? 'bg-blue-500'
                    : 'bg-blue-500'
          )}
        />

        {/* Header with icon and title */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {icon && (
              <div
                className={cn(
                  'p-2 rounded-full',
                  color === 'success'
                    ? 'bg-green-100 text-green-600'
                    : color === 'warning'
                      ? 'bg-yellow-100 text-yellow-600'
                      : color === 'error'
                        ? 'bg-red-100 text-red-600'
                        : color === 'info'
                          ? 'bg-blue-100 text-blue-600'
                          : 'bg-blue-100 text-blue-600'
                )}
              >
                {icon}
              </div>
            )}
            <h3 className="text-sm font-medium text-gray-600">{title}</h3>
          </div>
          {getTrendIcon()}
        </div>

        {/* Main value */}
        <div className="mb-4">
          <span
            className={cn(
              'font-bold',
              valueTextSize,
              color === 'success'
                ? 'text-green-600'
                : color === 'warning'
                  ? 'text-yellow-600'
                  : color === 'error'
                    ? 'text-red-600'
                    : color === 'info'
                      ? 'text-blue-600'
                      : 'text-blue-600',
              loading && 'opacity-50'
            )}
          >
            {loading ? '---' : value}
          </span>
        </div>

        {/* Progress bar */}
        {progress !== undefined && (
          <div className="mb-3">
            <Progress value={loading ? undefined : progress} className="h-2" />
            {!loading && (
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0%</span>
                <span>{Math.round(progress)}%</span>
                <span>100%</span>
              </div>
            )}
          </div>
        )}

        {/* Subtitle */}
        {subtitle && (
          <p className={cn('text-sm text-gray-500', loading && 'opacity-50')}>
            {subtitle}
          </p>
        )}
      </Card>
    </div>
  )
}
