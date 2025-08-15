import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ROUTES } from '@/app/routes'

export default function LoginPage() {
  const { t } = useTranslation()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            {t('auth.sign_in_title')}
          </h2>
        </div>
        <div className="mt-8 p-8 bg-white dark:bg-gray-800 rounded-lg shadow">
          <p className="text-center text-gray-600 dark:text-gray-400">
            Login page - Coming soon!
          </p>
          <div className="mt-4 text-center">
            <Link
              to={ROUTES.HOME}
              className="text-primary-600 hover:text-primary-500"
              data-testid="back-to-home"
            >
              {t('common.back_to_home')}
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
