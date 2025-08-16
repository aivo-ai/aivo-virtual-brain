import { useEffect } from 'react'
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useLocation,
} from 'react-router-dom'
import { useTranslation } from 'react-i18next'

// Providers
import { ErrorBoundary } from './providers/ErrorBoundary'
import { AuthProvider, useAuth } from './providers/AuthProvider'
import { QueryProvider } from './providers/QueryProvider'
import { I18nProvider } from './providers/I18nProvider'
import { ThemeProvider } from './providers/ThemeProvider'

// Components
import { TopNav } from '@/components/nav/TopNav'
import { SideNav } from '@/components/nav/SideNav'

// Routes and utilities
import { ROUTES, canAccessRoute, isPublicRoute } from './routes'
import { analytics } from '@/utils/analytics'

// Pages (these would be created separately)
import Landing from '@/pages/Landing'
import HomePage from '@/pages/HomePage'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import ResetPasswordPage from '@/pages/ResetPasswordPage'
import TwoFASetupPage from '@/pages/TwoFASetupPage'
import DashboardPage from '@/pages/DashboardPage'
import NotFoundPage from '@/pages/NotFoundPage'
import HealthPage from '@/pages/HealthPage'
import DevMocksPage from '@/pages/DevMocksPage'

// Lazy load pages for better performance
import { lazy, Suspense } from 'react'

const OnboardingPage = lazy(() => import('@/pages/OnboardingPage'))
const LearnersPage = lazy(() => import('@/pages/LearnersPage'))
const LearnerDetailPage = lazy(() => import('@/pages/LearnerDetailPage'))
const SearchPage = lazy(() => import('@/pages/SearchPage'))
const TeacherPage = lazy(() => import('@/pages/TeacherPage'))
const DistrictPage = lazy(() => import('@/pages/DistrictPage'))

// Loading component
function PageLoading() {
  const { t } = useTranslation()
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">
          {t('common.loading')}
        </p>
      </div>
    </div>
  )
}

// Route guard component
interface RouteGuardProps {
  children: React.ReactNode
  requiredRole?: string[]
  redirectTo?: string
}

function RouteGuard({ children, redirectTo = ROUTES.LOGIN }: RouteGuardProps) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  // Show loading while checking auth
  if (isLoading) {
    return <PageLoading />
  }

  // Check if route is public
  if (isPublicRoute(location.pathname)) {
    return <>{children}</>
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    analytics.trackRouteGuard(location.pathname, false, 'Not authenticated')
    return <Navigate to={redirectTo} state={{ from: location }} replace />
  }

  // Check role-based access
  if (!canAccessRoute(location.pathname, user.role)) {
    analytics.trackRouteGuard(
      location.pathname,
      false,
      'Insufficient permissions',
      user.role
    )
    return <Navigate to={ROUTES.DASHBOARD} replace />
  }

  analytics.trackRouteGuard(location.pathname, true, undefined, user.role)
  return <>{children}</>
}

// Analytics tracker for route changes
function RouteTracker() {
  const location = useLocation()
  const { user } = useAuth()

  useEffect(() => {
    // Track page view
    analytics.trackPageView(location.pathname, {
      title: document.title,
      user_id: user?.id,
    })
  }, [location.pathname, user?.id])

  return null
}

// App shell component
function AppShell() {
  const { isAuthenticated } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Skip link for accessibility */}
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 bg-primary-600 text-white px-4 py-2 z-50 focus:z-50"
      >
        Skip to main content
      </a>

      <RouteTracker />
      <TopNav />

      <div className="flex">
        {isAuthenticated && <SideNav />}

        <main
          id="main"
          className={`flex-1 ${isAuthenticated ? 'lg:ml-64' : ''} focus:outline-none`}
          tabIndex={-1}
        >
          <div className="min-h-screen">
            <Suspense fallback={<PageLoading />}>
              <Routes>
                {/* Public routes */}
                <Route path={ROUTES.HOME} element={<Landing />} />
                <Route path={ROUTES.LOGIN} element={<LoginPage />} />
                <Route path={ROUTES.REGISTER} element={<RegisterPage />} />
                <Route
                  path={ROUTES.RESET_PASSWORD}
                  element={<ResetPasswordPage />}
                />
                <Route path={ROUTES.HEALTH} element={<HealthPage />} />
                <Route path={ROUTES.DEV_MOCKS} element={<DevMocksPage />} />

                {/* Protected routes */}
                <Route
                  path={ROUTES.DASHBOARD}
                  element={
                    <RouteGuard>
                      <DashboardPage />
                    </RouteGuard>
                  }
                />

                {/* 2FA Setup - Protected route */}
                <Route
                  path={ROUTES.TWO_FA_SETUP}
                  element={
                    <RouteGuard>
                      <TwoFASetupPage />
                    </RouteGuard>
                  }
                />

                {/* Onboarding routes */}
                <Route
                  path="/onboarding/*"
                  element={
                    <RouteGuard>
                      <OnboardingPage />
                    </RouteGuard>
                  }
                />

                {/* Parent routes */}
                <Route
                  path={ROUTES.LEARNERS}
                  element={
                    <RouteGuard>
                      <LearnersPage />
                    </RouteGuard>
                  }
                />
                <Route
                  path="/learners/:id/*"
                  element={
                    <RouteGuard>
                      <LearnerDetailPage />
                    </RouteGuard>
                  }
                />

                {/* Teacher routes */}
                <Route
                  path="/teacher/*"
                  element={
                    <RouteGuard>
                      <TeacherPage />
                    </RouteGuard>
                  }
                />

                {/* District admin routes */}
                <Route
                  path="/district/*"
                  element={
                    <RouteGuard>
                      <DistrictPage />
                    </RouteGuard>
                  }
                />

                {/* Search */}
                <Route
                  path={ROUTES.SEARCH}
                  element={
                    <RouteGuard>
                      <SearchPage />
                    </RouteGuard>
                  }
                />

                {/* Catch-all route */}
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  )
}

// Main App component with all providers
function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ThemeProvider>
          <QueryProvider>
            <I18nProvider>
              <Router>
                <AppShell />
              </Router>
            </I18nProvider>
          </QueryProvider>
        </ThemeProvider>
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
