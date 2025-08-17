import React, { useState, useMemo } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Button } from '../ui/Button'
import { TrendingUp, BookOpen, Target, Download } from '../ui/Icons'

export interface ProgressData {
  date: string
  overall: number
  math: number
  reading: number
  science: number
  socialStudies: number
}

export interface Subject {
  name: string
  color: string
  target: number
  current: number
  trend: 'up' | 'down' | 'stable'
}

export interface ProgressChartProps {
  data: ProgressData[]
  subjects: Subject[]
  role: 'parent' | 'teacher' | 'district'
  className?: string
}

export const ProgressChart: React.FC<ProgressChartProps> = ({
  data,
  subjects,
  role,
  className = '',
}) => {
  const [selectedSubject, setSelectedSubject] = useState<string | null>(null)
  const [timeRange, setTimeRange] = useState<'week' | 'month' | 'quarter'>(
    'month'
  )
  const [viewMode, setViewMode] = useState<'trend' | 'comparison'>('trend')

  // Filter data based on time range
  const filteredData = useMemo(() => {
    const days = timeRange === 'week' ? 7 : timeRange === 'month' ? 30 : 90
    return data.slice(-days)
  }, [data, timeRange])

  // Get active subjects for display
  const activeSubjects = useMemo(() => {
    if (selectedSubject) {
      return subjects.filter(subject => subject.name === selectedSubject)
    }
    return subjects
  }, [subjects, selectedSubject])

  // Custom tooltip for the chart
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border rounded-lg shadow-lg">
          <p className="font-semibold">{`Date: ${label}`}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }}>
              {`${entry.dataKey}: ${entry.value}%`}
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
      ['Date', 'Overall', 'Math', 'Reading', 'Science', 'Social Studies'],
      ...filteredData.map(row => [
        row.date,
        row.overall,
        row.math,
        row.reading,
        row.science,
        row.socialStudies,
      ]),
    ]

    const csvString = csvContent.map(row => row.join(',')).join('\n')
    const blob = new Blob([csvString], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `progress-data-${role}-${timeRange}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  // Get trend icon
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

  const renderChart = () => {
    if (viewMode === 'comparison') {
      return (
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={filteredData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            {activeSubjects.map(subject => (
              <Bar
                key={subject.name}
                dataKey={subject.name.toLowerCase().replace(/\s+/g, '')}
                fill={subject.color}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      )
    }

    // Trend view (default)
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={filteredData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          {activeSubjects.map(subject => (
            <Line
              key={subject.name}
              type="monotone"
              dataKey={subject.name.toLowerCase().replace(/\s+/g, '')}
              stroke={subject.color}
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <CardTitle className="flex items-center gap-2">
            <BookOpen className="w-5 h-5" />
            Progress Tracking - {role.charAt(0).toUpperCase() + role.slice(1)}
          </CardTitle>

          <div className="flex flex-wrap gap-2">
            {/* Time Range Filter */}
            <div className="flex rounded-lg border">
              {(['week', 'month', 'quarter'] as const).map(range => (
                <Button
                  key={range}
                  size="sm"
                  variant={timeRange === range ? 'primary' : 'ghost'}
                  onClick={() => setTimeRange(range)}
                  className="rounded-none first:rounded-l-lg last:rounded-r-lg"
                >
                  {range.charAt(0).toUpperCase() + range.slice(1)}
                </Button>
              ))}
            </div>

            {/* View Mode Toggle */}
            <div className="flex rounded-lg border">
              <Button
                size="sm"
                variant={viewMode === 'trend' ? 'primary' : 'ghost'}
                onClick={() => setViewMode('trend')}
                className="rounded-none rounded-l-lg"
              >
                Trend
              </Button>
              <Button
                size="sm"
                variant={viewMode === 'comparison' ? 'primary' : 'ghost'}
                onClick={() => setViewMode('comparison')}
                className="rounded-none rounded-r-lg"
              >
                Compare
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
        {/* Subject Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {subjects.map((subject, index) => (
            <div
              key={index}
              className={`cursor-pointer transition-all hover:shadow-md border rounded-lg p-4 ${
                selectedSubject === subject.name ? 'ring-2 ring-blue-500' : ''
              }`}
              onClick={() =>
                setSelectedSubject(
                  selectedSubject === subject.name ? null : subject.name
                )
              }
              role="button"
              tabIndex={0}
              aria-pressed={selectedSubject === subject.name}
              onKeyDown={(e: React.KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  setSelectedSubject(
                    selectedSubject === subject.name ? null : subject.name
                  )
                }
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-sm">{subject.name}</h3>
                {getTrendIcon(subject.trend)}
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-500">Current</span>
                  <span
                    className="text-lg font-bold"
                    style={{ color: subject.color }}
                  >
                    {subject.current}%
                  </span>
                </div>

                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${subject.current}%`,
                      backgroundColor: subject.color,
                    }}
                  />
                </div>

                <div className="flex justify-between text-xs text-gray-500">
                  <span>Target: {subject.target}%</span>
                  <span>
                    {subject.current >= subject.target
                      ? '✓'
                      : `${subject.target - subject.current}% to go`}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Chart Display */}
        <div className="space-y-4">
          {selectedSubject && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Target className="w-4 h-4" />
              Showing data for:{' '}
              <span className="font-medium">{selectedSubject}</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setSelectedSubject(null)}
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
            <Target className="w-4 h-4" />
            {role === 'parent'
              ? 'Learning Insights'
              : role === 'teacher'
                ? 'Class Performance'
                : 'District Progress'}
          </h4>
          <p className="text-sm text-gray-600">
            {role === 'parent'
              ? "Track your child's academic progress across subjects and identify areas that may need additional support."
              : role === 'teacher'
                ? 'Monitor student progress to adjust instruction and provide targeted interventions where needed.'
                : 'Analyze district-wide academic performance to inform curriculum decisions and resource allocation.'}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export default ProgressChart
