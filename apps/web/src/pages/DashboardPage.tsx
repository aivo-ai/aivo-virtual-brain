import { useTranslation } from 'react-i18next'
import { useAuth } from '@/app/providers/AuthProvider'

export default function DashboardPage() {
  const { t } = useTranslation()
  const { user } = useAuth()

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            {t('dashboard.welcome_back', { name: user?.name })}
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            {t(`dashboard.${user?.role}_description`)}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              Dashboard Content
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              Dashboard implementation coming soon!
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
