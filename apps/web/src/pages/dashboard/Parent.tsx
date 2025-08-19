export default function ParentDashboard() {
  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Parent Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
            View your child&apos;s progress and communicate with teachers.
          </p>
        </div>

        {/* Children Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Emma Johnson
              </h3>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                Grade 3
              </span>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Math Progress</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">85%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Reading Level</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">Above Grade</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">IEP Goals</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">3/4 Met</span>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Alex Johnson
              </h3>
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Grade 1
              </span>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Math Progress</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">78%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">Reading Level</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">On Grade</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-500 dark:text-gray-400">IEP Goals</span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">2/3 Met</span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Communications */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Recent Messages
              </h3>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                      <span className="text-xs font-medium text-blue-800">MS</span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      Ms. Smith (Emma&apos;s Teacher)
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Emma did excellent work on her math assessment today...
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      2 hours ago
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                      <span className="text-xs font-medium text-green-800">MJ</span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      Mr. Jones (Alex&apos;s Teacher)
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Alex has been making great progress with his reading...
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      Yesterday
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                Upcoming Events
              </h3>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      Parent-Teacher Conference
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Emma&apos;s quarterly review
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      Mar 15
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      2:00 PM
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      IEP Review Meeting
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Alex&apos;s annual IEP update
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      Mar 22
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      10:00 AM
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
