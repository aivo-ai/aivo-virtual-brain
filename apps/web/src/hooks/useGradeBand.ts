import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  getGradeBandFromGrade,
  isValidGradeBand,
  type GradeBand,
} from '../../../../libs/design-tokens'

export interface GradeBandPreferences {
  gradeBand: GradeBand
  isDyslexicFont: boolean
  isReducedMotion: boolean
  isHighContrast: boolean
  fontSize: 'normal' | 'large' | 'larger'
}

export interface GradeBandHookReturn {
  gradeBand: GradeBand
  preferences: GradeBandPreferences
  setGradeBand: (gradeBand: GradeBand) => void
  setPreferences: (preferences: Partial<GradeBandPreferences>) => void
  applyGradeBand: (element?: HTMLElement) => void
  resetToDefault: () => void
  isPreviewMode: boolean
  setPreviewMode: (enabled: boolean) => void
}

const STORAGE_KEY = 'aivo-grade-band-preferences'
const PREVIEW_STORAGE_KEY = 'aivo-grade-band-preview'

const DEFAULT_PREFERENCES: GradeBandPreferences = {
  gradeBand: '9-12', // Default to high school
  isDyslexicFont: false,
  isReducedMotion: false,
  isHighContrast: false,
  fontSize: 'normal',
}

/**
 * Hook for managing grade band theming and accessibility preferences
 *
 * @param learnerGrade - The learner's grade level (0-12, where 0 = Kindergarten)
 * @param persistPreferences - Whether to persist preferences to localStorage
 * @returns Grade band management utilities and current state
 */
export function useGradeBand(
  learnerGrade?: number,
  persistPreferences = true
): GradeBandHookReturn {
  // Determine initial grade band from learner grade or storage
  const getInitialGradeBand = useCallback((): GradeBand => {
    if (persistPreferences) {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          if (isValidGradeBand(parsed.gradeBand)) {
            return parsed.gradeBand
          }
        }
      } catch {
        // Ignore storage errors
      }
    }

    if (typeof learnerGrade === 'number') {
      return getGradeBandFromGrade(learnerGrade)
    }

    return DEFAULT_PREFERENCES.gradeBand
  }, [learnerGrade, persistPreferences])

  // Load initial preferences
  const getInitialPreferences = useCallback((): GradeBandPreferences => {
    let preferences = { ...DEFAULT_PREFERENCES }

    // Set grade band from learner or storage
    preferences.gradeBand = getInitialGradeBand()

    // Load from localStorage if persisting
    if (persistPreferences && typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (stored) {
          const parsed = JSON.parse(stored)
          preferences = { ...preferences, ...parsed }
        }
      } catch {
        // Ignore storage errors
      }
    }

    // Detect system preferences
    if (typeof window !== 'undefined') {
      preferences.isReducedMotion = window.matchMedia(
        '(prefers-reduced-motion: reduce)'
      ).matches
      preferences.isHighContrast = window.matchMedia(
        '(prefers-contrast: high)'
      ).matches
    }

    return preferences
  }, [getInitialGradeBand, persistPreferences])

  const [preferences, setPreferencesState] = useState<GradeBandPreferences>(
    getInitialPreferences
  )
  const [isPreviewMode, setPreviewModeState] = useState<boolean>(() => {
    if (!persistPreferences || typeof window === 'undefined') return false
    try {
      const stored = localStorage.getItem(PREVIEW_STORAGE_KEY)
      return stored === 'true'
    } catch {
      return false
    }
  })

  // Current grade band (derived from preferences)
  const gradeBand = useMemo(
    () => preferences.gradeBand,
    [preferences.gradeBand]
  )

  /**
   * Apply grade band styling to DOM element
   */
  const applyGradeBand = useCallback(
    (element: HTMLElement = document.documentElement) => {
      // Set grade band data attribute
      element.setAttribute('data-grade-band', preferences.gradeBand)

      // Apply font preferences
      if (preferences.isDyslexicFont) {
        element.classList.add('font-dyslexic')
      } else {
        element.classList.remove('font-dyslexic')
      }

      // Apply motion preferences
      if (preferences.isReducedMotion) {
        element.style.setProperty('--duration-fast', '0ms')
        element.style.setProperty('--duration-normal', '0ms')
        element.style.setProperty('--duration-slow', '0ms')
        element.style.setProperty('--scale-sm', '1')
        element.style.setProperty('--scale-md', '1')
        element.style.setProperty('--scale-lg', '1')
      }

      // Apply font size preferences
      const fontSizeMultiplier = {
        normal: 1,
        large: 1.125,
        larger: 1.25,
      }[preferences.fontSize]

      if (fontSizeMultiplier !== 1) {
        element.style.fontSize = `${fontSizeMultiplier}rem`
      }

      // Apply high contrast if needed
      if (preferences.isHighContrast) {
        element.setAttribute('data-high-contrast', 'true')
      } else {
        element.removeAttribute('data-high-contrast')
      }

      // Add preview mode indicator
      if (isPreviewMode) {
        element.setAttribute('data-preview-mode', 'true')
      } else {
        element.removeAttribute('data-preview-mode')
      }
    },
    [preferences, isPreviewMode]
  )

  /**
   * Update grade band
   */
  const setGradeBand = useCallback(
    (newGradeBand: GradeBand) => {
      if (!isValidGradeBand(newGradeBand)) {
        console.warn(`Invalid grade band: ${newGradeBand}`)
        return
      }

      const newPreferences = { ...preferences, gradeBand: newGradeBand }
      setPreferencesState(newPreferences)

      // Persist to localStorage
      if (persistPreferences && typeof window !== 'undefined') {
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(newPreferences))
        } catch {
          // Ignore localStorage errors
        }
      }
    },
    [preferences, persistPreferences]
  )

  /**
   * Update preferences
   */
  const setPreferences = useCallback(
    (updates: Partial<GradeBandPreferences>) => {
      const newPreferences = { ...preferences, ...updates }

      // Validate grade band if being updated
      if (updates.gradeBand && !isValidGradeBand(updates.gradeBand)) {
        console.warn(`Invalid grade band: ${updates.gradeBand}`)
        return
      }

      setPreferencesState(newPreferences)

      // Persist to localStorage
      if (persistPreferences && typeof window !== 'undefined') {
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(newPreferences))
        } catch {
          // Ignore localStorage errors
        }
      }
    },
    [preferences, persistPreferences]
  )

  /**
   * Set preview mode
   */
  const setPreviewMode = useCallback(
    (enabled: boolean) => {
      setPreviewModeState(enabled)

      if (persistPreferences && typeof window !== 'undefined') {
        try {
          if (enabled) {
            localStorage.setItem(PREVIEW_STORAGE_KEY, 'true')
          } else {
            localStorage.removeItem(PREVIEW_STORAGE_KEY)
          }
        } catch {
          // Ignore storage errors
        }
      }
    },
    [persistPreferences]
  )

  /**
   * Reset to default preferences
   */
  const resetToDefault = useCallback(() => {
    const defaultPrefs = { ...DEFAULT_PREFERENCES }

    // Use learner grade if available
    if (typeof learnerGrade === 'number') {
      defaultPrefs.gradeBand = getGradeBandFromGrade(learnerGrade)
    }

    setPreferencesState(defaultPrefs)
    setPreviewModeState(false)

    if (persistPreferences && typeof window !== 'undefined') {
      try {
        localStorage.removeItem(STORAGE_KEY)
        localStorage.removeItem(PREVIEW_STORAGE_KEY)
      } catch {
        // Ignore storage errors
      }
    }
  }, [learnerGrade, persistPreferences])

  // Persist preferences to storage
  useEffect(() => {
    if (!persistPreferences || typeof window === 'undefined') return

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
    } catch {
      // Ignore storage errors
    }
  }, [preferences, persistPreferences])

  // Apply grade band to DOM on changes
  useEffect(() => {
    applyGradeBand()
  }, [applyGradeBand])

  // Listen for system preference changes
  useEffect(() => {
    if (typeof window === 'undefined') return

    const handleMotionChange = (e: MediaQueryListEvent) => {
      setPreferences({ isReducedMotion: e.matches })
    }

    const handleContrastChange = (e: MediaQueryListEvent) => {
      setPreferences({ isHighContrast: e.matches })
    }

    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const contrastQuery = window.matchMedia('(prefers-contrast: high)')

    // Modern browsers
    if (motionQuery.addEventListener) {
      motionQuery.addEventListener('change', handleMotionChange)
      contrastQuery.addEventListener('change', handleContrastChange)

      return () => {
        motionQuery.removeEventListener('change', handleMotionChange)
        contrastQuery.removeEventListener('change', handleContrastChange)
      }
    }
    // Legacy browsers
    else if (motionQuery.addListener) {
      motionQuery.addListener(handleMotionChange)
      contrastQuery.addListener(handleContrastChange)

      return () => {
        motionQuery.removeListener(handleMotionChange)
        contrastQuery.removeListener(handleContrastChange)
      }
    }
  }, [setPreferences])

  return {
    gradeBand,
    preferences,
    setGradeBand,
    setPreferences,
    applyGradeBand,
    resetToDefault,
    isPreviewMode,
    setPreviewMode,
  }
}
