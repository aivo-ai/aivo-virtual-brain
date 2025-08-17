/**
 * S3-15 Global Search Component
 * Typeahead search with keyboard shortcuts and RBAC-aware filtering
 */

import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSearchSuggestions, useSearchHistory, SearchSuggestion } from '../../api/searchClient'
import { Card } from '../ui/Card'
import { Button } from '../ui/Button'
import { 
  Search, 
  Clock, 
  Loader2,
  X,
  BookOpen,
  User,
  ClipboardList,
  FileText,
  ChevronRight
} from '../ui/Icons'

interface GlobalSearchProps {
  placeholder?: string
  showShortcut?: boolean
  onSearch?: (query: string) => void
  onClose?: () => void
  autoFocus?: boolean
  className?: string
}

interface SuggestionItemProps {
  suggestion: SearchSuggestion
  isSelected: boolean
  onClick: () => void
  onMouseEnter: () => void
}

function SuggestionItem({ suggestion, isSelected, onClick, onMouseEnter }: SuggestionItemProps) {
  const getIcon = () => {
    switch (suggestion.type) {
      case 'lesson':
        return <BookOpen className="w-4 h-4 text-blue-500" />
      case 'student':
        return <User className="w-4 h-4 text-green-500" />
      case 'iep':
        return <ClipboardList className="w-4 h-4 text-purple-500" />
      default:
        return <FileText className="w-4 h-4 text-gray-500" />
    }
  }

  const getTypeLabel = () => {
    switch (suggestion.type) {
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

  return (
    <div
      className={`flex items-center gap-3 px-3 py-2 cursor-pointer rounded-md transition-colors ${
        isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800'
      }`}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
    >
      {getIcon()}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-white truncate">
            {suggestion.text}
          </span>
          <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full">
            {getTypeLabel()}
          </span>
        </div>
        {suggestion.category && (
          <div className="text-sm text-gray-500 dark:text-gray-400 truncate">
            {suggestion.category}
          </div>
        )}
      </div>
      <ChevronRight className="w-4 h-4 text-gray-400" />
    </div>
  )
}

export function GlobalSearch({ 
  placeholder = "Search lessons, students, IEPs...", 
  showShortcut = true,
  onSearch,
  onClose,
  autoFocus = false,
  className = ""
}: GlobalSearchProps) {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  const { suggestions, loading: suggestionsLoading } = useSearchSuggestions(query, isOpen && query.length > 0)
  const { history } = useSearchHistory()

  // Show suggestions or history
  const showSuggestions = isOpen && query.length > 0
  const showHistory = isOpen && query.length === 0 && history.length > 0
  const displayItems = showSuggestions ? suggestions : (showHistory ? history.map(h => ({
    id: h,
    text: h,
    type: 'general' as const,
    category: 'Recent search'
  })) : [])

  // Keyboard shortcut handling
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Cmd/Ctrl + K to open search
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault()
        setIsOpen(true)
        setTimeout(() => inputRef.current?.focus(), 100)
      }

      // Escape to close
      if (event.key === 'Escape' && isOpen) {
        handleClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setSelectedIndex(-1)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  // Auto-focus when requested
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus()
      setIsOpen(true)
    }
  }, [autoFocus])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value
    setQuery(value)
    setSelectedIndex(-1)
    
    if (!isOpen) {
      setIsOpen(true)
    }
  }

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev => Math.min(prev + 1, displayItems.length - 1))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => Math.max(prev - 1, -1))
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < displayItems.length) {
          handleSuggestionSelect(displayItems[selectedIndex])
        } else if (query.trim()) {
          handleSearch()
        }
        break
      case 'Escape':
        handleClose()
        break
    }
  }

  const handleSuggestionSelect = (suggestion: SearchSuggestion) => {
    if (suggestion.url) {
      navigate(suggestion.url)
    } else {
      setQuery(suggestion.text)
      handleSearch(suggestion.text)
    }
    setIsOpen(false)
    setSelectedIndex(-1)
  }

  const handleSearch = (searchQuery?: string) => {
    const finalQuery = searchQuery || query
    if (!finalQuery.trim()) return

    // Navigate to search results page
    navigate(`/search?q=${encodeURIComponent(finalQuery)}`)
    
    // Call custom search handler if provided
    onSearch?.(finalQuery)
    
    // Close search
    setIsOpen(false)
    setSelectedIndex(-1)
  }

  const handleClose = () => {
    setIsOpen(false)
    setSelectedIndex(-1)
    setQuery('')
    onClose?.()
  }

  const handleFocus = () => {
    setIsOpen(true)
  }

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      {/* Search Input */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-gray-400" />
        </div>
        
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleInputKeyDown}
          onFocus={handleFocus}
          placeholder={placeholder}
          className="block w-full pl-10 pr-12 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          autoComplete="off"
          spellCheck="false"
        />

        <div className="absolute inset-y-0 right-0 flex items-center">
          {suggestionsLoading && query.length > 0 && (
            <Loader2 className="h-4 w-4 text-gray-400 animate-spin mr-3" />
          )}
          
          {query.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setQuery('')}
              className="h-6 w-6 p-0 mr-2 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <X className="h-3 w-3" />
            </Button>
          )}

          {showShortcut && !isOpen && (
            <div className="hidden sm:flex items-center gap-1 mr-3 text-xs text-gray-400">
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
                {navigator.platform.toLowerCase().includes('mac') ? '⌘' : 'Ctrl'}
              </kbd>
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">K</kbd>
            </div>
          )}
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && (displayItems.length > 0 || query.length > 0) && (
        <Card className="absolute top-full left-0 right-0 mt-2 max-h-96 overflow-y-auto z-50 shadow-lg border border-gray-200 dark:border-gray-700">
          <div className="p-2">
            {/* Header */}
            {showHistory && (
              <div className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-700 mb-2">
                <Clock className="w-4 h-4" />
                Recent searches
              </div>
            )}
            
            {showSuggestions && suggestions.length === 0 && !suggestionsLoading && (
              <div className="px-3 py-4 text-center text-gray-500 dark:text-gray-400">
                <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No suggestions found</p>
                <p className="text-xs mt-1">Try a different search term</p>
              </div>
            )}

            {/* Suggestions/History Items */}
            {displayItems.map((item, index) => (
              <SuggestionItem
                key={item.id}
                suggestion={item}
                isSelected={index === selectedIndex}
                onClick={() => handleSuggestionSelect(item)}
                onMouseEnter={() => setSelectedIndex(index)}
              />
            ))}

            {/* Search Action */}
            {query.trim() && (
              <div className="border-t border-gray-100 dark:border-gray-700 mt-2 pt-2">
                <div
                  className={`flex items-center gap-3 px-3 py-2 cursor-pointer rounded-md transition-colors ${
                    selectedIndex === displayItems.length ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                  }`}
                  onClick={() => handleSearch()}
                  onMouseEnter={() => setSelectedIndex(displayItems.length)}
                >
                  <Search className="w-4 h-4 text-blue-500" />
                  <span className="flex-1 font-medium text-gray-900 dark:text-white">
                    Search for "{query}"
                  </span>
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Zero State Guidance */}
      {isOpen && displayItems.length === 0 && query.length === 0 && history.length === 0 && (
        <Card className="absolute top-full left-0 right-0 mt-2 z-50 shadow-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="text-center">
              <Search className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                Search AIVO
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                Find lessons, student information, IEP data, and more
              </p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-left">
                <div className="flex items-start gap-3">
                  <BookOpen className="w-5 h-5 text-blue-500 mt-0.5" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Lessons</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Search by subject, grade, or topic</div>
                  </div>
                </div>
                
                <div className="flex items-start gap-3">
                  <User className="w-5 h-5 text-green-500 mt-0.5" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Students</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Find student records (privacy-aware)</div>
                  </div>
                </div>
                
                <div className="flex items-start gap-3">
                  <ClipboardList className="w-5 h-5 text-purple-500 mt-0.5" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">IEP Data</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Access IEP metadata and goals</div>
                  </div>
                </div>
                
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-gray-500 mt-0.5" />
                  <div>
                    <div className="font-medium text-gray-900 dark:text-white">Content</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">Assessments, resources, and more</div>
                  </div>
                </div>
              </div>

              <div className="mt-6 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <div className="text-sm text-blue-900 dark:text-blue-100">
                  <strong>Tip:</strong> Use keyboard shortcut{' '}
                  <kbd className="px-1 py-0.5 bg-blue-100 dark:bg-blue-800 rounded text-xs">
                    {navigator.platform.toLowerCase().includes('mac') ? '⌘K' : 'Ctrl+K'}
                  </kbd>{' '}
                  to quickly open search from anywhere
                </div>
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
