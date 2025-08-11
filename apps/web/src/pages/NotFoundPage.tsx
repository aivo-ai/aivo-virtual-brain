import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ROUTES } from '@/types/routes'

function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center">
        {/* 404 illustration */}
        <div className="mb-8">
          <h1 className="text-9xl font-bold text-primary-200">404</h1>
        </div>

        <h2 className="text-3xl font-bold text-gray-900 mb-4">
          {t('pages.not_found.title')}
        </h2>

        <p className="text-lg text-gray-600 mb-8">
          {t('pages.not_found.description')}
        </p>

        <Link
          to={ROUTES.HOME}
          className="bg-primary-600 text-white px-6 py-3 rounded-md text-lg font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-colors"
          data-testid="go-home-link"
        >
          {t('pages.not_found.go_home')}
        </Link>
      </div>
    </div>
  )
}

export default NotFoundPage
