import { useTranslation } from 'react-i18next'

function DevMocksPage() {
  const { t } = useTranslation()

  const mockData = {
    users: [
      { id: 1, name: 'John Doe', email: 'john@example.com', role: 'admin' },
      { id: 2, name: 'Jane Smith', email: 'jane@example.com', role: 'user' },
      { id: 3, name: 'Bob Johnson', email: 'bob@example.com', role: 'user' },
    ],
    settings: {
      theme: 'light',
      notifications: true,
      autoSave: false,
    },
    apiResponses: {
      '/api/health': { status: 'healthy', timestamp: '2025-08-11T15:30:00Z' },
      '/api/users': { count: 3, users: [] },
      '/api/config': { version: '1.0.0', env: 'development' },
    },
  }

  const handleCopyData = (data: unknown) => {
    navigator.clipboard
      .writeText(JSON.stringify(data, null, 2))
      .then(() => {
        alert('Data copied to clipboard!')
      })
      .catch(() => {
        alert('Failed to copy data')
      })
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          {t('pages.dev_mocks.title')}
        </h1>
        <p className="mt-4 text-lg text-gray-600">
          {t('pages.dev_mocks.description')}
        </p>
      </div>

      <div className="space-y-8">
        {/* Mock Users */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Mock Users</h2>
            <button
              onClick={() => handleCopyData(mockData.users)}
              className="bg-gray-100 text-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              data-testid="copy-users-button"
            >
              Copy JSON
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Role
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {mockData.users.map(user => (
                  <tr key={user.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {user.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {user.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {user.email}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          user.role === 'admin'
                            ? 'bg-purple-100 text-purple-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {user.role}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Mock Settings */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Mock Settings
            </h2>
            <button
              onClick={() => handleCopyData(mockData.settings)}
              className="bg-gray-100 text-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              data-testid="copy-settings-button"
            >
              Copy JSON
            </button>
          </div>

          <pre className="bg-gray-50 p-4 rounded text-sm overflow-x-auto">
            {JSON.stringify(mockData.settings, null, 2)}
          </pre>
        </div>

        {/* Mock API Responses */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Mock API Responses
            </h2>
            <button
              onClick={() => handleCopyData(mockData.apiResponses)}
              className="bg-gray-100 text-gray-700 px-3 py-1 rounded text-sm hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
              data-testid="copy-api-button"
            >
              Copy JSON
            </button>
          </div>

          <div className="space-y-4">
            {Object.entries(mockData.apiResponses).map(
              ([endpoint, response]) => (
                <div key={endpoint} className="border rounded p-4">
                  <h3 className="font-medium text-gray-900 mb-2">{endpoint}</h3>
                  <pre className="bg-gray-50 p-3 rounded text-xs overflow-x-auto">
                    {JSON.stringify(response, null, 2)}
                  </pre>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DevMocksPage
