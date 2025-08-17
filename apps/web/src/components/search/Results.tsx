/**
 * S3-15 Search Results Component
 * RBAC-aware search results display with faceted filtering
 */

import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { SearchResult, SearchFilters, useUserRole } from '../../api/searchClient'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { 
  BookOpen,
  User,
  ClipboardList,
  FileText,
  Calendar,
  Star,
  EyeOff,
  Filter,
  ChevronDown,
  ExternalLink,
  Clock,
  MapPin,
  Tag
} from '../ui/Icons'

interface ResultsProps {
  results: SearchResult[]
  filters: SearchFilters
  onFiltersChange: (filters: SearchFilters) => void
  loading?: boolean
  totalCount?: number
  query?: string
  className?: string
}

interface ResultCardProps {
  result: SearchResult
  userRole: any
  onNavigate: (url: string) => void
}

interface FilterSectionProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  isOpen: boolean
  onToggle: () => void
}

function FilterSection({ title, icon, children, isOpen, onToggle }: FilterSectionProps) {
  return (
    <div className="border-b border-gray-200 dark:border-gray-700 last:border-b-0">
      <button
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium text-gray-900 dark:text-white">{title}</span>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>
      {isOpen && (
        <div className="px-4 pb-4">
          {children}
        </div>
      )}
    </div>
  )
}

function ResultCard({ result, userRole, onNavigate }: ResultCardProps) {
  const canViewStudent = userRole === 'teacher' || userRole === 'admin' || userRole === 'counselor'
  const canViewIEP = userRole === 'admin' || userRole === 'special_ed' || userRole === 'counselor'
  
  const getIcon = () => {
    switch (result.type) {
      case 'lesson':
        return <BookOpen className="w-5 h-5 text-blue-500" />
      case 'student':
        return <User className="w-5 h-5 text-green-500" />
      case 'iep':
        return <ClipboardList className="w-5 h-5 text-purple-500" />
      default:
        return <FileText className="w-5 h-5 text-gray-500" />
    }
  }

  const getTypeLabel = () => {
    switch (result.type) {
      case 'lesson':
        return 'Lesson'
      case 'student':
        return 'Student'
      case 'iep':
        return 'IEP'
      default:
        return 'Content'
    }
  }

  const getVariant = () => {
    switch (result.type) {
      case 'lesson':
        return 'default' as const
      case 'student':
        return 'success' as const
      case 'iep':
        return 'secondary' as const
      default:
        return 'outline' as const
    }
  }

  const isRestricted = () => {
    if (result.type === 'student' && !canViewStudent) return true
    if (result.type === 'iep' && !canViewIEP) return true
    return false
  }

  const shouldMaskContent = () => {
    // Mask student names for non-authorized users
    return result.type === 'student' && !canViewStudent
  }

  const getDisplayTitle = () => {
    if (shouldMaskContent()) {
      return 'Student (Access Restricted)'
    }
    return result.title
  }

  const getDisplayDescription = () => {
    if (shouldMaskContent()) {
      return 'You do not have permission to view student information. Contact your administrator for access.'
    }
    return result.description
  }

  const handleClick = () => {
    if (!isRestricted()) {
      onNavigate(result.url)
    }
  }

  return (
    <Card className={`${isRestricted() ? 'opacity-60' : ''}`}>
      <div 
        className={`p-4 hover:shadow-md transition-all cursor-pointer ${
          isRestricted() ? 'cursor-not-allowed' : ''
        }`}
        onClick={handleClick}
      >
      <div className="flex items-start gap-4">
        {getIcon()}
        
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-gray-900 dark:text-white truncate">
                {getDisplayTitle()}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant={getVariant()} size="sm">
                  {getTypeLabel()}
                </Badge>
                {result.category && (
                  <span className="text-sm text-gray-500 dark:text-gray-400">
                    {result.category}
                  </span>
                )}
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              {isRestricted() ? (
                <div title="Access Restricted">
                  <EyeOff className="w-4 h-4 text-red-500" />
                </div>
              ) : (
                <ExternalLink className="w-4 h-4 text-gray-400" />
              )}
            </div>
          </div>

          <p className="text-gray-600 dark:text-gray-300 text-sm mb-3 line-clamp-2">
            {getDisplayDescription()}
          </p>

          <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
            {result.metadata?.lastModified && (
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>Modified {new Date(result.metadata.lastModified).toLocaleDateString()}</span>
              </div>
            )}
            
            {result.category && (
              <div className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                <span>{result.category}</span>
              </div>
            )}

            {result.relevanceScore && (
              <div className="flex items-center gap-1">
                <Star className="w-3 h-3" />
                <span>Relevance: {Math.round(result.relevanceScore * 100)}%</span>
              </div>
            )}
          </div>

          {result.metadata?.tags && result.metadata.tags.length > 0 && (
            <div className="flex items-center gap-2 mt-3">
              <Tag className="w-3 h-3 text-gray-400" />
              <div className="flex flex-wrap gap-1">
                {result.metadata.tags.slice(0, 3).map((tag: string, index: number) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs"
                  >
                    {tag}
                  </span>
                ))}
                {result.metadata.tags.length > 3 && (
                  <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded text-xs">
                    +{result.metadata.tags.length - 3} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
      </div>
    </Card>
  )
}

export function Results({ 
  results, 
  filters, 
  onFiltersChange, 
  loading = false, 
  totalCount = 0,
  query = '',
  className = ""
}: ResultsProps) {
  const navigate = useNavigate()
  const { role: userRole } = useUserRole()
  
  const [openSections, setOpenSections] = useState({
    type: true,
    category: false,
    dateRange: false,
    sort: true
  })

  const toggleSection = (section: keyof typeof openSections) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    onFiltersChange({ ...filters, [key]: value })
  }

  const handleTypeToggle = (type: string) => {
    const currentTypes = filters.types || []
    const newTypes = currentTypes.includes(type)
      ? currentTypes.filter(t => t !== type)
      : [...currentTypes, type]
    handleFilterChange('types', newTypes)
  }

  const handleCategoryToggle = (category: string) => {
    const currentCategories = filters.categories || []
    const newCategories = currentCategories.includes(category)
      ? currentCategories.filter(c => c !== category)
      : [...currentCategories, category]
    handleFilterChange('categories', newCategories)
  }

  const handleNavigate = (url: string) => {
    navigate(url)
  }

  const clearFilters = () => {
    onFiltersChange({
      types: [],
      categories: [],
      subjects: [],
      gradeLevels: [],
      privacy: [],
      onlyMyContent: false
    })
  }

  const hasActiveFilters = () => {
    return (filters.types && filters.types.length > 0) ||
           (filters.categories && filters.categories.length > 0) ||
           filters.dateRange ||
           filters.onlyMyContent
  }

  // Count by type for faceted filtering
  const typeCounts = results.reduce((acc, result) => {
    acc[result.type] = (acc[result.type] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  // Extract unique categories
  const categories = [...new Set(results.map(r => r.category).filter(Boolean))]

  return (
    <div className={`flex gap-6 ${className}`}>
      {/* Filters Sidebar */}
      <div className="w-64 flex-shrink-0">
        <Card className="sticky top-4">
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-500" />
                <h3 className="font-medium text-gray-900 dark:text-white">Filters</h3>
              </div>
              {hasActiveFilters() && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={clearFilters}
                  className="text-xs text-blue-600 hover:text-blue-700"
                >
                  Clear all
                </Button>
              )}
            </div>
          </div>

          {/* Content Type Filter */}
          <FilterSection
            title="Content Type"
            icon={<FileText className="w-4 h-4 text-gray-500" />}
            isOpen={openSections.type}
            onToggle={() => toggleSection('type')}
          >
            <div className="space-y-2">
              {Object.entries(typeCounts).map(([type, count]) => (
                <label key={type} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.types?.includes(type) || false}
                    onChange={() => handleTypeToggle(type)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                    {type} ({count})
                  </span>
                </label>
              ))}
            </div>
          </FilterSection>

          {/* Category Filter */}
          {categories.length > 0 && (
            <FilterSection
              title="Category"
              icon={<Tag className="w-4 h-4 text-gray-500" />}
              isOpen={openSections.category}
              onToggle={() => toggleSection('category')}
            >
              <div className="space-y-2">
                {categories.map((category) => (
                  <label key={category} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filters.categories?.includes(category) || false}
                      onChange={() => handleCategoryToggle(category)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {category}
                    </span>
                  </label>
                ))}
              </div>
            </FilterSection>
          )}

          {/* Date Range Filter */}
          <FilterSection
            title="Date Range"
            icon={<Calendar className="w-4 h-4 text-gray-500" />}
            isOpen={openSections.dateRange}
            onToggle={() => toggleSection('dateRange')}
          >
            <div className="space-y-2">
              {['today', 'week', 'month', 'year'].map((range) => (
                <label key={range} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="dateRange"
                    value={range}
                    checked={filters.dateRange === range}
                    onChange={(e) => handleFilterChange('dateRange', e.target.value)}
                    className="text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                    Past {range}
                  </span>
                </label>
              ))}
            </div>
          </FilterSection>

          {/* Sort Options */}
          <FilterSection
            title="Privacy Level"
            icon={<Filter className="w-4 h-4 text-gray-500" />}
            isOpen={openSections.sort}
            onToggle={() => toggleSection('sort')}
          >
            <div className="space-y-2">
              {[
                { value: 'public', label: 'Public Content' },
                { value: 'private', label: 'Private Content' },
                { value: 'restricted', label: 'Restricted Access' }
              ].map((option) => (
                <label key={option.value} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={filters.privacy?.includes(option.value) || false}
                    onChange={() => {
                      const current = filters.privacy || []
                      const updated = current.includes(option.value)
                        ? current.filter(p => p !== option.value)
                        : [...current, option.value]
                      handleFilterChange('privacy', updated)
                    }}
                    className="text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    {option.label}
                  </span>
                </label>
              ))}
            </div>
          </FilterSection>
        </Card>
      </div>

      {/* Results List */}
      <div className="flex-1 min-w-0">
        {/* Results Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Search Results
              </h2>
              {query && (
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  {totalCount} results for "{query}"
                </p>
              )}
            </div>
            
            {hasActiveFilters() && (
              <div className="text-sm text-gray-500 dark:text-gray-400">
                Filtered results
              </div>
            )}
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <Card key={i} className="p-4 animate-pulse">
                <div className="flex items-start gap-4">
                  <div className="w-5 h-5 bg-gray-200 dark:bg-gray-700 rounded"></div>
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/2 mb-3"></div>
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Results */}
        {!loading && results.length > 0 && (
          <div className="space-y-4">
            {results.map((result) => (
              <ResultCard
                key={result.id}
                result={result}
                userRole={userRole}
                onNavigate={handleNavigate}
              />
            ))}
          </div>
        )}

        {/* No Results */}
        {!loading && results.length === 0 && (
          <Card className="p-8 text-center">
            <FileText className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No results found
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">
              {query ? `No results match "${query}"` : 'Try adjusting your search terms or filters'}
            </p>
            {hasActiveFilters() && (
              <Button variant="outline" onClick={clearFilters}>
                Clear filters
              </Button>
            )}
          </Card>
        )}
      </div>
    </div>
  )
}
