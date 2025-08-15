import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from 'react'

// Simple query cache implementation
interface QueryState<T> {
  data?: T
  error?: Error
  isLoading: boolean
  isError: boolean
  isSuccess: boolean
  lastFetched?: number
}

interface QueryOptions {
  staleTime?: number // How long data is considered fresh (ms)
  cacheTime?: number // How long to keep data in cache (ms)
  refetchOnWindowFocus?: boolean
  retry?: boolean | number
}

interface QueryContextType {
  queries: Map<string, QueryState<unknown>>
  setQueryData: <T>(key: string, data: T) => void
  invalidateQuery: (key: string) => void
  prefetchQuery: <T>(
    key: string,
    queryFn: () => Promise<T>,
    options?: QueryOptions
  ) => Promise<void>
}

const QueryContext = createContext<QueryContextType | undefined>(undefined)

export function useQuery<T>(
  key: string,
  queryFn: () => Promise<T>,
  options: QueryOptions = {}
) {
  const context = useContext(QueryContext)
  if (!context) {
    throw new Error('useQuery must be used within a QueryProvider')
  }

  const { queries, setQueryData } = context
  const [state, setState] = useState<QueryState<T>>(() => {
    const existing = queries.get(key) as QueryState<T> | undefined
    return (
      existing || {
        isLoading: false,
        isError: false,
        isSuccess: false,
      }
    )
  })

  const {
    staleTime = 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus = true,
    retry = 3,
  } = options

  // Execute query
  const executeQuery = async (retryCount = 0) => {
    setState(prev => ({ ...prev, isLoading: true, isError: false }))

    try {
      const data = await queryFn()
      const newState: QueryState<T> = {
        data,
        isLoading: false,
        isError: false,
        isSuccess: true,
        lastFetched: Date.now(),
      }

      setState(newState)
      queries.set(key, newState)
      return data
    } catch (error) {
      const shouldRetry = typeof retry === 'number' ? retryCount < retry : retry

      if (shouldRetry) {
        // Exponential backoff
        const delay = Math.pow(2, retryCount) * 1000
        await new Promise(resolve => setTimeout(resolve, delay))
        return executeQuery(retryCount + 1)
      }

      const errorState: QueryState<T> = {
        ...state,
        error: error as Error,
        isLoading: false,
        isError: true,
        isSuccess: false,
      }

      setState(errorState)
      queries.set(key, errorState)
      throw error
    }
  }

  // Check if data is stale
  const isStale = () => {
    if (!state.lastFetched) return true
    return Date.now() - state.lastFetched > staleTime
  }

  // Refetch function
  const refetch = () => executeQuery()

  // Auto-fetch on mount if no data or stale
  useEffect(() => {
    if (!state.data || isStale()) {
      executeQuery()
    }
  }, [key])

  // Refetch on window focus
  useEffect(() => {
    if (!refetchOnWindowFocus) return

    const handleFocus = () => {
      if (isStale()) {
        executeQuery()
      }
    }

    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [refetchOnWindowFocus])

  // Manual data setting
  const setData = (data: T) => {
    setQueryData(key, data)
    setState({
      data,
      isLoading: false,
      isError: false,
      isSuccess: true,
      lastFetched: Date.now(),
    })
  }

  return {
    ...state,
    refetch,
    setData,
  }
}

export function useMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options: {
    onSuccess?: (data: TData, variables: TVariables) => void
    onError?: (error: Error, variables: TVariables) => void
    onSettled?: (
      data: TData | undefined,
      error: Error | undefined,
      variables: TVariables
    ) => void
  } = {}
) {
  const [state, setState] = useState({
    data: undefined as TData | undefined,
    error: undefined as Error | undefined,
    isLoading: false,
    isError: false,
    isSuccess: false,
  })

  const mutate = async (variables: TVariables) => {
    setState({
      data: undefined,
      error: undefined,
      isLoading: true,
      isError: false,
      isSuccess: false,
    })

    try {
      const data = await mutationFn(variables)

      setState({
        data,
        error: undefined,
        isLoading: false,
        isError: false,
        isSuccess: true,
      })

      options.onSuccess?.(data, variables)
      options.onSettled?.(data, undefined, variables)

      return data
    } catch (error) {
      const err = error as Error

      setState({
        data: undefined,
        error: err,
        isLoading: false,
        isError: true,
        isSuccess: false,
      })

      options.onError?.(err, variables)
      options.onSettled?.(undefined, err, variables)

      throw error
    }
  }

  return {
    ...state,
    mutate,
    mutateAsync: mutate,
  }
}

interface QueryProviderProps {
  children: ReactNode
}

export function QueryProvider({ children }: QueryProviderProps) {
  const [queries] = useState(() => new Map<string, QueryState<unknown>>())

  // Cleanup stale queries periodically
  useEffect(() => {
    const cleanup = setInterval(() => {
      const now = Date.now()
      const cacheTime = 10 * 60 * 1000 // 10 minutes

      for (const [key, query] of queries.entries()) {
        if (query.lastFetched && now - query.lastFetched > cacheTime) {
          queries.delete(key)
        }
      }
    }, 60 * 1000) // Check every minute

    return () => clearInterval(cleanup)
  }, [queries])

  const setQueryData = <T,>(key: string, data: T) => {
    const newState: QueryState<T> = {
      data,
      isLoading: false,
      isError: false,
      isSuccess: true,
      lastFetched: Date.now(),
    }
    queries.set(key, newState)
  }

  const invalidateQuery = (key: string) => {
    queries.delete(key)
  }

  const prefetchQuery = async <T,>(
    key: string,
    queryFn: () => Promise<T>,
    options: QueryOptions = {}
  ) => {
    const existing = queries.get(key)
    const { staleTime = 5 * 60 * 1000 } = options

    // Don't prefetch if we have fresh data
    if (
      existing?.lastFetched &&
      Date.now() - existing.lastFetched < staleTime
    ) {
      return
    }

    try {
      const data = await queryFn()
      setQueryData(key, data)
    } catch (error) {
      console.warn(`Prefetch failed for key ${key}:`, error)
    }
  }

  const value: QueryContextType = {
    queries,
    setQueryData,
    invalidateQuery,
    prefetchQuery,
  }

  return <QueryContext.Provider value={value}>{children}</QueryContext.Provider>
}

// Query key utilities
export const queryKeys = {
  // User queries
  user: (id: string) => ['user', id],
  userProfile: (id: string) => ['user', id, 'profile'],

  // Learner queries
  learners: (parentId?: string) =>
    parentId ? ['learners', 'parent', parentId] : ['learners'],
  learner: (id: string) => ['learner', id],
  learnerProgress: (id: string) => ['learner', id, 'progress'],
  learnerAssessments: (id: string) => ['learner', id, 'assessments'],
  learnerGoals: (id: string) => ['learner', id, 'goals'],

  // Teacher queries
  teacherClasses: (teacherId: string) => ['teacher', teacherId, 'classes'],
  teacherStudents: (teacherId: string) => ['teacher', teacherId, 'students'],
  teacherAssignments: (teacherId: string) => [
    'teacher',
    teacherId,
    'assignments',
  ],
  teacherReports: (teacherId: string) => ['teacher', teacherId, 'reports'],

  // District queries
  districtOverview: (districtId: string) => [
    'district',
    districtId,
    'overview',
  ],
  districtSchools: (districtId: string) => ['district', districtId, 'schools'],
  districtTeachers: (districtId: string) => [
    'district',
    districtId,
    'teachers',
  ],
  districtReports: (districtId: string) => ['district', districtId, 'reports'],

  // Search queries
  search: (query: string, filters?: Record<string, unknown>) => [
    'search',
    query,
    ...(filters ? [filters] : []),
  ],
} as const
