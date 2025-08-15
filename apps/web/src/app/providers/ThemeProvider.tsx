import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react'
import { useAuth } from './AuthProvider'

export type Theme = 'light' | 'dark' | 'system'

interface ThemeContextType {
  theme: Theme
  resolvedTheme: 'light' | 'dark'
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

interface ThemeProviderProps {
  children: ReactNode
  defaultTheme?: Theme
  storageKey?: string
}

export function ThemeProvider({
  children,
  defaultTheme = 'system',
  storageKey = 'aivo-theme',
}: ThemeProviderProps) {
  const auth = useAuth()
  const user = auth?.user // Make it optional since auth might not be available
  const [theme, setTheme] = useState<Theme>(() => {
    // Try to get theme from localStorage first
    const stored = localStorage.getItem(storageKey) as Theme
    if (stored && ['light', 'dark', 'system'].includes(stored)) {
      return stored
    }
    return defaultTheme
  })

  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('light')

  // Update theme when user preference changes
  useEffect(() => {
    const userTheme = user?.settings?.theme as Theme
    if (userTheme && userTheme !== theme) {
      setTheme(userTheme)
    }
  }, [user?.settings?.theme, theme])

  // Resolve system theme
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')

    const updateResolvedTheme = () => {
      if (theme === 'system') {
        setResolvedTheme(mediaQuery.matches ? 'dark' : 'light')
      } else {
        setResolvedTheme(theme)
      }
    }

    updateResolvedTheme()

    if (theme === 'system') {
      mediaQuery.addEventListener('change', updateResolvedTheme)
      return () => mediaQuery.removeEventListener('change', updateResolvedTheme)
    }
  }, [theme])

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement

    // Remove existing theme classes
    root.classList.remove('light', 'dark')

    // Add current theme class
    root.classList.add(resolvedTheme)

    // Update CSS custom properties for theme
    if (resolvedTheme === 'dark') {
      root.style.setProperty('--color-scheme', 'dark')
    } else {
      root.style.setProperty('--color-scheme', 'light')
    }

    // Update meta theme-color for mobile browsers
    const metaThemeColor = document.querySelector('meta[name="theme-color"]')
    if (metaThemeColor) {
      metaThemeColor.setAttribute(
        'content',
        resolvedTheme === 'dark' ? '#1f2937' : '#ffffff'
      )
    }
  }, [resolvedTheme])

  const handleSetTheme = (newTheme: Theme) => {
    setTheme(newTheme)
    localStorage.setItem(storageKey, newTheme)

    // Track theme change
    if (typeof window !== 'undefined' && window.analytics) {
      window.analytics.track('theme_changed', {
        theme: newTheme,
        resolved_theme:
          newTheme === 'system'
            ? window.matchMedia('(prefers-color-scheme: dark)').matches
              ? 'dark'
              : 'light'
            : newTheme,
      })
    }
  }

  const value: ThemeContextType = {
    theme,
    resolvedTheme,
    setTheme: handleSetTheme,
  }

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

// Hook for theme-aware styling
export function useThemeStyles() {
  const { resolvedTheme } = useTheme()

  const getThemeClasses = (lightClasses: string, darkClasses: string) => {
    return resolvedTheme === 'dark' ? darkClasses : lightClasses
  }

  const getThemeValue = <T,>(lightValue: T, darkValue: T): T => {
    return resolvedTheme === 'dark' ? darkValue : lightValue
  }

  return {
    resolvedTheme,
    getThemeClasses,
    getThemeValue,
    isDark: resolvedTheme === 'dark',
    isLight: resolvedTheme === 'light',
  }
}

// CSS variable helpers
export const themeColors = {
  light: {
    primary: '#3b82f6',
    primaryHover: '#2563eb',
    secondary: '#6b7280',
    background: '#ffffff',
    surface: '#f9fafb',
    text: '#111827',
    textSecondary: '#6b7280',
    border: '#e5e7eb',
    error: '#ef4444',
    warning: '#f59e0b',
    success: '#10b981',
    info: '#3b82f6',
  },
  dark: {
    primary: '#60a5fa',
    primaryHover: '#3b82f6',
    secondary: '#9ca3af',
    background: '#111827',
    surface: '#1f2937',
    text: '#f9fafb',
    textSecondary: '#d1d5db',
    border: '#374151',
    error: '#f87171',
    warning: '#fbbf24',
    success: '#34d399',
    info: '#60a5fa',
  },
} as const

declare global {
  interface Window {
    analytics?: {
      track: (event: string, properties?: Record<string, unknown>) => void
    }
  }
}
