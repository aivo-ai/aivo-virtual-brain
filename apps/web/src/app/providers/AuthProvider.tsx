import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react'
import { analytics } from '@/utils/analytics'

export interface User {
  id: string
  email: string
  name: string
  role: 'parent' | 'teacher' | 'district_admin' | 'staff' | 'system_admin'
  dash_context: 'parent' | 'teacher' | 'district'
  avatar?: string
  settings?: {
    language?: string
    timezone?: string
    notifications?: boolean
    theme?: 'light' | 'dark' | 'system'
  }
}

export interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  sessionId: string
}

export interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<User>
  logout: () => Promise<void>
  register: (
    email: string,
    password: string,
    name: string,
    role: User['role']
  ) => Promise<User>
  updateUser: (updates: Partial<User>) => Promise<User>
  checkSession: () => Promise<boolean>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [sessionId] = useState(() => generateSessionId())

  const isAuthenticated = user !== null

  useEffect(() => {
    // Initialize analytics with auth context
    analytics.initialize({
      user_id: user?.id,
      role: user?.role,
      dash_context: user?.dash_context,
      session_id: sessionId,
    })
  }, [user, sessionId])

  useEffect(() => {
    // Check for existing session on mount
    checkSession().finally(() => {
      setIsLoading(false)
    })
  }, [])

  const login = async (email: string, password: string): Promise<User> => {
    setIsLoading(true)

    try {
      // In a real app, this would be an API call
      const response = await mockApiCall('/auth/login', {
        email,
        password,
      })

      const userData: User = response.user
      setUser(userData)

      // Store session data
      localStorage.setItem(
        'auth-session',
        JSON.stringify({
          user: userData,
          sessionId,
          timestamp: Date.now(),
        })
      )

      // Track login event
      analytics.trackAuth('login', 'email')
      analytics.updateContext({
        user_id: userData.id,
        role: userData.role,
        dash_context: userData.dash_context,
      })

      return userData
    } catch (error) {
      analytics.track('auth_error', {
        action: 'login',
        error: error instanceof Error ? error.message : 'Unknown error',
      })
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async (): Promise<void> => {
    setIsLoading(true)

    try {
      // In a real app, this would be an API call
      await mockApiCall('/auth/logout')

      setUser(null)
      localStorage.removeItem('auth-session')

      // Track logout event
      analytics.trackAuth('logout')
      analytics.updateContext({
        user_id: undefined,
        role: undefined,
        dash_context: undefined,
      })
    } catch (error) {
      console.warn('Logout error:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (
    email: string,
    password: string,
    name: string,
    role: User['role']
  ): Promise<User> => {
    setIsLoading(true)

    try {
      // In a real app, this would be an API call
      const response = await mockApiCall('/auth/register', {
        email,
        password,
        name,
        role,
      })

      const userData: User = response.user
      setUser(userData)

      // Store session data
      localStorage.setItem(
        'auth-session',
        JSON.stringify({
          user: userData,
          sessionId,
          timestamp: Date.now(),
        })
      )

      // Track registration event
      analytics.trackAuth('register', 'email')
      analytics.updateContext({
        user_id: userData.id,
        role: userData.role,
        dash_context: userData.dash_context,
      })

      return userData
    } catch (error) {
      analytics.track('auth_error', {
        action: 'register',
        error: error instanceof Error ? error.message : 'Unknown error',
      })
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const updateUser = async (updates: Partial<User>): Promise<User> => {
    if (!user) {
      throw new Error('No authenticated user')
    }

    try {
      // In a real app, this would be an API call
      const response = await mockApiCall('/auth/profile', updates)

      const updatedUser: User = { ...user, ...response.user }
      setUser(updatedUser)

      // Update session storage
      const session = localStorage.getItem('auth-session')
      if (session) {
        const sessionData = JSON.parse(session)
        localStorage.setItem(
          'auth-session',
          JSON.stringify({
            ...sessionData,
            user: updatedUser,
          })
        )
      }

      // Update analytics context if role or context changed
      if (updates.role || updates.dash_context) {
        analytics.updateContext({
          role: updatedUser.role,
          dash_context: updatedUser.dash_context,
        })
      }

      return updatedUser
    } catch (error) {
      console.error('Update user error:', error)
      throw error
    }
  }

  const checkSession = async (): Promise<boolean> => {
    try {
      const session = localStorage.getItem('auth-session')
      if (!session) {
        return false
      }

      const sessionData = JSON.parse(session)
      const isExpired = Date.now() - sessionData.timestamp > 24 * 60 * 60 * 1000 // 24 hours

      if (isExpired) {
        localStorage.removeItem('auth-session')
        return false
      }

      // In a real app, validate session with API
      const isValid = await mockApiCall('/auth/validate', {
        sessionId: sessionData.sessionId,
      })

      if (isValid.valid) {
        setUser(sessionData.user)
        return true
      } else {
        localStorage.removeItem('auth-session')
        return false
      }
    } catch (error) {
      console.warn('Session check error:', error)
      localStorage.removeItem('auth-session')
      return false
    }
  }

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated,
    sessionId,
    login,
    logout,
    register,
    updateUser,
    checkSession,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// Utility functions
function generateSessionId(): string {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

async function mockApiCall(endpoint: string, data?: unknown): Promise<any> {
  // Mock API implementation for development/demo
  await new Promise(resolve => setTimeout(resolve, 500)) // Simulate network delay

  if (endpoint === '/auth/login') {
    const { email } = data as { email: string }
    return {
      user: {
        id: `user_${Date.now()}`,
        email,
        name: email.split('@')[0],
        role: 'parent' as const,
        dash_context: 'parent' as const,
        settings: {
          language: 'en',
          timezone: 'UTC',
          notifications: true,
        },
      },
    }
  }

  if (endpoint === '/auth/register') {
    const { email, name, role } = data as {
      email: string
      name: string
      role: User['role']
    }
    return {
      user: {
        id: `user_${Date.now()}`,
        email,
        name,
        role,
        dash_context: role === 'district_admin' ? 'district' : role,
        settings: {
          language: 'en',
          timezone: 'UTC',
          notifications: true,
        },
      },
    }
  }

  if (endpoint === '/auth/validate') {
    return { valid: true }
  }

  if (endpoint === '/auth/profile') {
    return { user: data }
  }

  if (endpoint === '/auth/logout') {
    return { success: true }
  }

  throw new Error(`Unknown endpoint: ${endpoint}`)
}
