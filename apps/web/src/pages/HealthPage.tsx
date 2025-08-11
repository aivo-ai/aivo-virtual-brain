import { useTranslation } from 'react-i18next'
import { useState, useEffect } from 'react'

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  services: {
    database: 'up' | 'down'
    api: 'up' | 'down'
    cache: 'up' | 'down'
  }
}

function HealthPage() {
  const { t } = useTranslation()
  const [healthData, setHealthData] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Simulate health check API call
    const fetchHealthData = async () => {
      setLoading(true)

      // Mock API delay
      await new Promise(resolve => setTimeout(resolve, 1000))

      // Mock health data
      setHealthData({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: {
          database: 'up',
          api: 'up',
          cache: 'up',
        },
      })

      setLoading(false)
    }

    fetchHealthData()
  }, [])

  const handleRefresh = () => {
    setHealthData(null)
    setLoading(true)

    // Simulate refresh
    setTimeout(() => {
      setHealthData({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        services: {
          database: 'up',
          api: 'up',
          cache: 'up',
        },
      })
      setLoading(false)
    }, 800)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
      case 'up':
        return 'text-green-600 bg-green-100'
      case 'degraded':
        return 'text-yellow-600 bg-yellow-100'
      case 'unhealthy':
      case 'down':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          {t('pages.health.title')}
        </h1>
        <p className="mt-4 text-lg text-gray-600">
          {t('pages.health.description')}
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border p-6">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-semibold text-gray-900">System Status</h2>

          <button
            onClick={handleRefresh}
            disabled={loading}
            className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            data-testid="refresh-button"
          >
            {loading ? t('common.loading') : t('common.retry')}
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            <p className="mt-4 text-gray-600">{t('common.loading')}</p>
          </div>
        ) : healthData ? (
          <div className="space-y-6">
            {/* Overall Status */}
            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
              <div>
                <h3 className="text-lg font-medium text-gray-900">
                  Overall Status
                </h3>
                <p className="text-sm text-gray-600">
                  Last updated:{' '}
                  {new Date(healthData.timestamp).toLocaleString()}
                </p>
              </div>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${getStatusColor(healthData.status)}`}
              >
                {healthData.status}
              </span>
            </div>

            {/* Service Status */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                Service Status
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {Object.entries(healthData.services).map(
                  ([service, status]) => (
                    <div key={service} className="bg-gray-50 p-4 rounded-lg">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-900 capitalize">
                          {service}
                        </h4>
                        <span
                          className={`px-2 py-1 rounded-full text-xs font-medium uppercase ${getStatusColor(status)}`}
                        >
                          {status}
                        </span>
                      </div>
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-600">{t('common.error')}</p>
            <button
              onClick={handleRefresh}
              className="mt-4 text-primary-600 hover:text-primary-700"
              data-testid="retry-button"
            >
              {t('common.retry')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default HealthPage
