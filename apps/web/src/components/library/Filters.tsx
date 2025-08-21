import React, { useState } from 'react'
import { LibraryFilters } from '../../pages/library/Index'

interface FiltersProps {
  filters: LibraryFilters
  facets?: {
    subjects: Array<{ name: string; count: number }>
    topics: Array<{ name: string; count: number }>
    types: Array<{ name: string; count: number }>
    gradeBands: Array<{ name: string; count: number }>
  } | null
  onFiltersChange: (filters: LibraryFilters) => void
}

export const Filters: React.FC<FiltersProps> = ({
  filters,
  facets,
  onFiltersChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(false)

  const predefinedOptions = {
    subjects: [
      'Mathematics',
      'Science',
      'English Language Arts',
      'Social Studies',
      'History',
      'Geography',
      'Art',
      'Music',
      'Physical Education',
      'Computer Science',
      'Foreign Languages',
      'Life Skills',
    ],
    topics: [
      'Algebra',
      'Geometry',
      'Statistics',
      'Biology',
      'Chemistry',
      'Physics',
      'Reading Comprehension',
      'Creative Writing',
      'Grammar',
      'World History',
      'American History',
      'Civics',
      'Visual Arts',
      'Performing Arts',
      'Programming',
      'Critical Thinking',
    ],
    types: [
      'lesson',
      'document',
      'image',
      'video',
      'audio',
      'interactive',
      'assessment',
      'worksheet',
      'presentation',
    ],
    gradeBands: ['K-2', '3-5', '6-8', '9-12', 'Adult'],
  }

  const handleFilterChange = (key: keyof LibraryFilters, value: string) => {
    const newFilters = {
      ...filters,
      [key]: value === '' ? undefined : value,
    }
    onFiltersChange(newFilters)
  }

  const clearFilters = () => {
    onFiltersChange({ source: 'all' })
  }

  const getFilterOptions = (key: keyof typeof predefinedOptions) => {
    // Use facets if available, otherwise fall back to predefined options
    if (facets && facets[key]) {
      return facets[key].map(facet => facet.name)
    }
    return predefinedOptions[key]
  }

  const getFilterCount = (
    key: keyof typeof predefinedOptions,
    value: string
  ) => {
    if (facets && facets[key]) {
      const facet = facets[key].find(f => f.name === value)
      return facet?.count
    }
    return undefined
  }

  const activeFiltersCount = Object.values(filters).filter(
    value => value && value !== 'all'
  ).length

  return (
    <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-4">
      {/* Mobile Filter Toggle */}
      <div className="lg:hidden mb-4">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex w-full items-center justify-between rounded-md bg-gray-50 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label={`${isExpanded ? 'Collapse' : 'Expand'} filter options`}
        >
          <span>
            Filters {activeFiltersCount > 0 && `(${activeFiltersCount})`}
          </span>
          <svg
            className={`h-5 w-5 transform transition-transform ${
              isExpanded ? 'rotate-180' : ''
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
      </div>

      <div className={`space-y-6 ${isExpanded ? 'block' : 'hidden lg:block'}`}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Filters</h3>
          {activeFiltersCount > 0 && (
            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:text-blue-800 focus:outline-none focus:underline"
            >
              Clear all
            </button>
          )}
        </div>

        {/* Source Filter */}
        <div>
          <label
            htmlFor="source"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Source
          </label>
          <select
            id="source"
            value={filters.source || 'all'}
            onChange={e => handleFilterChange('source', e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="all">All Sources</option>
            <option value="lessons">Lessons Only</option>
            <option value="coursework">Coursework Only</option>
          </select>
        </div>

        {/* Subject Filter */}
        <div>
          <label
            htmlFor="subject"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Subject
          </label>
          <select
            id="subject"
            value={filters.subject || ''}
            onChange={e => handleFilterChange('subject', e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Subjects</option>
            {getFilterOptions('subjects').map(subject => (
              <option key={subject} value={subject}>
                {subject}
                {getFilterCount('subjects', subject) &&
                  ` (${getFilterCount('subjects', subject)})`}
              </option>
            ))}
          </select>
        </div>

        {/* Topic Filter */}
        <div>
          <label
            htmlFor="topic"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Topic
          </label>
          <select
            id="topic"
            value={filters.topic || ''}
            onChange={e => handleFilterChange('topic', e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Topics</option>
            {getFilterOptions('topics').map(topic => (
              <option key={topic} value={topic}>
                {topic}
                {getFilterCount('topics', topic) &&
                  ` (${getFilterCount('topics', topic)})`}
              </option>
            ))}
          </select>
        </div>

        {/* Type Filter */}
        <div>
          <label
            htmlFor="type"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Type
          </label>
          <select
            id="type"
            value={filters.type || ''}
            onChange={e => handleFilterChange('type', e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Types</option>
            {getFilterOptions('types').map(type => (
              <option key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1)}
                {getFilterCount('types', type) &&
                  ` (${getFilterCount('types', type)})`}
              </option>
            ))}
          </select>
        </div>

        {/* Grade Band Filter */}
        <div>
          <label
            htmlFor="gradeBand"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Grade Band
          </label>
          <select
            id="gradeBand"
            value={filters.gradeBand || ''}
            onChange={e => handleFilterChange('gradeBand', e.target.value)}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Grades</option>
            {getFilterOptions('gradeBands').map(gradeBand => (
              <option key={gradeBand} value={gradeBand}>
                Grade {gradeBand}
                {getFilterCount('gradeBands', gradeBand) &&
                  ` (${getFilterCount('gradeBands', gradeBand)})`}
              </option>
            ))}
          </select>
        </div>

        {/* Active Filters Summary */}
        {activeFiltersCount > 0 && (
          <div className="pt-4 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Active Filters:
            </h4>
            <div className="space-y-1">
              {filters.source && filters.source !== 'all' && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">
                    Source: {filters.source}
                  </span>
                  <button
                    onClick={() => handleFilterChange('source', 'all')}
                    className="text-red-600 hover:text-red-800 focus:outline-none"
                    aria-label="Remove source filter"
                  >
                    ×
                  </button>
                </div>
              )}
              {filters.subject && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">
                    Subject: {filters.subject}
                  </span>
                  <button
                    onClick={() => handleFilterChange('subject', '')}
                    className="text-red-600 hover:text-red-800 focus:outline-none"
                    aria-label="Remove subject filter"
                  >
                    ×
                  </button>
                </div>
              )}
              {filters.topic && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Topic: {filters.topic}</span>
                  <button
                    onClick={() => handleFilterChange('topic', '')}
                    className="text-red-600 hover:text-red-800 focus:outline-none"
                    aria-label="Remove topic filter"
                  >
                    ×
                  </button>
                </div>
              )}
              {filters.type && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Type: {filters.type}</span>
                  <button
                    onClick={() => handleFilterChange('type', '')}
                    className="text-red-600 hover:text-red-800 focus:outline-none"
                    aria-label="Remove type filter"
                  >
                    ×
                  </button>
                </div>
              )}
              {filters.gradeBand && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">
                    Grade: {filters.gradeBand}
                  </span>
                  <button
                    onClick={() => handleFilterChange('gradeBand', '')}
                    className="text-red-600 hover:text-red-800 focus:outline-none"
                    aria-label="Remove grade band filter"
                  >
                    ×
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Filters
