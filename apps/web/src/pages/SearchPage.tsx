import { useTranslation } from 'react-i18next'

export default function SearchPage() {
  const { t } = useTranslation()

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
          {t('search.title')}
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          Search functionality - Coming soon!
        </p>
      </div>
    </div>
  )
}
