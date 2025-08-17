/**
 * S3-15 Global Search Client
 * RBAC-aware search across lessons, IEP metadata, and masked students
 */

import { useState, useEffect, useCallback } from 'react'

// Search Types and Interfaces
export interface SearchSuggestion {
  id: string
  text: string
  type: 'lesson' | 'student' | 'iep' | 'general'
  category: string
  metadata?: Record<string, any>
  url?: string
}

export interface SearchResult {
  id: string
  title: string
  description: string
  type: 'lesson' | 'student' | 'iep' | 'content' | 'assessment'
  category: string
  url: string
  relevanceScore: number
  highlightText?: string
  metadata: {
    lastModified?: string
    author?: string
    tags?: string[]
    subject?: string
    gradeLevel?: string
    privacy?: 'public' | 'private' | 'restricted'
    studentMasked?: boolean
  }
  permissions: {
    canView: boolean
    canEdit: boolean
    canShare: boolean
  }
}

export interface SearchFilters {
  types?: string[]
  categories?: string[]
  subjects?: string[]
  gradeLevels?: string[]
  dateRange?: {
    start: string
    end: string
  } | string
  privacy?: string[]
  onlyMyContent?: boolean
  sortBy?: 'relevance' | 'date' | 'title' | 'type'
}

export interface SearchResponse {
  results: SearchResult[]
  suggestions: SearchSuggestion[]
  totalCount: number
  facets: {
    types: Array<{ name: string; count: number }>
    categories: Array<{ name: string; count: number }>
    subjects: Array<{ name: string; count: number }>
    gradeLevels: Array<{ name: string; count: number }>
  }
  searchTime: number
}

export interface UserRole {
  role: string
  permissions: string[]
  districts: string[]
  schools: string[]
  subjects: string[]
}

// Helper function to get auth token
function getAuthToken(): string | null {
  return localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token')
}

// API helper function
async function apiCall(endpoint: string, options: RequestInit = {}): Promise<any> {
  const token = getAuthToken()
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` }),
      ...options.headers,
    },
  }

  const response = await fetch(`/api${endpoint}`, { ...defaultOptions, ...options })
  
  if (!response.ok) {
    throw new Error(`Search API call failed: ${response.statusText}`)
  }
  
  return response.json()
}

// Search API
export const searchAPI = {
  // Get search suggestions
  getSuggestions: async (query: string, limit = 5): Promise<SearchSuggestion[]> => {
    if (!query.trim()) return []
    
    const params = new URLSearchParams({
      q: query,
      limit: limit.toString()
    })
    
    const response = await apiCall(`/search/suggest?${params.toString()}`)
    return response.suggestions || []
  },

  // Perform full search
  search: async (
    query: string, 
    filters: Partial<SearchFilters> = {}, 
    page = 1, 
    limit = 20
  ): Promise<SearchResponse> => {
    const params = new URLSearchParams({
      q: query,
      page: page.toString(),
      limit: limit.toString(),
      ...Object.entries(filters).reduce((acc, [key, value]) => {
        if (Array.isArray(value) && value.length > 0) {
          acc[key] = value.join(',')
        } else if (typeof value === 'boolean') {
          acc[key] = value.toString()
        } else if (value && typeof value === 'object' && 'start' in value) {
          acc[`${key}_start`] = value.start
          acc[`${key}_end`] = value.end
        }
        return acc
      }, {} as Record<string, string>)
    })

    return apiCall(`/search?${params.toString()}`)
  },

  // Get user's search history
  getSearchHistory: async (limit = 10): Promise<string[]> => {
    try {
      const response = await apiCall(`/search/history?limit=${limit}`)
      return response.history || []
    } catch (error) {
      console.warn('Failed to load search history:', error)
      return []
    }
  },

  // Save search query to history
  saveToHistory: async (query: string): Promise<void> => {
    try {
      await apiCall('/search/history', {
        method: 'POST',
        body: JSON.stringify({ query })
      })
    } catch (error) {
      console.warn('Failed to save search history:', error)
    }
  },

  // Get user's role and permissions for RBAC
  getUserRole: async (): Promise<UserRole> => {
    try {
      const response = await apiCall('/user/role')
      return response.role
    } catch (error) {
      console.warn('Failed to load user role:', error)
      return {
        role: 'student',
        permissions: ['view_content'],
        districts: [],
        schools: [],
        subjects: []
      }
    }
  },

  // Get search analytics (for admin users)
  getSearchAnalytics: async (dateRange?: { start: string; end: string }): Promise<{
    popularQueries: Array<{ query: string; count: number }>
    searchVolume: Array<{ date: string; count: number }>
    noResultsQueries: Array<{ query: string; count: number }>
  }> => {
    const params = new URLSearchParams()
    if (dateRange) {
      params.append('start', dateRange.start)
      params.append('end', dateRange.end)
    }

    return apiCall(`/search/analytics?${params.toString()}`)
  }
}

// Search Hooks

/**
 * Hook for managing search suggestions
 */
export function useSearchSuggestions(query: string, enabled = true) {
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchSuggestions = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim() || !enabled) {
      setSuggestions([])
      return
    }

    try {
      setLoading(true)
      setError(null)
      const results = await searchAPI.getSuggestions(searchQuery)
      setSuggestions(results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch suggestions')
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      fetchSuggestions(query)
    }, 300) // Debounce suggestions

    return () => clearTimeout(timeoutId)
  }, [query, fetchSuggestions])

  return {
    suggestions,
    loading,
    error,
    refetch: () => fetchSuggestions(query)
  }
}

/**
 * Hook for managing full search functionality
 */
export function useSearch(query = '', searchFilters: SearchFilters = {}, enabled = true) {
  const [results, setResults] = useState<SearchResult[]>([])
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [totalCount, setTotalCount] = useState(0)
  const [facets, setFacets] = useState<SearchResponse['facets']>({
    types: [],
    categories: [],
    subjects: [],
    gradeLevels: []
  })
  const [searchTime, setSearchTime] = useState(0)

  const performSearch = useCallback(async () => {
    if (!query.trim() || !enabled) {
      setResults([])
      setTotalCount(0)
      setSuggestions([])
      return
    }

    try {
      setLoading(true)
      setError(null)

      const response = await searchAPI.search(query, searchFilters, 1)
      
      setResults(response.results)
      setSuggestions(response.suggestions)
      setTotalCount(response.totalCount)
      setFacets(response.facets)
      setSearchTime(response.searchTime)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
      setResults([])
      setSuggestions([])
      setTotalCount(0)
    } finally {
      setLoading(false)
    }
  }, [query, searchFilters, enabled])

  useEffect(() => {
    performSearch()
  }, [performSearch])

  return {
    results,
    suggestions,
    loading,
    error,
    totalCount,
    facets,
    searchTime,
    refetch: performSearch
  }
}

/**
 * Hook for managing search history
 */
export function useSearchHistory() {
  const [history, setHistory] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadHistory = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const historyData = await searchAPI.getSearchHistory()
      setHistory(historyData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load search history')
    } finally {
      setLoading(false)
    }
  }, [])

  const addToHistory = useCallback(async (query: string) => {
    try {
      await searchAPI.saveToHistory(query)
      setHistory(prev => [query, ...prev.filter(q => q !== query)].slice(0, 10))
    } catch (err) {
      console.warn('Failed to add to search history:', err)
    }
  }, [])

  const clearHistory = useCallback(() => {
    setHistory([])
    // Note: API call to clear server-side history could be added here
  }, [])

  useEffect(() => {
    loadHistory()
  }, [loadHistory])

  return {
    history,
    loading,
    error,
    addToHistory,
    clearHistory,
    refetch: loadHistory
  }
}

/**
 * Hook for user role and permissions
 */
export function useUserRole() {
  const [role, setRole] = useState<UserRole | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadRole = async () => {
      try {
        setError(null)
        const userRole = await searchAPI.getUserRole()
        setRole(userRole)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load user role')
      } finally {
        setLoading(false)
      }
    }

    loadRole()
  }, [])

  const hasPermission = useCallback((permission: string): boolean => {
    return role?.permissions.includes(permission) || false
  }, [role])

  const canViewContent = useCallback((content: SearchResult): boolean => {
    if (!role) return false

    // Admin can view everything
    if (role.role === 'admin') return true

    // Check basic view permission
    if (!content.permissions.canView) return false

    // Check privacy settings
    if (content.metadata.privacy === 'private' && content.metadata.author !== 'current-user') {
      return false
    }

    // Check student masking for non-teachers
    if (content.metadata.studentMasked && !['teacher', 'admin'].includes(role.role)) {
      return false
    }

    return true
  }, [role])

  return {
    role,
    loading,
    error,
    hasPermission,
    canViewContent
  }
}
