import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { ROUTES } from '@/types/routes'

function HomePage() {
  const { t } = useTranslation()

  const handleGetStarted = () => {
    // Example handler for CTA guard testing
    console.log('Get started clicked')
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 sm:text-5xl md:text-6xl">
          {t('pages.home.title')}
        </h1>

        <p className="mt-6 text-xl text-gray-600 max-w-2xl mx-auto">
          {t('pages.home.subtitle')}
        </p>

        <div className="mt-10 flex justify-center space-x-4">
          {/* Button with handler - should pass CTA guard */}
          <button
            onClick={handleGetStarted}
            className="bg-primary-600 text-white px-8 py-3 rounded-md text-lg font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-colors"
            data-testid="get-started-button"
          >
            {t('pages.home.cta')}
          </button>

          {/* Link to valid route - should pass CTA guard */}
          <Link
            to={ROUTES.HEALTH}
            className="border border-primary-600 text-primary-600 px-8 py-3 rounded-md text-lg font-medium hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-colors"
            data-testid="health-check-link"
          >
            Health Check
          </Link>
        </div>

        {/* Grid of features */}
        <div className="mt-20">
          <h2 className="text-2xl font-bold text-gray-900 mb-8 text-center">
            {t('pages.home.features.title')}
          </h2>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
            <div className="bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Virtual Brain Simulation
              </h3>
              <p className="text-gray-600">
                Advanced AI-powered brain simulation capabilities for research
                and development.
              </p>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Real-time Analytics
              </h3>
              <p className="text-gray-600">
                Monitor and analyze brain activity patterns in real-time with
                detailed metrics.
              </p>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-sm border">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Research Integration
              </h3>
              <p className="text-gray-600">
                Seamlessly integrate with existing research tools and workflows.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HomePage
