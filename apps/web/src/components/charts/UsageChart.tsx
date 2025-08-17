import React, { useState, useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Button } from '../ui/Button'
import {
  Download,
  TrendingUp,
  Target,
  Award,
  Activity,
  BarChart3,
} from '../ui/Icons'
export interface UsageMetric {
  name: string
  current: number
  previous: number
  trend: 'up' | 'down' | 'stable'
  description: string
  category: 'engagement' | 'performance' | 'activity'
}

export interface UsageData {
  date: string
  activeUsers: number
  sessionsCompleted: number
  avgSessionTime: number
  engagementScore: number
  completionRate: number
}

export interface UsageChartProps {
  data: UsageData[]
  metrics: UsageMetric[]
  role: 'parent' | 'teacher' | 'district'
  className?: string
}

export const UsageChart: React.FC<UsageChartProps> = ({
  data,
  metrics,
  role,
  className = '',
}) => {
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'chart' | 'table'>('chart')
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d')
  const [filterCategory, setFilterCategory] = useState<
    'all' | 'engagement' | 'performance' | 'activity'
  >('all')

  // Filter data based on time range
  const filteredData = useMemo(() => {
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90
    return data.slice(-days)
  }, [data, timeRange])

  // Filter metrics based on category
  const filteredMetrics = useMemo(() => {
    if (filterCategory === 'all') return metrics
    return metrics.filter(metric => metric.category === filterCategory)
  }, [metrics, filterCategory])

  // Calculate trend indicators
  const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-500" />
      case 'down':
        return <TrendingUp className="w-4 h-4 text-red-500 rotate-180" />
      default:
        return <div className="w-4 h-4 bg-gray-400 rounded-full" />
    }
  }

  // Format numbers for display
  const formatNumber = (
    num: number,
    type: 'percentage' | 'time' | 'count' = 'count'
  ) => {
    switch (type) {
      case 'percentage':
        return `${num.toFixed(1)}%`
      case 'time':
        return `${Math.floor(num / 60)}h ${num % 60}m`
      default:
        return num.toLocaleString()
    }
  }

  // Custom tooltip for charts
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border rounded-lg shadow-lg">
          <p className="font-semibold">{`Date: ${label}`}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }}>
              {`${entry.dataKey}: ${entry.value}`}
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  // Export functionality
  const handleExport = () => {
    const csvContent = [
      [
        'Date',
        'Active Users',
        'Sessions Completed',
        'Avg Session Time',
        'Engagement Score',
        'Completion Rate',
      ],
      ...filteredData.map(row => [
        row.date,
        row.activeUsers,
        row.sessionsCompleted,
        row.avgSessionTime,
        row.engagementScore,
        row.completionRate,
      ]),
    ]

    const csvString = csvContent.map(row => row.join(',')).join('\n')
    const blob = new Blob([csvString], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `usage-data-${role}-${timeRange}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  const renderChart = () => {
    if (viewMode === 'table') {
      return (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse border border-gray-200">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-200 p-2 text-left">Date</th>
                <th className="border border-gray-200 p-2 text-left">
                  Active Users
                </th>
                <th className="border border-gray-200 p-2 text-left">
                  Sessions
                </th>
                <th className="border border-gray-200 p-2 text-left">
                  Avg Time
                </th>
                <th className="border border-gray-200 p-2 text-left">
                  Engagement
                </th>
                <th className="border border-gray-200 p-2 text-left">
                  Completion
                </th>
              </tr>
            </thead>
            <tbody>
              {filteredData.map((row, index) => (
                <tr key={index} className="hover:bg-gray-50">
                  <td className="border border-gray-200 p-2">{row.date}</td>
                  <td className="border border-gray-200 p-2">
                    {formatNumber(row.activeUsers)}
                  </td>
                  <td className="border border-gray-200 p-2">
                    {formatNumber(row.sessionsCompleted)}
                  </td>
                  <td className="border border-gray-200 p-2">
                    {formatNumber(row.avgSessionTime, 'time')}
                  </td>
                  <td className="border border-gray-200 p-2">
                    {formatNumber(row.engagementScore, 'percentage')}
                  </td>
                  <td className="border border-gray-200 p-2">
                    {formatNumber(row.completionRate, 'percentage')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }

    // Chart view
    if (selectedMetric) {
      const metric = filteredMetrics.find(m => m.name === selectedMetric)
      if (!metric) return null

      // Render specific metric chart based on type
      return (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey={metric.name.toLowerCase().replace(/\s+/g, '')}
              stroke="#3B82F6"
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      )
    }

    // Overview chart with multiple metrics
    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={filteredData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="activeUsers" fill="#3B82F6" />
          <Bar dataKey="sessionsCompleted" fill="#10B981" />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  return (
    <Card className={`${className}`}>
      <CardHeader>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Usage Analytics - {role.charAt(0).toUpperCase() + role.slice(1)}
          </CardTitle>

          <div className="flex flex-wrap gap-2">
            {/* Time Range Filter */}
            <div className="flex rounded-lg border">
              {(['7d', '30d', '90d'] as const).map(range => (
                <Button
                  key={range}
                  size="sm"
                  variant={timeRange === range ? 'primary' : 'ghost'}
                  onClick={() => setTimeRange(range)}
                  className="rounded-none first:rounded-l-lg last:rounded-r-lg"
                >
                  {range}
                </Button>
              ))}
            </div>

            {/* Category Filter */}
            <select
              value={filterCategory}
              onChange={e => setFilterCategory(e.target.value as any)}
              className="px-3 py-1 border rounded-lg text-sm"
              aria-label="Filter by category"
            >
              <option value="all">All Categories</option>
              <option value="engagement">Engagement</option>
              <option value="performance">Performance</option>
              <option value="activity">Activity</option>
            </select>

            {/* View Mode Toggle */}
            <div className="flex rounded-lg border">
              <Button
                size="sm"
                variant={viewMode === 'chart' ? 'primary' : 'ghost'}
                onClick={() => setViewMode('chart')}
                className="rounded-none rounded-l-lg"
              >
                <BarChart3 className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant={viewMode === 'table' ? 'primary' : 'ghost'}
                onClick={() => setViewMode('table')}
                className="rounded-none rounded-r-lg"
              >
                Table
              </Button>
            </div>

            {/* Export Button */}
            <Button
              size="sm"
              variant="outline"
              onClick={handleExport}
              className="flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {/* Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
          {filteredMetrics.map((metric, index) => (
            <div
              key={index}
              className={`cursor-pointer transition-all hover:shadow-md border rounded-lg p-4 ${
                selectedMetric === metric.name ? 'ring-2 ring-blue-500' : ''
              }`}
              onClick={() =>
                setSelectedMetric(
                  selectedMetric === metric.name ? null : metric.name
                )
              }
              role="button"
              tabIndex={0}
              aria-pressed={selectedMetric === metric.name}
              onKeyDown={(e: React.KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  setSelectedMetric(
                    selectedMetric === metric.name ? null : metric.name
                  )
                }
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-sm">{metric.name}</h3>
                {getTrendIcon(metric.trend)}
              </div>

              <div className="space-y-1">
                <div className="text-2xl font-bold text-gray-900">
                  {formatNumber(metric.current)}
                </div>
                <div className="text-xs text-gray-500">
                  vs {formatNumber(metric.previous)} last period
                </div>
                <div className="text-xs text-gray-600">
                  {metric.description}
                </div>
              </div>

              <div className="mt-2 pt-2 border-t">
                <span
                  className={`text-xs px-2 py-1 rounded-full ${
                    metric.category === 'engagement'
                      ? 'bg-blue-100 text-blue-700'
                      : metric.category === 'performance'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-purple-100 text-purple-700'
                  }`}
                >
                  {metric.category}
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Chart/Table Display */}
        <div className="space-y-4">
          {selectedMetric && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Target className="w-4 h-4" />
              Showing data for:{' '}
              <span className="font-medium">{selectedMetric}</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setSelectedMetric(null)}
                className="ml-2"
              >
                Clear
              </Button>
            </div>
          )}

          {renderChart()}
        </div>

        {/* Role-specific insights */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-medium mb-2 flex items-center gap-2">
            <Award className="w-4 h-4" />
            {role === 'parent'
              ? 'Student Progress Insights'
              : role === 'teacher'
                ? 'Classroom Analytics'
                : 'District Overview'}
          </h4>
          <p className="text-sm text-gray-600">
            {role === 'parent'
              ? "Track your child's learning engagement and session completion rates to identify learning patterns."
              : role === 'teacher'
                ? 'Monitor student activity across your classes to optimize instruction and identify students who need support.'
                : 'View district-wide usage patterns to inform policy decisions and resource allocation.'}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export default UsageChart
