const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// Search Types for Library
export interface LibrarySearchRequest {
  query: string
  filters?: {
    subject?: string
    topic?: string
    type?: string
    gradeBand?: string
    source?: 'lessons' | 'coursework' | 'all'
  }
  limit?: number
  offset?: number
}

export interface LibrarySearchResult {
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
  relevanceScore: number
  highlights?: {
    title?: string
    description?: string
    content?: string
  }
}

export interface LibrarySearchResponse {
  results: LibrarySearchResult[]
  total: number
  hasMore: boolean
  suggestions?: string[]
  facets?: {
    subjects: Array<{ name: string; count: number }>
    topics: Array<{ name: string; count: number }>
    types: Array<{ name: string; count: number }>
    gradeBands: Array<{ name: string; count: number }>
  }
}

export interface SearchSuggestion {
  text: string
  type: 'query' | 'subject' | 'topic'
}

class SearchClient {
  private getAuthHeaders() {
    const token = localStorage.getItem('token')
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    }
  }

  async searchLibrary(
    params: LibrarySearchRequest
  ): Promise<LibrarySearchResponse> {
    const queryParams = new URLSearchParams()

    if (params.query) {
      queryParams.append('q', params.query)
    }

    if (params.filters) {
      Object.entries(params.filters).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          queryParams.append(key, String(value))
        }
      })
    }

    if (params.limit) {
      queryParams.append('limit', String(params.limit))
    }

    if (params.offset) {
      queryParams.append('offset', String(params.offset))
    }

    const response = await fetch(
      `${API_BASE}/search-svc/library?${queryParams}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to search library: ${response.statusText}`)
    }

    return response.json()
  }

  async getSuggestions(
    query: string,
    limit: number = 5
  ): Promise<SearchSuggestion[]> {
    const queryParams = new URLSearchParams({
      q: query,
      limit: String(limit),
    })

    const response = await fetch(
      `${API_BASE}/search-svc/suggestions?${queryParams}`,
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    )

    if (!response.ok) {
      throw new Error(
        `Failed to get search suggestions: ${response.statusText}`
      )
    }

    return response.json()
  }

  async indexAsset(
    assetId: string,
    source: 'lessons' | 'coursework'
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/search-svc/index`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ assetId, source }),
    })

    if (!response.ok) {
      throw new Error(`Failed to index asset: ${response.statusText}`)
    }
  }

  async removeFromIndex(
    assetId: string,
    source: 'lessons' | 'coursework'
  ): Promise<void> {
    const response = await fetch(`${API_BASE}/search-svc/index`, {
      method: 'DELETE',
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ assetId, source }),
    })

    if (!response.ok) {
      throw new Error(
        `Failed to remove asset from index: ${response.statusText}`
      )
    }
  }
}

export const searchClient = new SearchClient()
export default searchClient
