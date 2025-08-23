import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { courseworkClient } from '../../api/courseworkClient'
import { lessonRegistryClient } from '../../api/lessonRegistryClient'

interface AssetDetail {
  id: string
  title: string
  description?: string
  type: string
  source: 'lessons' | 'coursework'
  subject?: string
  topic?: string
  gradeBand?: string
  tags: string[]
  url?: string
  thumbnailUrl?: string
  createdAt: string
  updatedAt?: string
  attachedToLearner?: boolean
  metadata?: {
    fileSize?: number
    duration?: number
    pages?: number
    language?: string
    author?: string
  }
}

const Detail: React.FC = () => {
  const { source, id } = useParams<{
    source: 'lessons' | 'coursework'
    id: string
  }>()
  const [asset, setAsset] = useState<AssetDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [attachmentLoading, setAttachmentLoading] = useState(false)
  const [linkbackModalOpen, setLinkbackModalOpen] = useState(false)
  const [availableLessons, setAvailableLessons] = useState<any[]>([])
  const [linkedLessons, setLinkedLessons] = useState<any[]>([])
  const [linkbackLoading, setLinkbackLoading] = useState(false)

  useEffect(() => {
    if (source && id) {
      loadAsset()
    }
  }, [source, id])

  const loadAsset = async () => {
    if (!source || !id) return

    setLoading(true)
    setError(null)

    try {
      let assetData: AssetDetail

      if (source === 'lessons') {
        const lesson = await lessonRegistryClient.getLesson(id)
        assetData = {
          id: lesson.id,
          title: lesson.title,
          description: lesson.description,
          type: 'lesson',
          source: 'lessons',
          subject: lesson.subject,
          topic: lesson.topics?.[0],
          gradeBand: lesson.gradeBand,
          tags: lesson.tags || [],
          url: lesson.contentUrl,
          thumbnailUrl: lesson.thumbnailUrl,
          createdAt: lesson.createdAt,
          updatedAt: lesson.updatedAt,
          attachedToLearner: false, // Would need to check learner data
          metadata: {
            author: lesson.author,
            duration: lesson.estimatedDuration,
            language: lesson.language,
          },
        }
      } else {
        const courseworkAsset = await courseworkClient.getAsset(id)
        assetData = {
          id: courseworkAsset.id,
          title: courseworkAsset.title,
          description: courseworkAsset.description,
          type: courseworkAsset.type,
          source: 'coursework',
          subject: courseworkAsset.metadata?.subject,
          topic: courseworkAsset.metadata?.topic,
          gradeBand: courseworkAsset.metadata?.gradeBand,
          tags: courseworkAsset.tags || [],
          url: courseworkAsset.url,
          thumbnailUrl: courseworkAsset.thumbnailUrl,
          createdAt: courseworkAsset.createdAt,
          updatedAt: courseworkAsset.updatedAt,
          attachedToLearner: courseworkAsset.attachedToLearner,
          metadata: {
            fileSize: courseworkAsset.fileSize,
            pages: courseworkAsset.metadata?.pages,
            language: courseworkAsset.metadata?.language,
            author: courseworkAsset.metadata?.author,
          },
        }
      }

      setAsset(assetData)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load asset details'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleAttachmentToggle = async () => {
    if (!asset || asset.source !== 'coursework') return

    setAttachmentLoading(true)
    try {
      if (asset.attachedToLearner) {
        await courseworkClient.detachFromLearner(asset.id, 'current-learner') // Would need actual learner ID
      } else {
        await courseworkClient.attachToLearner(asset.id, 'current-learner') // Would need actual learner ID
      }

      // Update local state
      setAsset(prev =>
        prev ? { ...prev, attachedToLearner: !prev.attachedToLearner } : null
      )
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to update attachment'
      )
    } finally {
      setAttachmentLoading(false)
    }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDuration = (minutes: number): string => {
    if (minutes < 60) return `${minutes} min`
    const hours = Math.floor(minutes / 60)
    const remainingMinutes = minutes % 60
    return `${hours}h ${remainingMinutes}m`
  }

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return 'Unknown date'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading asset details...</p>
        </div>
      </div>
    )
  }

  if (error || !asset) {
    return (
      <div className="min-h-screen bg-gray-50 px-4 py-8">
        <div className="mx-auto max-w-4xl">
          <div className="rounded-lg bg-red-50 p-4">
            <h3 className="text-lg font-medium text-red-800">
              Error Loading Asset
            </h3>
            <p className="mt-1 text-sm text-red-700">
              {error || 'Asset not found'}
            </p>
            <div className="mt-4 flex space-x-3">
              <button
                onClick={loadAsset}
                className="rounded-md bg-red-100 px-3 py-2 text-sm font-medium text-red-800 hover:bg-red-200"
              >
                Retry
              </button>
              <a
                href="/library"
                className="rounded-md bg-gray-100 px-3 py-2 text-sm font-medium text-gray-800 hover:bg-gray-200"
              >
                Back to Library
              </a>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-4xl px-4">
        {/* Breadcrumb */}
        <div className="mb-6">
          <nav className="flex items-center space-x-2 text-sm text-gray-500">
            <a href="/library" className="hover:text-gray-700">
              Library
            </a>
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
            <span className="text-gray-900">{asset.title}</span>
          </nav>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Header */}
            <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                        asset.source === 'lessons'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-green-100 text-green-800'
                      }`}
                    >
                      {asset.source === 'lessons' ? 'Lesson' : 'Coursework'}
                    </span>
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-1 text-xs font-medium text-gray-800">
                      {asset.type}
                    </span>
                    {asset.attachedToLearner && (
                      <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-1 text-xs font-medium text-green-800">
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
                      </span>
                    )}
                  </div>
                  <h1 className="text-2xl font-bold text-gray-900 mb-2">
                    {asset.title}
                  </h1>
                  {asset.description && (
                    <p className="text-gray-600">{asset.description}</p>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex flex-wrap gap-3">
                {asset.url && (
                  <a
                    href={asset.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                  >
                    <svg
                      className="mr-1.5 h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                      />
                    </svg>
                    View Asset
                  </a>
                )}

                {asset.source === 'coursework' && (
                  <button
                    onClick={handleAttachmentToggle}
                    disabled={attachmentLoading}
                    className={`inline-flex items-center rounded-md px-3 py-2 text-sm font-semibold transition-colors disabled:opacity-50 ${
                      asset.attachedToLearner
                        ? 'bg-green-100 text-green-800 hover:bg-green-200'
                        : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                    }`}
                  >
                    {attachmentLoading ? (
                      <div className="mr-1.5 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"></div>
                    ) : asset.attachedToLearner ? (
                      <svg
                        className="mr-1.5 h-4 w-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : (
                      <svg
                        className="mr-1.5 h-4 w-4"
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
                    )}
                    {asset.attachedToLearner
                      ? 'Detach from Learner'
                      : 'Attach to Learner'}
                  </button>
                )}
              </div>
            </div>

            {/* Preview */}
            {asset.thumbnailUrl && (
              <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">
                  Preview
                </h2>
                <div className="aspect-w-16 aspect-h-9 bg-gray-100 rounded-lg overflow-hidden">
                  <img
                    src={asset.thumbnailUrl}
                    alt={asset.title}
                    className="w-full h-full object-cover"
                  />
                </div>
              </div>
            )}

            {/* Tags */}
            {asset.tags.length > 0 && (
              <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-6">
                <h2 className="text-lg font-medium text-gray-900 mb-4">Tags</h2>
                <div className="flex flex-wrap gap-2">
                  {asset.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center rounded-full bg-blue-100 px-3 py-1 text-sm font-medium text-blue-800"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Metadata */}
            <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">
                Details
              </h2>
              <dl className="space-y-3">
                {asset.subject && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Subject
                    </dt>
                    <dd className="text-sm text-gray-900">{asset.subject}</dd>
                  </div>
                )}
                {asset.topic && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Topic</dt>
                    <dd className="text-sm text-gray-900">{asset.topic}</dd>
                  </div>
                )}
                {asset.gradeBand && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Grade Band
                    </dt>
                    <dd className="text-sm text-gray-900">
                      Grade {asset.gradeBand}
                    </dd>
                  </div>
                )}
                {asset.metadata?.fileSize && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      File Size
                    </dt>
                    <dd className="text-sm text-gray-900">
                      {formatFileSize(asset.metadata.fileSize)}
                    </dd>
                  </div>
                )}
                {asset.metadata?.duration && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Duration
                    </dt>
                    <dd className="text-sm text-gray-900">
                      {formatDuration(asset.metadata.duration)}
                    </dd>
                  </div>
                )}
                {asset.metadata?.pages && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">Pages</dt>
                    <dd className="text-sm text-gray-900">
                      {asset.metadata.pages}
                    </dd>
                  </div>
                )}
                {asset.metadata?.language && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Language
                    </dt>
                    <dd className="text-sm text-gray-900">
                      {asset.metadata.language}
                    </dd>
                  </div>
                )}
                {asset.metadata?.author && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Author
                    </dt>
                    <dd className="text-sm text-gray-900">
                      {asset.metadata.author}
                    </dd>
                  </div>
                )}
                <div>
                  <dt className="text-sm font-medium text-gray-500">Created</dt>
                  <dd className="text-sm text-gray-900">
                    {formatDate(asset.createdAt)}
                  </dd>
                </div>
                {asset.updatedAt && asset.updatedAt !== asset.createdAt && (
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      Last Updated
                    </dt>
                    <dd className="text-sm text-gray-900">
                      {formatDate(asset.updatedAt)}
                    </dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Related Actions */}
            <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">
                Actions
              </h2>
              <div className="space-y-3">
                <a
                  href={`/library?subject=${encodeURIComponent(asset.subject || '')}`}
                  className="block w-full rounded-md bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Find Similar Assets
                </a>
                <a
                  href="/library/upload"
                  className="block w-full rounded-md bg-blue-100 px-3 py-2 text-sm font-medium text-blue-700 hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Upload New Asset
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Detail
