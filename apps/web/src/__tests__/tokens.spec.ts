import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useGradeBand } from '../hooks/useGradeBand'
import type { GradeBand } from '../../../../libs/design-tokens'
import { designTokens } from '../../../../libs/design-tokens'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(() => null) as any,
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  configurable: true,
})

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

describe('Design Tokens - Grade Band Theming', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.documentElement.removeAttribute('data-grade-band')
    document.documentElement.removeAttribute('data-preview-mode')
    document.documentElement.classList.remove('font-dyslexic')

    // Reset localStorage mock
    localStorageMock.getItem.mockReturnValue(null)
    localStorageMock.setItem.mockClear()
    localStorageMock.removeItem.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('useGradeBand Hook', () => {
    it('should initialize with default grade band (9-12)', () => {
      const { result } = renderHook(() => useGradeBand())

      expect(result.current.gradeBand).toBe('9-12')
      expect(result.current.preferences.gradeBand).toBe('9-12')
      expect(result.current.isPreviewMode).toBe(false)
    })

    it('should determine grade band from learner grade', () => {
      const testCases: [number, GradeBand][] = [
        [0, 'k-2'], // Kindergarten
        [1, 'k-2'],
        [2, 'k-2'],
        [3, '3-5'],
        [4, '3-5'],
        [5, '3-5'],
        [6, '6-8'],
        [7, '6-8'],
        [8, '6-8'],
        [9, '9-12'],
        [10, '9-12'],
        [11, '9-12'],
        [12, '9-12'],
      ]

      testCases.forEach(([grade, expectedGradeBand]) => {
        const { result } = renderHook(() => useGradeBand(grade))
        expect(result.current.gradeBand).toBe(expectedGradeBand)
      })
    })

    it('should apply grade band to DOM element', () => {
      const { result } = renderHook(() => useGradeBand(5)) // Grade 5 -> 3-5 band

      act(() => {
        result.current.applyGradeBand()
      })

      expect(document.documentElement.getAttribute('data-grade-band')).toBe(
        '3-5'
      )
    })

    it('should update grade band correctly', () => {
      const { result } = renderHook(() => useGradeBand())

      act(() => {
        result.current.setGradeBand('k-2')
      })

      expect(result.current.gradeBand).toBe('k-2')
      expect(document.documentElement.getAttribute('data-grade-band')).toBe(
        'k-2'
      )
    })

    it('should handle dyslexic font preference', () => {
      const { result } = renderHook(() => useGradeBand())

      act(() => {
        result.current.setPreferences({ isDyslexicFont: true })
      })

      expect(result.current.preferences.isDyslexicFont).toBe(true)
      expect(document.documentElement.classList.contains('font-dyslexic')).toBe(
        true
      )
    })

    it('should handle reduced motion preference', () => {
      const { result } = renderHook(() => useGradeBand())

      act(() => {
        result.current.setPreferences({ isReducedMotion: true })
      })

      expect(result.current.preferences.isReducedMotion).toBe(true)
      // Check if CSS custom properties are set for reduced motion
      const style = document.documentElement.style
      expect(style.getPropertyValue('--duration-fast')).toBe('0ms')
      expect(style.getPropertyValue('--scale-sm')).toBe('1')
    })

    it('should persist preferences to localStorage', () => {
      const { result } = renderHook(() => useGradeBand(3, true)) // persistPreferences = true

      act(() => {
        result.current.setPreferences({ isDyslexicFont: true })
      })

      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'aivo-grade-band-preferences',
        expect.stringContaining('isDyslexicFont')
      )
    })

    it('should load preferences from localStorage', () => {
      const mockPreferences = {
        gradeBand: 'k-2',
        isDyslexicFont: true,
        isReducedMotion: false,
        isHighContrast: false,
        fontSize: 'large',
      }

      localStorageMock.getItem.mockReturnValue(JSON.stringify(mockPreferences))

      const { result } = renderHook(() => useGradeBand(undefined, true))

      expect(result.current.preferences.gradeBand).toBe('k-2')
      expect(result.current.preferences.isDyslexicFont).toBe(true)
      expect(result.current.preferences.fontSize).toBe('large')
    })

    it('should handle preview mode', () => {
      const { result } = renderHook(() => useGradeBand(undefined, true)) // persistPreferences = true

      act(() => {
        result.current.setPreviewMode(true)
      })

      expect(result.current.isPreviewMode).toBe(true)
      expect(document.documentElement.getAttribute('data-preview-mode')).toBe(
        'true'
      )
      expect(localStorageMock.setItem).toHaveBeenCalledWith(
        'aivo-grade-band-preview',
        'true'
      )
    })

    it('should reset to default preferences', () => {
      const { result } = renderHook(() => useGradeBand(1)) // Grade 1 -> k-2

      // Change some preferences
      act(() => {
        result.current.setPreferences({
          isDyslexicFont: true,
          fontSize: 'larger',
        })
        result.current.setPreviewMode(true)
      })

      // Reset
      act(() => {
        result.current.resetToDefault()
      })

      expect(result.current.preferences.gradeBand).toBe('k-2') // Should use learner grade
      expect(result.current.preferences.isDyslexicFont).toBe(false)
      expect(result.current.preferences.fontSize).toBe('normal')
      expect(result.current.isPreviewMode).toBe(false)
    })

    it('should validate grade band input', () => {
      const { result } = renderHook(() => useGradeBand())
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      act(() => {
        result.current.setGradeBand('invalid-grade-band' as GradeBand)
      })

      expect(consoleSpy).toHaveBeenCalledWith(
        'Invalid grade band: invalid-grade-band'
      )
      expect(result.current.gradeBand).toBe('9-12') // Should remain unchanged
    })

    it('should handle media query changes for system preferences', () => {
      const mockMediaQuery = {
        matches: true,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }

      window.matchMedia = vi.fn().mockReturnValue(mockMediaQuery) as any

      const { result } = renderHook(() => useGradeBand())

      // Simulate system reduced motion preference
      expect(mockMediaQuery.addEventListener).toHaveBeenCalledWith(
        'change',
        expect.any(Function)
      )

      // Simulate media query change
      const changeHandler = mockMediaQuery.addEventListener.mock.calls[0][1]
      act(() => {
        changeHandler({ matches: true })
      })

      expect(result.current.preferences.isReducedMotion).toBe(true)
    })
  })

  describe('Design Token Accessibility', () => {
    it('should meet WCAG AA contrast requirements', () => {
      // This would typically use a color contrast testing library
      // For now, we'll test that the contrast values are configured correctly

      expect(designTokens.accessibility.contrast.normal).toBe(4.5)
      expect(designTokens.accessibility.contrast.large).toBe(3.0)
      expect(designTokens.accessibility.contrast.enhanced).toBe(7.0)
    })

    it('should provide appropriate focus ring styling', () => {
      expect(designTokens.accessibility.focusRing.width).toBe('2px')
      expect(designTokens.accessibility.focusRing.offset).toBe('2px')
      expect(designTokens.accessibility.focusRing.color).toBe('#2563eb')
    })

    it('should have dyslexia-friendly font stack', () => {
      expect(designTokens.fonts.dyslexic).toContain('OpenDyslexic')
      expect(designTokens.fonts.dyslexic).toContain('"Noto Sans"')
    })
  })

  describe('Grade Band Token Variations', () => {
    it('should have appropriate sizing for K-2 grade band', () => {
      const k2Tokens = designTokens.gradeBands['k-2']

      // K-2 should have larger, more playful sizing
      expect(k2Tokens.fontSize.base[0]).toBe('1.125rem') // Larger than default
      expect(k2Tokens.borderRadius.md).toBe('0.5rem') // More rounded
      expect(k2Tokens.iconSize.md).toBe('1.5rem') // Larger icons
    })

    it('should have refined sizing for 9-12 grade band', () => {
      const highSchoolTokens = designTokens.gradeBands['9-12']

      // 9-12 should have smaller, more professional sizing
      expect(highSchoolTokens.fontSize.base[0]).toBe('1rem') // Standard size
      expect(highSchoolTokens.borderRadius.sm).toBe('0.125rem') // Less rounded
      expect(highSchoolTokens.motion.duration.fast).toBe('100ms') // Faster animations
    })

    it('should have different accent colors per grade band', () => {
      // Each grade band should have appropriate accent colors
      expect(designTokens.gradeBands['k-2'].colors.accent['500']).toBe(
        '#f59e0b'
      ) // Warm yellow
      expect(designTokens.gradeBands['3-5'].colors.accent['500']).toBe(
        '#22c55e'
      ) // Green for growth
      expect(designTokens.gradeBands['6-8'].colors.accent['500']).toBe(
        '#6366f1'
      ) // Indigo for sophistication
      expect(designTokens.gradeBands['9-12'].colors.accent['500']).toBe(
        '#6b7280'
      ) // Neutral professional
    })
  })

  describe('Motion and Animation Tokens', () => {
    it('should respect reduced motion preferences', () => {
      // Mock reduced motion preference
      window.matchMedia = vi.fn().mockImplementation(query => ({
        matches: query.includes('prefers-reduced-motion'),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      }))

      const { result } = renderHook(() => useGradeBand())

      expect(result.current.preferences.isReducedMotion).toBe(true)

      act(() => {
        result.current.applyGradeBand()
      })

      const style = document.documentElement.style
      expect(style.getPropertyValue('--duration-fast')).toBe('0ms')
      expect(style.getPropertyValue('--duration-normal')).toBe('0ms')
      expect(style.getPropertyValue('--duration-slow')).toBe('0ms')
    })

    it('should have different motion speeds per grade band', () => {
      // Younger grades should have slower, more obvious animations
      expect(designTokens.gradeBands['k-2'].motion.duration.normal).toBe(
        '300ms'
      )
      // Older grades should have faster, more subtle animations
      expect(designTokens.gradeBands['9-12'].motion.duration.normal).toBe(
        '150ms'
      )
    })
  })
})
