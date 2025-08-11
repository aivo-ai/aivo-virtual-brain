import { describe, test, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import HomePage from '@/pages/HomePage'

// Mock i18next
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: {
      changeLanguage: () => new Promise(() => {}),
    },
  }),
}))

describe('HomePage', () => {
  const renderWithRouter = (component: React.ReactElement) => {
    return render(<BrowserRouter>{component}</BrowserRouter>)
  }

  test('should render homepage with main heading', () => {
    renderWithRouter(<HomePage />)

    const heading = screen.getByRole('heading', { level: 1 })
    expect(heading).toBeInTheDocument()
    expect(heading).toHaveTextContent('pages.home.title')
  })

  test('should render get started button with click handler', () => {
    renderWithRouter(<HomePage />)

    const getStartedButton = screen.getByTestId('get-started-button')
    expect(getStartedButton).toBeInTheDocument()
    expect(getStartedButton).toHaveTextContent('pages.home.cta')
  })

  test('should render health check link with valid route', () => {
    renderWithRouter(<HomePage />)

    const healthLink = screen.getByTestId('health-check-link')
    expect(healthLink).toBeInTheDocument()
    expect(healthLink).toHaveAttribute('href', '/health')
  })

  test('should render feature grid', () => {
    renderWithRouter(<HomePage />)

    const features = [
      'Virtual Brain Simulation',
      'Real-time Analytics',
      'Research Integration',
    ]

    features.forEach(feature => {
      expect(screen.getByText(feature)).toBeInTheDocument()
    })
  })
})
