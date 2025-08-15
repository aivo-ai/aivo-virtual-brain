import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import App from '@/app/App'

// Mock the analytics utility
vi.mock('@/utils/analytics', () => ({
  analytics: {
    initialize: vi.fn(),
    trackPageView: vi.fn(),
    trackNavigation: vi.fn(),
    track: vi.fn(),
    trackInteraction: vi.fn(),
    trackRouteGuard: vi.fn(),
    trackAuth: vi.fn(),
    updateContext: vi.fn(),
    getSessionInfo: vi.fn(),
  },
  useAnalytics: () => ({
    trackPageView: vi.fn(),
    trackNavigation: vi.fn(),
    track: vi.fn(),
    trackInteraction: vi.fn(),
    trackRouteGuard: vi.fn(),
    trackAuth: vi.fn(),
    updateContext: vi.fn(),
    getSessionInfo: vi.fn(),
  }),
  trackLinkClick: vi.fn(),
  trackButtonClick: vi.fn(),
  trackFormSubmission: vi.fn(),
}))

// Mock i18n
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, params?: any) => {
      if (params) {
        return `${key}_${JSON.stringify(params)}`
      }
      return key
    },
    i18n: {
      language: 'en',
      changeLanguage: vi.fn(),
    },
  }),
}))

// Mock lazy imports
vi.mock('@/pages/OnboardingPage', () => ({
  default: () => <div data-testid="onboarding-page">Onboarding Page</div>,
}))

vi.mock('@/pages/LearnersPage', () => ({
  default: () => <div data-testid="learners-page">Learners Page</div>,
}))

vi.mock('@/pages/LearnerDetailPage', () => ({
  default: () => (
    <div data-testid="learner-detail-page">Learner Detail Page</div>
  ),
}))

vi.mock('@/pages/SearchPage', () => ({
  default: () => <div data-testid="search-page">Search Page</div>,
}))

vi.mock('@/pages/TeacherPage', () => ({
  default: () => <div data-testid="teacher-page">Teacher Page</div>,
}))

vi.mock('@/pages/DistrictPage', () => ({
  default: () => <div data-testid="district-page">District Page</div>,
}))

describe('App Shell', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Clear localStorage
    localStorage.clear()
  })

  describe('Public Routes', () => {
    it('renders home page by default', async () => {
      render(<App />)

      await waitFor(() => {
        expect(screen.getByTestId('nav-logo-link')).toBeInTheDocument()
      })
    })

    it('renders login page', async () => {
      window.history.pushState({}, '', '/login')
      render(<App />)

      await waitFor(() => {
        expect(screen.getByText('auth.sign_in_title')).toBeInTheDocument()
      })
    })

    it('renders register page', async () => {
      window.history.pushState({}, '', '/register')
      render(<App />)

      await waitFor(() => {
        expect(screen.getByText('auth.register_title')).toBeInTheDocument()
      })
    })

    it('renders health page', async () => {
      window.history.pushState({}, '', '/health')
      render(<App />)

      await waitFor(() => {
        expect(screen.getByText('Health Check')).toBeInTheDocument()
      })
    })
  })

  describe('Navigation', () => {
    it('renders top navigation', async () => {
      render(<App />)

      await waitFor(() => {
        expect(
          screen.getByRole('navigation', { name: 'Main navigation' })
        ).toBeInTheDocument()
      })
    })

    it('shows login/register buttons when not authenticated', async () => {
      render(<App />)

      await waitFor(() => {
        expect(screen.getByTestId('nav-login-link')).toBeInTheDocument()
        expect(screen.getByTestId('nav-register-link')).toBeInTheDocument()
      })
    })

    it('does not show sidebar when not authenticated', async () => {
      render(<App />)

      await waitFor(() => {
        expect(
          screen.queryByRole('navigation', { name: 'Sidebar navigation' })
        ).not.toBeInTheDocument()
      })
    })
  })

  describe('Theme Support', () => {
    it('renders theme toggle button', async () => {
      render(<App />)

      await waitFor(() => {
        expect(screen.getByTestId('nav-theme-toggle')).toBeInTheDocument()
      })
    })

    it('applies default light theme', async () => {
      render(<App />)

      await waitFor(() => {
        expect(document.documentElement).toHaveClass('light')
      })
    })
  })

  describe('Error Boundary', () => {
    it('catches and displays errors', async () => {
      const ThrowError = () => {
        throw new Error('Test error')
      }

      // Mock the App to throw an error
      vi.doMock('@/pages/HomePage', () => ({
        default: ThrowError,
      }))

      render(<App />)

      await waitFor(() => {
        expect(screen.getByText('Something went wrong')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('provides skip link for keyboard navigation', async () => {
      render(<App />)

      await waitFor(() => {
        expect(screen.getByText('Skip to main content')).toBeInTheDocument()
      })
    })

    it('sets proper ARIA labels on navigation', async () => {
      render(<App />)

      await waitFor(() => {
        const nav = screen.getByRole('navigation', { name: 'Main navigation' })
        expect(nav).toBeInTheDocument()
      })
    })

    it('sets proper document language', async () => {
      render(<App />)

      await waitFor(() => {
        expect(document.documentElement).toHaveAttribute('lang', 'en')
      })
    })
  })

  describe('Route Guards', () => {
    it('redirects protected routes to login when not authenticated', async () => {
      window.history.pushState({}, '', '/dashboard')
      render(<App />)

      await waitFor(() => {
        expect(window.location.pathname).toBe('/login')
      })
    })

    it('allows access to public routes without authentication', async () => {
      window.history.pushState({}, '', '/health')
      render(<App />)

      await waitFor(() => {
        expect(screen.getByText('Health Check')).toBeInTheDocument()
      })
    })
  })

  describe('Mobile Responsiveness', () => {
    it('renders mobile menu toggle button', async () => {
      render(<App />)

      await waitFor(() => {
        expect(screen.getByTestId('nav-mobile-menu-toggle')).toBeInTheDocument()
      })
    })

    it('renders mobile theme toggle', async () => {
      render(<App />)

      await waitFor(() => {
        expect(
          screen.getByTestId('nav-mobile-theme-toggle')
        ).toBeInTheDocument()
      })
    })
  })
})
