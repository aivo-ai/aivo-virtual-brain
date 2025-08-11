import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { ROUTES } from '@/types/routes'
import HomePage from '@/pages/HomePage'
import HealthPage from '@/pages/HealthPage'
import DevMocksPage from '@/pages/DevMocksPage'
import NotFoundPage from '@/pages/NotFoundPage'

function App() {
  const { t } = useTranslation()

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Skip link for accessibility */}
        <a href="#main" className="skip-link">
          {t('common.skip_to_content')}
        </a>

        {/* Navigation */}
        <nav
          className="bg-white shadow-sm border-b"
          role="navigation"
          aria-label="Main navigation"
        >
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex items-center space-x-8">
                <Link
                  to={ROUTES.HOME}
                  className="text-xl font-bold text-primary-600 hover:text-primary-700 focus:text-primary-700"
                  data-testid="nav-home-link"
                >
                  {t('nav.home')}
                </Link>

                <div className="hidden sm:flex sm:space-x-4">
                  <Link
                    to={ROUTES.HEALTH}
                    className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500"
                    data-testid="nav-health-link"
                  >
                    {t('nav.health')}
                  </Link>

                  <Link
                    to={ROUTES.DEV_MOCKS}
                    className="text-gray-600 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary-500"
                    data-testid="nav-dev-mocks-link"
                  >
                    {t('nav.dev_mocks')}
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <main id="main" role="main">
          <Routes>
            <Route path={ROUTES.HOME} element={<HomePage />} />
            <Route path={ROUTES.HEALTH} element={<HealthPage />} />
            <Route path={ROUTES.DEV_MOCKS} element={<DevMocksPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
