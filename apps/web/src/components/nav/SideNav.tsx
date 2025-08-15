import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'
import { ROUTES, type UserRole } from '@/app/routes'
import { analytics, trackLinkClick } from '@/utils/analytics'

interface NavItem {
  label: string
  path: string
  icon: JSX.Element
  roles: UserRole[]
  children?: NavItem[]
}

export function SideNav() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const location = useLocation()

  if (!user) return null

  const navItems: NavItem[] = [
    {
      label: t('nav.dashboard'),
      path: ROUTES.DASHBOARD,
      icon: (
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
            d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2V7z"
          />
        </svg>
      ),
      roles: ['parent', 'teacher', 'district_admin'],
    },
    {
      label: t('nav.learners'),
      path: ROUTES.LEARNERS,
      icon: (
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
            d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"
          />
        </svg>
      ),
      roles: ['parent'],
    },
    {
      label: t('nav.teacher_section'),
      path: ROUTES.TEACHER,
      icon: (
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
            d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253z"
          />
        </svg>
      ),
      roles: ['teacher'],
      children: [
        {
          label: t('nav.my_classes'),
          path: ROUTES.TEACHER_CLASSES,
          icon: (
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
          ),
          roles: ['teacher'],
        },
        {
          label: t('nav.students'),
          path: ROUTES.TEACHER_STUDENTS,
          icon: (
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"
              />
            </svg>
          ),
          roles: ['teacher'],
        },
        {
          label: t('nav.assignments'),
          path: ROUTES.TEACHER_ASSIGNMENTS,
          icon: (
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
              />
            </svg>
          ),
          roles: ['teacher'],
        },
        {
          label: t('nav.reports'),
          path: ROUTES.TEACHER_REPORTS,
          icon: (
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          ),
          roles: ['teacher'],
        },
      ],
    },
    {
      label: t('nav.district_section'),
      path: ROUTES.DISTRICT,
      icon: (
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
            d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
          />
        </svg>
      ),
      roles: ['district_admin'],
      children: [
        {
          label: t('nav.overview'),
          path: ROUTES.DISTRICT_OVERVIEW,
          icon: (
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          ),
          roles: ['district_admin'],
        },
        {
          label: t('nav.schools'),
          path: ROUTES.DISTRICT_SCHOOLS,
          icon: (
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
              />
            </svg>
          ),
          roles: ['district_admin'],
        },
        {
          label: t('nav.teachers'),
          path: ROUTES.DISTRICT_TEACHERS,
          icon: (
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
          ),
          roles: ['district_admin'],
        },
        {
          label: t('nav.district_reports'),
          path: ROUTES.DISTRICT_REPORTS,
          icon: (
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          ),
          roles: ['district_admin'],
        },
        {
          label: t('nav.district_settings'),
          path: ROUTES.DISTRICT_SETTINGS,
          icon: (
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          ),
          roles: ['district_admin'],
        },
      ],
    },
    {
      label: t('nav.search'),
      path: ROUTES.SEARCH,
      icon: (
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
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      ),
      roles: ['parent', 'teacher', 'district_admin'],
    },
  ]

  const isActive = (path: string) => {
    if (path === ROUTES.DASHBOARD) {
      return location.pathname === path
    }
    return location.pathname.startsWith(path)
  }

  const isParentActive = (item: NavItem) => {
    return (
      isActive(item.path) ||
      (item.children?.some(child => isActive(child.path)) ?? false)
    )
  }

  const renderNavItem = (item: NavItem, level = 0) => {
    const canAccess = item.roles.includes(user.role)
    if (!canAccess) return null

    const active = isActive(item.path)
    const parentActive = isParentActive(item)

    const baseClasses = `flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 ${level > 0 ? 'ml-6' : ''}`
    const activeClasses = active
      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-900 dark:text-primary-100'
      : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'

    return (
      <div key={item.path}>
        <Link
          to={item.path}
          className={`${baseClasses} ${activeClasses}`}
          data-testid={`sidenav-${item.label.toLowerCase().replace(/\s+/g, '-')}-link`}
          aria-current={active ? 'page' : undefined}
          onClick={() => {
            trackLinkClick(item.path, item.label)
            analytics.track('sidenav_click', {
              item: item.label,
              path: item.path,
              level,
              user_role: user.role,
            })
          }}
        >
          <span className={level > 0 ? 'mr-2' : 'mr-3'}>{item.icon}</span>
          {item.label}
          {item.children && (
            <svg
              className={`ml-auto w-4 h-4 transition-transform ${parentActive ? 'rotate-90' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          )}
        </Link>

        {/* Render children if parent is active */}
        {item.children && parentActive && (
          <div className="mt-1 space-y-1">
            {item.children.map(child => renderNavItem(child, level + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <aside
      className="hidden lg:flex lg:flex-col lg:w-64 lg:fixed lg:inset-y-0 lg:pt-16 lg:bg-white lg:dark:bg-gray-800 lg:border-r lg:border-gray-200 lg:dark:border-gray-700"
      role="navigation"
      aria-label="Sidebar navigation"
    >
      <div className="flex-1 flex flex-col min-h-0 overflow-y-auto">
        <div className="flex-1 px-4 py-6 space-y-1">
          {/* User context indicator */}
          <div className="mb-6 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-primary-500 rounded-full" />
              <span className="text-xs text-gray-600 dark:text-gray-400 font-medium uppercase tracking-wide">
                {t(`nav.${user.dash_context}_context`)}
              </span>
            </div>
            <p className="text-sm text-gray-900 dark:text-gray-100 mt-1">
              {user.role === 'parent' && t('nav.parent_description')}
              {user.role === 'teacher' && t('nav.teacher_description')}
              {user.role === 'district_admin' &&
                t('nav.district_admin_description')}
            </p>
          </div>

          {/* Navigation items */}
          {navItems.map(item => renderNavItem(item))}
        </div>

        {/* Footer section */}
        <div className="flex-shrink-0 p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
            <p>{t('nav.version')} 1.0.0</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
