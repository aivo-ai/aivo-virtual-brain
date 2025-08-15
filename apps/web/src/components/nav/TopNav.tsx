import { useState, useRef, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { useTheme } from '@/app/providers/ThemeProvider'
import { ROUTES } from '@/app/routes'
import { analytics, trackLinkClick } from '@/utils/analytics'

export function TopNav() {
  const { t } = useTranslation()
  const { user, logout, isAuthenticated } = useAuth()
  const { theme, setTheme } = useTheme()
  const location = useLocation()
  const navigate = useNavigate()

  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(event.target as Node)
      ) {
        setIsUserMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Close mobile menu when route changes
  useEffect(() => {
    setIsMobileMenuOpen(false)
  }, [location.pathname])

  const handleLogout = async () => {
    try {
      await logout()
      navigate(ROUTES.HOME)
      analytics.track('nav_logout')
    } catch (error) {
      console.error('Logout error:', error)
    }
  }

  const handleThemeToggle = () => {
    const nextTheme =
      theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light'
    setTheme(nextTheme)
    analytics.track('nav_theme_toggle', { theme: nextTheme })
  }

  const handleMobileMenuToggle = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen)
    analytics.track('nav_mobile_menu_toggle', { open: !isMobileMenuOpen })
  }

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return (
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
            />
          </svg>
        )
      case 'dark':
        return (
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
            />
          </svg>
        )
      default:
        return (
          <svg
            className="w-5 h-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
            />
          </svg>
        )
    }
  }

  return (
    <nav
      className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and brand */}
          <div className="flex items-center">
            <Link
              to={isAuthenticated ? ROUTES.DASHBOARD : ROUTES.HOME}
              className="flex items-center space-x-2 text-xl font-bold text-primary-600 hover:text-primary-700 focus:text-primary-700 transition-colors"
              data-testid="nav-logo-link"
              onClick={() =>
                trackLinkClick(
                  isAuthenticated ? ROUTES.DASHBOARD : ROUTES.HOME,
                  'Aivo Logo'
                )
              }
            >
              <svg
                className="w-8 h-8"
                fill="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path d="M12 2L3 7l9 5 9-5-9-5zM3 17l9 5 9-5M3 12l9 5 9-5" />
              </svg>
              <span>{t('nav.brand')}</span>
            </Link>
          </div>

          {/* Desktop navigation */}
          <div className="hidden md:flex md:items-center md:space-x-4">
            {/* Search */}
            {isAuthenticated && (
              <Link
                to={ROUTES.SEARCH}
                className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 px-3 py-2 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
                data-testid="nav-search-link"
                onClick={() => trackLinkClick(ROUTES.SEARCH, t('nav.search'))}
              >
                <svg
                  className="w-5 h-5 inline mr-2"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                {t('nav.search')}
              </Link>
            )}

            {/* Theme toggle */}
            <button
              onClick={handleThemeToggle}
              className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 p-2 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
              data-testid="nav-theme-toggle"
              aria-label={t('nav.toggle_theme')}
            >
              {getThemeIcon()}
            </button>

            {/* User menu or auth links */}
            {isAuthenticated && user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center space-x-2 text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-md p-2 transition-colors"
                  data-testid="nav-user-menu-toggle"
                  aria-expanded={isUserMenuOpen}
                  aria-haspopup="true"
                >
                  {user.avatar ? (
                    <img
                      className="h-8 w-8 rounded-full"
                      src={user.avatar}
                      alt={user.name}
                    />
                  ) : (
                    <div className="h-8 w-8 rounded-full bg-primary-500 flex items-center justify-center text-white text-sm font-medium">
                      {user.name.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <span className="text-sm font-medium">{user.name}</span>
                  <svg
                    className={`w-4 h-4 transition-transform ${isUserMenuOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>

                {/* User dropdown menu */}
                {isUserMenuOpen && (
                  <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50">
                    <div className="py-1">
                      <div className="px-4 py-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                        {user.email}
                      </div>
                      <Link
                        to="/profile"
                        className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        data-testid="nav-profile-link"
                        onClick={() => {
                          setIsUserMenuOpen(false)
                          trackLinkClick('/profile', t('nav.profile'))
                        }}
                      >
                        {t('nav.profile')}
                      </Link>
                      <Link
                        to="/settings"
                        className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        data-testid="nav-settings-link"
                        onClick={() => {
                          setIsUserMenuOpen(false)
                          trackLinkClick('/settings', t('nav.settings'))
                        }}
                      >
                        {t('nav.settings')}
                      </Link>
                      <button
                        onClick={handleLogout}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        data-testid="nav-logout-button"
                      >
                        {t('nav.logout')}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex items-center space-x-2">
                <Link
                  to={ROUTES.LOGIN}
                  className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 px-3 py-2 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
                  data-testid="nav-login-link"
                  onClick={() => trackLinkClick(ROUTES.LOGIN, t('nav.login'))}
                >
                  {t('nav.login')}
                </Link>
                <Link
                  to={ROUTES.REGISTER}
                  className="bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                  data-testid="nav-register-link"
                  onClick={() =>
                    trackLinkClick(ROUTES.REGISTER, t('nav.register'))
                  }
                >
                  {t('nav.register')}
                </Link>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center space-x-2">
            {/* Theme toggle for mobile */}
            <button
              onClick={handleThemeToggle}
              className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 p-2 rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
              data-testid="nav-mobile-theme-toggle"
              aria-label={t('nav.toggle_theme')}
            >
              {getThemeIcon()}
            </button>

            <button
              onClick={handleMobileMenuToggle}
              className="text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded-md p-2 transition-colors"
              data-testid="nav-mobile-menu-toggle"
              aria-expanded={isMobileMenuOpen}
              aria-label={t('nav.toggle_menu')}
            >
              <svg
                className="w-6 h-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                {isMobileMenuOpen ? (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                ) : (
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                )}
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
          <div className="px-2 pt-2 pb-3 space-y-1">
            {isAuthenticated && user ? (
              <>
                <div className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700 mb-2">
                  {user.name} ({user.email})
                </div>
                <Link
                  to={ROUTES.SEARCH}
                  className="block px-3 py-2 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                  data-testid="nav-mobile-search-link"
                  onClick={() => trackLinkClick(ROUTES.SEARCH, t('nav.search'))}
                >
                  {t('nav.search')}
                </Link>
                <Link
                  to="/profile"
                  className="block px-3 py-2 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                  data-testid="nav-mobile-profile-link"
                  onClick={() => trackLinkClick('/profile', t('nav.profile'))}
                >
                  {t('nav.profile')}
                </Link>
                <Link
                  to="/settings"
                  className="block px-3 py-2 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                  data-testid="nav-mobile-settings-link"
                  onClick={() => trackLinkClick('/settings', t('nav.settings'))}
                >
                  {t('nav.settings')}
                </Link>
                <button
                  onClick={handleLogout}
                  className="block w-full text-left px-3 py-2 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                  data-testid="nav-mobile-logout-button"
                >
                  {t('nav.logout')}
                </button>
              </>
            ) : (
              <>
                <Link
                  to={ROUTES.LOGIN}
                  className="block px-3 py-2 text-base font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
                  data-testid="nav-mobile-login-link"
                  onClick={() => trackLinkClick(ROUTES.LOGIN, t('nav.login'))}
                >
                  {t('nav.login')}
                </Link>
                <Link
                  to={ROUTES.REGISTER}
                  className="block px-3 py-2 text-base font-medium text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-md transition-colors"
                  data-testid="nav-mobile-register-link"
                  onClick={() =>
                    trackLinkClick(ROUTES.REGISTER, t('nav.register'))
                  }
                >
                  {t('nav.register')}
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
