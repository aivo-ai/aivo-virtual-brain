import React from 'react'
import { LibraryAsset } from '../../pages/library/Index'

interface AssetCardProps {
  asset: LibraryAsset
  onAttachToLearner?: (assetId: string) => void
  onRemoveFromLearner?: (assetId: string) => void
}

export const AssetCard: React.FC<AssetCardProps> = ({
  asset,
  onAttachToLearner,
  onRemoveFromLearner,
}) => {
  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    } catch {
      return 'Unknown date'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'lesson':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
            />
          </svg>
        )
      case 'document':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        )
      case 'image':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
        )
      case 'video':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        )
      case 'audio':
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"
            />
          </svg>
        )
      default:
        return (
          <svg
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        )
    }
  }

  const getSourceBadgeColor = (source: string) => {
    switch (source) {
      case 'lessons':
        return 'bg-blue-100 text-blue-800'
      case 'coursework':
        return 'bg-green-100 text-green-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const handleAttachmentToggle = () => {
    if (asset.attachedToLearner) {
      onRemoveFromLearner?.(asset.id)
    } else {
      onAttachToLearner?.(asset.id)
    }
  }

  return (
    <div className="group relative overflow-hidden rounded-lg bg-white shadow-sm ring-1 ring-gray-900/5 transition-all hover:shadow-md hover:ring-gray-900/10">
      {/* Thumbnail/Preview */}
      <div className="aspect-w-16 aspect-h-10 bg-gray-100">
        {asset.thumbnail ? (
          <img
            src={asset.thumbnail}
            alt={asset.title}
            className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-200"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100">
            <div className="text-gray-400">{getTypeIcon(asset.type)}</div>
          </div>
        )}

        {/* Source Badge */}
        <div className="absolute top-2 left-2">
          <span
            className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${getSourceBadgeColor(asset.source)}`}
          >
            {asset.source === 'lessons' ? 'Lesson' : 'Coursework'}
          </span>
        </div>

        {/* Attachment Status */}
        {asset.attachedToLearner && (
          <div className="absolute top-2 right-2">
            <div className="rounded-full bg-green-100 p-1">
              <svg
                className="h-4 w-4 text-green-600"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-2 mb-2">
          <h3 className="text-sm font-medium text-gray-900 line-clamp-2 group-hover:text-blue-600 transition-colors">
            <a
              href={`/library/${asset.source}/${asset.id}`}
              className="focus:outline-none"
              aria-label={`View details for ${asset.title}`}
            >
              <span className="absolute inset-0" aria-hidden="true" />
              {asset.title}
            </a>
          </h3>
          <div className="text-gray-400 flex-shrink-0">
            {getTypeIcon(asset.type)}
          </div>
        </div>

        {asset.description && (
          <p className="text-sm text-gray-600 line-clamp-2 mb-3">
            {asset.description}
          </p>
        )}

        {/* Metadata */}
        <div className="space-y-1 mb-3">
          {asset.subject && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <span className="font-medium">Subject:</span>
              <span>{asset.subject}</span>
            </div>
          )}
          {asset.topic && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <span className="font-medium">Topic:</span>
              <span>{asset.topic}</span>
            </div>
          )}
          {asset.gradeBand && (
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <span className="font-medium">Grade:</span>
              <span>{asset.gradeBand}</span>
            </div>
          )}
        </div>

        {/* Tags */}
        {asset.tags.length > 0 && (
          <div className="mb-3">
            <div className="flex flex-wrap gap-1">
              {asset.tags.slice(0, 3).map((tag, index) => (
                <span
                  key={index}
                  className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800"
                >
                  {tag}
                </span>
              ))}
              {asset.tags.length > 3 && (
                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-500">
                  +{asset.tags.length - 3}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between">
          <time className="text-xs text-gray-500" dateTime={asset.createdAt}>
            {formatDate(asset.createdAt)}
          </time>

          {/* Action Button */}
          {asset.source === 'coursework' &&
            (onAttachToLearner || onRemoveFromLearner) && (
              <button
                onClick={e => {
                  e.preventDefault()
                  e.stopPropagation()
                  handleAttachmentToggle()
                }}
                className={`relative z-10 inline-flex items-center rounded-md px-2 py-1 text-xs font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                  asset.attachedToLearner
                    ? 'bg-green-100 text-green-800 hover:bg-green-200 focus:ring-green-500'
                    : 'bg-blue-100 text-blue-800 hover:bg-blue-200 focus:ring-blue-500'
                }`}
                aria-label={
                  asset.attachedToLearner
                    ? 'Remove from learner'
                    : 'Attach to learner'
                }
              >
                {asset.attachedToLearner ? (
                  <>
                    <svg
                      className="mr-1 h-3 w-3"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Attached
                  </>
                ) : (
                  <>
                    <svg
                      className="mr-1 h-3 w-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                      />
                    </svg>
                    Attach
                  </>
                )}
              </button>
            )}
        </div>
      </div>
    </div>
  )
}

export default AssetCard
