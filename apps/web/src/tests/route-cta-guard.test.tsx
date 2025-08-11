import { describe, test, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { validateAllCTAs } from '@/utils/cta-guard'
import { getAllRoutes } from '@/types/routes'
import App from '@/App'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      changeLanguage: () => new Promise(() => {}),
    },
  }),
  initReactI18next: {
    type: '3rdParty',
    init: () => {},
  },
}))

describe('Route CTA Guard', () => {
  test('should validate that all routes in manifest are strings', () => {
    const routes = getAllRoutes()

    expect(routes).toHaveLength(3)
    expect(routes).toContain('/')
    expect(routes).toContain('/health')
    expect(routes).toContain('/_dev/mocks')

    routes.forEach(route => {
      expect(typeof route).toBe('string')
      expect(route).toMatch(/^\//)
    })
  })

  test('should validate all CTA elements in the app have handlers or valid routes', () => {
    const { container } = render(<App />)

    const validation = validateAllCTAs(container)

    if (!validation.valid) {
      console.error('CTA Guard violations:')
      validation.violations.forEach((violation, index) => {
        console.error(`${index + 1}. ${violation.type}:`, {
          element: violation.element.outerHTML,
          reason: violation.reason,
          href: violation.href,
        })
      })
    }

    expect(validation.valid).toBe(true)
    expect(validation.violations).toHaveLength(0)
  })

  test('should fail when a CTA element has invalid route', () => {
    // Create a test component with invalid route
    const TestComponent = () => (
      <div>
        <a href="/invalid-route" data-testid="invalid-link">
          Invalid Link
        </a>
      </div>
    )

    const { container } = render(<TestComponent />)
    const validation = validateAllCTAs(container)

    expect(validation.valid).toBe(false)
    expect(validation.violations).toHaveLength(1)
    expect(validation.violations[0].reason).toContain('not in route manifest')
  })

  test('should fail when a button has no handler', () => {
    // Create a test component with button without handler
    const TestComponent = () => (
      <div>
        <button data-testid="no-handler-button">No Handler</button>
      </div>
    )

    const { container } = render(<TestComponent />)
    const validation = validateAllCTAs(container)

    expect(validation.valid).toBe(false)
    expect(validation.violations).toHaveLength(1)
    expect(validation.violations[0].reason).toContain('no click handler')
  })

  test('should pass for buttons with onclick handlers', () => {
    const TestComponent = () => (
      <div>
        <button onClick={() => {}} data-testid="with-handler-button">
          With Handler
        </button>
      </div>
    )

    const { container } = render(<TestComponent />)
    const validation = validateAllCTAs(container)

    expect(validation.valid).toBe(true)
  })

  test('should pass for submit buttons without handlers', () => {
    const TestComponent = () => (
      <form>
        <button type="submit" data-testid="submit-button">
          Submit
        </button>
      </form>
    )

    const { container } = render(<TestComponent />)
    const validation = validateAllCTAs(container)

    expect(validation.valid).toBe(true)
  })

  test('should pass for external links', () => {
    const TestComponent = () => (
      <div>
        <a href="https://example.com" data-testid="external-link">
          External
        </a>
        <a href="mailto:test@example.com" data-testid="email-link">
          Email
        </a>
        <a href="#section" data-testid="anchor-link">
          Anchor
        </a>
      </div>
    )

    const { container } = render(<TestComponent />)
    const validation = validateAllCTAs(container)

    expect(validation.valid).toBe(true)
  })
})
