import '@testing-library/jest-dom'
import { afterEach, beforeAll } from 'vitest'
import { cleanup } from '@testing-library/react'

// Runs a cleanup after each test case (e.g. clearing jsdom)
afterEach(() => {
  cleanup()
})

// Mock window.matchMedia for theme provider tests
beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => {},
    }),
  })

  // Mock localStorage
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
      clear: () => {},
    },
    writable: true,
  })
})
