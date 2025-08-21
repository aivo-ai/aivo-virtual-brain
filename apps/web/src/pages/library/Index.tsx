import React, { useState, useEffect, useCallback } from 'react'
import { courseworkClient } from '../../api/courseworkClient'
import { lessonRegistryClient } from '../../api/lessonRegistryClient'
import { searchClient, LibrarySearchRequest } from '../../api/searchClient'
import { AssetCard } from '../../components/library/AssetCard'
import { Filters } from '../../components/library/Filters'

export interface LibraryAsset {
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
  thumbnail?: string
  createdAt: string
  attachedToLearner?: boolean
}

export interface LibraryFilters {
  subject?: string
  topic?: string
  type?: string
  gradeBand?: string
  source?: 'lessons' | 'coursework' | 'all'
}

const LibraryIndex: React.FC = () => {
  const [assets, setAssets] = useState<LibraryAsset[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<LibraryFilters>({ source: 'all' })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [page, setPage] = useState(0)
  const [facets, setFacets] = useState<any>(null)

  const ITEMS_PER_PAGE = 20

  const loadAssets = useCallback(
    async (resetPage = false) => {
      const currentPage = resetPage ? 0 : page
      setLoading(true)
      setError(null)

      try {
        let allAssets: LibraryAsset[] = []

        if (searchQuery) {
          // Use search API for filtered results
          const searchParams: LibrarySearchRequest = {
            query: searchQuery,
            filters,
            limit: ITEMS_PER_PAGE,
            offset: currentPage * ITEMS_PER_PAGE,
          }

          const searchResults = await searchClient.searchLibrary(searchParams)

          allAssets = searchResults.results.map(result => ({
            id: result.id,
            title: result.title,
            description: result.description,
            type: result.type,
            source: result.source,
            subject: result.subject,
            topic: result.topic,
            gradeBand: result.gradeBand,
            tags: result.tags,
            url: result.url,
            thumbnail: result.thumbnail,
            createdAt: new Date().toISOString(), // Search doesn't return createdAt
            attachedToLearner: false, // Would need to check against learner data
          }))

          setTotal(searchResults.total)
          setHasMore(searchResults.hasMore)
          setFacets(searchResults.facets)
        } else {
          // Direct API calls for browsing without search - union view implementation
          const promises: Promise<any>[] = []

          if (filters.source === 'all' || filters.source === 'lessons') {
            promises.push(
              lessonRegistryClient.searchLessons({
                subjects: filters.subject ? [filters.subject] : undefined,
                topics: filters.topic ? [filters.topic] : undefined,
                gradeBands: filters.gradeBand ? [filters.gradeBand] : undefined,
                limit: ITEMS_PER_PAGE,
                offset: currentPage * ITEMS_PER_PAGE,
              })
            )
          }

          if (filters.source === 'all' || filters.source === 'coursework') {
            promises.push(
              courseworkClient.getAssets({
                subject: filters.subject,
                topic: filters.topic,
                gradeBand: filters.gradeBand,
                type: filters.type,
                limit: ITEMS_PER_PAGE,
                offset: currentPage * ITEMS_PER_PAGE,
              })
            )
          }

          const results = await Promise.all(promises)

          let lessonAssets: LibraryAsset[] = []
          let courseworkAssets: LibraryAsset[] = []

          if (filters.source === 'all') {
            if (results[0]) {
              lessonAssets = results[0].lessons.map((lesson: any) => ({
                id: lesson.id,
                title: lesson.title,
                description: lesson.description,
                type: 'lesson',
                source: 'lessons' as const,
                subject: lesson.subject,
                topic: lesson.topics?.[0],
                gradeBand: lesson.gradeBand,
                tags: lesson.tags || [],
                url: lesson.contentUrl,
                thumbnail: lesson.thumbnailUrl,
                createdAt: lesson.createdAt,
                attachedToLearner: false,
              }))
            }

            if (results[1]) {
              courseworkAssets = results[1].assets.map((asset: any) => ({
                id: asset.id,
                title: asset.title,
                description: asset.description,
                type: asset.type,
                source: 'coursework' as const,
                subject: asset.metadata?.subject,
                topic: asset.metadata?.topic,
                gradeBand: asset.metadata?.gradeBand,
                tags: asset.tags || [],
                url: asset.url,
                thumbnail: asset.thumbnailUrl,
                createdAt: asset.createdAt,
                attachedToLearner: asset.attachedToLearner,
              }))
            }

            // merge and sort by creation date
            allAssets = [...lessonAssets, ...courseworkAssets].sort(
              (a, b) =>
                new Date(b.createdAt).getTime() -
                new Date(a.createdAt).getTime()
            )
          } else if (filters.source === 'lessons' && results[0]) {
            allAssets = results[0].lessons.map((lesson: any) => ({
              id: lesson.id,
              title: lesson.title,
              description: lesson.description,
              type: 'lesson',
              source: 'lessons' as const,
              subject: lesson.subject,
              topic: lesson.topics?.[0],
              gradeBand: lesson.gradeBand,
              tags: lesson.tags || [],
              url: lesson.contentUrl,
              thumbnail: lesson.thumbnailUrl,
              createdAt: lesson.createdAt,
              attachedToLearner: false,
            }))
          } else if (filters.source === 'coursework' && results[0]) {
            allAssets = results[0].assets.map((asset: any) => ({
              id: asset.id,
              title: asset.title,
              description: asset.description,
              type: asset.type,
              source: 'coursework' as const,
              subject: asset.metadata?.subject,
              topic: asset.metadata?.topic,
              gradeBand: asset.metadata?.gradeBand,
              tags: asset.tags || [],
              url: asset.url,
              thumbnail: asset.thumbnailUrl,
              createdAt: asset.createdAt,
              attachedToLearner: asset.attachedToLearner,
            }))
          }

          // Calculate totals for non-search mode
          const totalLessons = results[0]?.total || 0
          const totalCoursework = results[1]?.total || 0
          setTotal(
            filters.source === 'all'
              ? totalLessons + totalCoursework
              : filters.source === 'lessons'
                ? totalLessons
                : totalCoursework
          )
          setHasMore(allAssets.length === ITEMS_PER_PAGE)
        }

        if (resetPage) {
          setAssets(allAssets)
          setPage(0)
        } else {
          setAssets(prev => [...prev, ...allAssets])
          setPage(currentPage + 1)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load assets')
      } finally {
        setLoading(false)
      }
    },
    [searchQuery, filters, page]
  )

  useEffect(() => {
    loadAssets(true)
  }, [searchQuery, filters])

  const handleSearchChange = (query: string) => {
    setSearchQuery(query)
  }

  const handleFiltersChange = (newFilters: LibraryFilters) => {
    setFilters(newFilters)
  }

  const handleLoadMore = () => {
    if (!loading && hasMore) {
      loadAssets(false)
    }
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 px-4 py-8">
        <div className="mx-auto max-w-7xl">
          <div className="rounded-lg bg-red-50 p-4">
            <h3 className="text-lg font-medium text-red-800">
              Error Loading Library
            </h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
            <button
              onClick={() => loadAssets(true)}
              className="mt-3 rounded-md bg-red-100 px-3 py-2 text-sm font-medium text-red-800 hover:bg-red-200"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-7xl px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Learning Library</h1>
          <p className="mt-2 text-lg text-gray-600">
            Browse and discover learning assets from lessons and coursework
          </p>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="relative">
            <input
              type="text"
              placeholder="Search for assets, topics, or subjects..."
              value={searchQuery}
              onChange={e => handleSearchChange(e.target.value)}
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 pl-10 text-gray-900 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              aria-label="Search library assets"
            />
            <div className="absolute inset-y-0 left-0 flex items-center pl-3">
              <svg
                className="h-5 w-5 text-gray-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </div>
          </div>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Filters Sidebar */}
          <aside className="w-full lg:w-64 flex-shrink-0">
            <Filters
              filters={filters}
              facets={facets}
              onFiltersChange={handleFiltersChange}
            />
          </aside>

          {/* Main Content */}
          <main className="flex-1">
            {/* Results Summary */}
            <div className="mb-6 flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">
                  {loading && assets.length === 0
                    ? 'Loading...'
                    : `${total.toLocaleString()} ${total === 1 ? 'asset' : 'assets'} found`}
                </p>
              </div>
              <a
                href="/library/upload"
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              >
                Upload Asset
              </a>
            </div>

            {/* Assets Grid */}
            {assets.length > 0 ? (
              <>
                <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                  {assets.map(asset => (
                    <AssetCard
                      key={`${asset.source}-${asset.id}`}
                      asset={asset}
                    />
                  ))}
                </div>

                {/* Load More */}
                {hasMore && (
                  <div className="mt-8 flex justify-center">
                    <button
                      onClick={handleLoadMore}
                      disabled={loading}
                      className="rounded-lg bg-gray-200 px-6 py-3 text-sm font-medium text-gray-900 hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50"
                    >
                      {loading ? 'Loading...' : 'Load More'}
                    </button>
                  </div>
                )}
              </>
            ) : !loading ? (
              <div className="text-center py-12">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2h4a1 1 0 110 2h-1v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6H3a1 1 0 110-2h4zM9 6h6v12H9V6z"
                  />
                </svg>
                <h3 className="mt-2 text-sm font-medium text-gray-900">
                  No assets found
                </h3>
                <p className="mt-1 text-sm text-gray-500">
                  {searchQuery ||
                  Object.values(filters).some(f => f && f !== 'all')
                    ? 'Try adjusting your search or filters'
                    : 'Get started by uploading your first asset'}
                </p>
                <div className="mt-6">
                  <a
                    href="/library/upload"
                    className="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white hover:bg-blue-700"
                  >
                    <svg
                      className="-ml-0.5 mr-1.5 h-5 w-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Upload Asset
                  </a>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {/* Loading skeletons */}
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="animate-pulse">
                    <div className="bg-gray-200 rounded-lg h-48 mb-4"></div>
                    <div className="h-4 bg-gray-200 rounded mb-2"></div>
                    <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                  </div>
                ))}
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  )
}

export default LibraryIndex
