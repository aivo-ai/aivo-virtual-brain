/**
 * S3-15 Search Page Component
 * Complete search interface with RBAC-aware results and filtering
 */

import React, { useState, useEffect, useMemo } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useSearch, useSearchHistory, SearchFilters, SearchResult } from '../api/searchClient'
import { GlobalSearch } from '../components/search/GlobalSearch'
import { Results } from '../components/search/Results'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { 
  ArrowLeft,
  Search,
  Clock,
  BookOpen,
  Users,
  ClipboardList,
  FileText,
  Star,
  Filter
} from '../components/ui/Icons'

interface QuickSearchItem {
  query: string
  description: string
  icon: React.ReactNode
  category: string
}

export default function SearchPage() {
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  
  const [query, setQuery] = useState(searchParams.get('q') || '')
  const [filters, setFilters] = useState<SearchFilters>({
    types: [],
    categories: [],
    subjects: [],
    gradeLevels: [],
    privacy: [],
    onlyMyContent: false
  })
  
  // Search API calls
  const { results, loading, error, totalCount } = useSearch(query, filters, query.length > 0)
  const { addToHistory, history } = useSearchHistory()

  // Update query from URL params
  useEffect(() => {
    const urlQuery = searchParams.get('q') || ''
    setQuery(urlQuery)
  }, [searchParams])

  // Add successful searches to history
  useEffect(() => {
    if (query && results.length > 0 && !loading) {
      addToHistory(query)
    }
  }, [query, results.length, loading, addToHistory])

  const handleSearch = (newQuery: string) => {
    setQuery(newQuery)
    setSearchParams({ q: newQuery })
  }

  const handleFiltersChange = (newFilters: SearchFilters) => {
    setFilters(newFilters)
  }

  const handleBack = () => {
    navigate(-1)
  }

  // Quick search suggestions
  const quickSearches: QuickSearchItem[] = [
    {
      query: 'math lessons grade 3',
      description: 'Find grade 3 mathematics lessons',
      icon: <BookOpen className="w-4 h-4 text-blue-500" />,
      category: 'Lessons'
    },
    {
      query: 'IEP goals reading',
      description: 'Search IEP reading goals and objectives',
      icon: <ClipboardList className="w-4 h-4 text-purple-500" />,
      category: 'IEP Data'
    },
    {
      query: 'student assessments',
      description: 'View recent student assessments',
      icon: <FileText className="w-4 h-4 text-green-500" />,
      category: 'Assessments'
    },
    {
      query: 'special education resources',
      description: 'Find special education teaching materials',
      icon: <Users className="w-4 h-4 text-orange-500" />,
      category: 'Resources'
    }
  ]

  // Memoized filtered results for performance
  const filteredResults = useMemo(() => {
    return results.filter((result: SearchResult) => {
      // Apply client-side filtering if needed
      if (filters.types && filters.types.length > 0 && !filters.types.includes(result.type)) {
        return false
      }
      if (filters.categories && filters.categories.length > 0 && result.category && !filters.categories.includes(result.category)) {
        return false
      }
      return true
    })
  }, [results, filters])

  const hasQuery = query.length > 0

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4 py-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBack}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Back
            </Button>
            
            <div className="flex-1 max-w-2xl">
              <GlobalSearch
                placeholder="Search lessons, students, IEPs..."
                showShortcut={false}
                onSearch={handleSearch}
                autoFocus={!hasQuery}
                className="w-full"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Results */}
        {hasQuery && (
          <Results
            results={filteredResults}
            filters={filters}
            onFiltersChange={handleFiltersChange}
            loading={loading}
            totalCount={totalCount}
            query={query}
          />
        )}

        {/* Error State */}
        {error && (
          <Card className="p-8 text-center">
            <div className="text-red-500 mb-4">
              <Search className="w-12 h-12 mx-auto" />
            </div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Search Error
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              There was an error performing your search. Please try again.
            </p>
            <Button onClick={() => window.location.reload()}>
              Retry Search
            </Button>
          </Card>
        )}

        {/* Zero State - No Query */}
        {!hasQuery && !loading && (
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-12">
              <Search className="w-16 h-16 mx-auto mb-6 text-gray-400" />
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
                {t('search.title')}
              </h1>
              <p className="text-xl text-gray-600 dark:text-gray-400 mb-8">
                Find lessons, student information, IEP data, and educational resources
              </p>
            </div>

            {/* Quick Searches */}
            <div className="mb-12">
              <div className="flex items-center gap-2 mb-6">
                <Star className="w-5 h-5 text-blue-500" />
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Quick Searches
                </h2>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {quickSearches.map((item, index) => (
                  <div
                    key={index}
                    className="p-4 cursor-pointer hover:shadow-md transition-all hover:border-blue-300 dark:hover:border-blue-600 border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800"
                    onClick={() => handleSearch(item.query)}
                  >
                    <div className="flex items-start gap-3">
                      {item.icon}
                      <div className="flex-1">
                        <div className="font-medium text-gray-900 dark:text-white mb-1">
                          {item.query}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                          {item.description}
                        </div>
                        <div className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full inline-block">
                          {item.category}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Searches */}
            {history.length > 0 && (
              <div className="mb-12">
                <div className="flex items-center gap-2 mb-6">
                  <Clock className="w-5 h-5 text-gray-500" />
                  <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                    Recent Searches
                  </h2>
                </div>
                
                <div className="flex flex-wrap gap-2">
                  {history.slice(0, 8).map((item, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => handleSearch(item)}
                      className="text-gray-600 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                    >
                      {item}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* Search Tips */}
            <Card className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <Filter className="w-5 h-5 text-green-500" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Search Tips
                </h3>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    Search by Content Type
                  </h4>
                  <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    <li>• "lesson math grade 3" - Find specific lessons</li>
                    <li>• "student [name]" - Look up student records</li>
                    <li>• "IEP goals reading" - Search IEP data</li>
                    <li>• "assessment results" - Find assessments</li>
                  </ul>
                </div>
                
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                    Advanced Techniques
                  </h4>
                  <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    <li>• Use quotes for exact phrases</li>
                    <li>• Try synonyms and related terms</li>
                    <li>• Filter by date and content type</li>
                    <li>• Use keyboard shortcut ⌘/Ctrl + K</li>
                  </ul>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
