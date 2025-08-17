import React, { useState, useMemo } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Button } from '../ui/Button'
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  Download,
  Target,
  AlertCircle,
} from '../ui/Icons'

export interface Alert {
  id: string
  title: string
  description: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  category: 'academic' | 'behavior' | 'attendance' | 'technical' | 'safety'
  studentId?: string
  studentName?: string
  classId?: string
  className?: string
  schoolId?: string
  schoolName?: string
  date: string
  status: 'active' | 'acknowledged' | 'resolved'
  assignedTo?: string
  dueDate?: string
}

export interface AlertsChartProps {
  alerts: Alert[]
  role: 'parent' | 'teacher' | 'district'
  className?: string
}

const SEVERITY_COLORS = {
  low: '#3B82F6', // Blue
  medium: '#F59E0B', // Yellow
  high: '#EF4444', // Red
  critical: '#DC2626', // Dark Red
}

const STATUS_COLORS = {
  active: '#EF4444', // Red
  acknowledged: '#F59E0B', // Yellow
  resolved: '#10B981', // Green
}

export const AlertsChart: React.FC<AlertsChartProps> = ({
  alerts,
  role,
  className = '',
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [selectedSeverity, setSelectedSeverity] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'overview' | 'detailed'>('overview')
  const [sortBy, setSortBy] = useState<'date' | 'severity' | 'category'>('date')

  // Filter alerts based on selections
  const filteredAlerts = useMemo(() => {
    let filtered = alerts

    if (selectedCategory) {
      filtered = filtered.filter(alert => alert.category === selectedCategory)
    }

    if (selectedSeverity) {
      filtered = filtered.filter(alert => alert.severity === selectedSeverity)
    }

    return filtered.sort((a, b) => {
      switch (sortBy) {
        case 'severity':
          const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 }
          return severityOrder[b.severity] - severityOrder[a.severity]
        case 'category':
          return a.category.localeCompare(b.category)
        default: // date
          return new Date(b.date).getTime() - new Date(a.date).getTime()
      }
    })
  }, [alerts, selectedCategory, selectedSeverity, sortBy])

  // Aggregate data for charts
  const severityData = useMemo(() => {
    const counts = alerts.reduce(
      (acc, alert) => {
        acc[alert.severity] = (acc[alert.severity] || 0) + 1
        return acc
      },
      {} as Record<string, number>
    )

    return Object.entries(counts).map(([severity, count]) => ({
      name: severity.charAt(0).toUpperCase() + severity.slice(1),
      value: count,
      color: SEVERITY_COLORS[severity as keyof typeof SEVERITY_COLORS],
    }))
  }, [alerts])

  const categoryData = useMemo(() => {
    const counts = alerts.reduce(
      (acc, alert) => {
        acc[alert.category] = (acc[alert.category] || 0) + 1
        return acc
      },
      {} as Record<string, number>
    )

    return Object.entries(counts).map(([category, count]) => ({
      category: category.charAt(0).toUpperCase() + category.slice(1),
      count,
      active: alerts.filter(
        a => a.category === category && a.status === 'active'
      ).length,
      resolved: alerts.filter(
        a => a.category === category && a.status === 'resolved'
      ).length,
    }))
  }, [alerts])

  const statusData = useMemo(() => {
    const counts = alerts.reduce(
      (acc, alert) => {
        acc[alert.status] = (acc[alert.status] || 0) + 1
        return acc
      },
      {} as Record<string, number>
    )

    return Object.entries(counts).map(([status, count]) => ({
      name: status.charAt(0).toUpperCase() + status.slice(1),
      value: count,
      color: STATUS_COLORS[status as keyof typeof STATUS_COLORS],
    }))
  }, [alerts])

  console.log('Status data for potential future use:', statusData)

  // Export functionality
  const handleExport = () => {
    const csvContent = [
      [
        'ID',
        'Title',
        'Severity',
        'Category',
        'Status',
        'Date',
        'Student',
        'Class',
        'School',
      ],
      ...filteredAlerts.map(alert => [
        alert.id,
        alert.title,
        alert.severity,
        alert.category,
        alert.status,
        alert.date,
        alert.studentName || '',
        alert.className || '',
        alert.schoolName || '',
      ]),
    ]

    const csvString = csvContent.map(row => row.join(',')).join('\n')
    const blob = new Blob([csvString], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `alerts-${role}-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  }

  // Get severity icon and color
  const getSeverityIcon = (severity: Alert['severity']) => {
    switch (severity) {
      case 'critical':
        return <AlertTriangle className="w-4 h-4 text-red-600" />
      case 'high':
        return <AlertTriangle className="w-4 h-4 text-red-500" />
      case 'medium':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />
      case 'low':
        return <AlertCircle className="w-4 h-4 text-blue-500" />
    }
  }

  const getStatusIcon = (status: Alert['status']) => {
    switch (status) {
      case 'resolved':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'acknowledged':
        return <Clock className="w-4 h-4 text-yellow-500" />
      case 'active':
        return <AlertTriangle className="w-4 h-4 text-red-500" />
    }
  }

  const getSeverityColor = (severity: Alert['severity']) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-700 border-red-200'
      case 'high':
        return 'bg-red-50 text-red-600 border-red-200'
      case 'medium':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      case 'low':
        return 'bg-blue-100 text-blue-700 border-blue-200'
    }
  }

  // Custom tooltip for pie charts
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div className="bg-white p-3 border rounded-lg shadow-lg">
          <p className="font-semibold">{data.name}</p>
          <p style={{ color: data.payload.color }}>Count: {data.value}</p>
        </div>
      )
    }
    return null
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            Alerts & Notifications -{' '}
            {role.charAt(0).toUpperCase() + role.slice(1)}
          </CardTitle>

          <div className="flex flex-wrap gap-2">
            {/* Category Filter */}
            <select
              value={selectedCategory || ''}
              onChange={e => setSelectedCategory(e.target.value || null)}
              className="px-3 py-1 border rounded-lg text-sm"
              aria-label="Filter by category"
            >
              <option value="">All Categories</option>
              <option value="academic">Academic</option>
              <option value="behavior">Behavior</option>
              <option value="attendance">Attendance</option>
              <option value="technical">Technical</option>
              <option value="safety">Safety</option>
            </select>

            {/* Severity Filter */}
            <select
              value={selectedSeverity || ''}
              onChange={e => setSelectedSeverity(e.target.value || null)}
              className="px-3 py-1 border rounded-lg text-sm"
              aria-label="Filter by severity"
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            {/* Sort By */}
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
              className="px-3 py-1 border rounded-lg text-sm"
              aria-label="Sort by"
            >
              <option value="date">Sort by Date</option>
              <option value="severity">Sort by Severity</option>
              <option value="category">Sort by Category</option>
            </select>

            {/* View Mode Toggle */}
            <div className="flex rounded-lg border">
              <Button
                size="sm"
                variant={viewMode === 'overview' ? 'primary' : 'ghost'}
                onClick={() => setViewMode('overview')}
                className="rounded-none rounded-l-lg"
              >
                Overview
              </Button>
              <Button
                size="sm"
                variant={viewMode === 'detailed' ? 'primary' : 'ghost'}
                onClick={() => setViewMode('detailed')}
                className="rounded-none rounded-r-lg"
              >
                Detailed
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
        {viewMode === 'overview' ? (
          <div className="space-y-6">
            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-red-50 rounded-lg">
                <div className="text-2xl font-bold text-red-600">
                  {alerts.filter(a => a.status === 'active').length}
                </div>
                <div className="text-sm text-red-600">Active Alerts</div>
              </div>
              <div className="text-center p-4 bg-yellow-50 rounded-lg">
                <div className="text-2xl font-bold text-yellow-600">
                  {alerts.filter(a => a.status === 'acknowledged').length}
                </div>
                <div className="text-sm text-yellow-600">Acknowledged</div>
              </div>
              <div className="text-center p-4 bg-green-50 rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {alerts.filter(a => a.status === 'resolved').length}
                </div>
                <div className="text-sm text-green-600">Resolved</div>
              </div>
              <div className="text-center p-4 bg-blue-50 rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {alerts.length}
                </div>
                <div className="text-sm text-blue-600">Total Alerts</div>
              </div>
            </div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Severity Distribution */}
              <div>
                <h4 className="font-medium mb-4">Alerts by Severity</h4>
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={severityData}
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      dataKey="value"
                    >
                      {severityData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Category Breakdown */}
              <div>
                <h4 className="font-medium mb-4">Alerts by Category</h4>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={categoryData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="category" />
                    <YAxis />
                    <Tooltip />
                    <Bar
                      dataKey="active"
                      stackId="a"
                      fill="#EF4444"
                      name="Active"
                    />
                    <Bar
                      dataKey="resolved"
                      stackId="a"
                      fill="#10B981"
                      name="Resolved"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Recent High Priority Alerts */}
            <div>
              <h4 className="font-medium mb-4">High Priority Alerts</h4>
              <div className="space-y-2">
                {filteredAlerts
                  .filter(
                    alert =>
                      alert.severity === 'critical' || alert.severity === 'high'
                  )
                  .slice(0, 5)
                  .map(alert => (
                    <div
                      key={alert.id}
                      className="p-3 border rounded-lg hover:bg-gray-50"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          {getSeverityIcon(alert.severity)}
                          <div>
                            <div className="font-medium">{alert.title}</div>
                            <div className="text-sm text-gray-600">
                              {alert.description}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {alert.studentName &&
                                `Student: ${alert.studentName} | `}
                              {alert.className &&
                                `Class: ${alert.className} | `}
                              {alert.date}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <div
                            className={`px-2 py-1 rounded-full text-xs border ${getSeverityColor(alert.severity)}`}
                          >
                            {alert.severity}
                          </div>
                          {getStatusIcon(alert.status)}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          </div>
        ) : (
          /* Detailed View */
          <div className="space-y-4">
            <div className="text-sm text-gray-600">
              Showing {filteredAlerts.length} of {alerts.length} alerts
            </div>

            <div className="space-y-3">
              {filteredAlerts.map(alert => (
                <div
                  key={alert.id}
                  className="p-4 border rounded-lg hover:bg-gray-50"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-start gap-3">
                      {getSeverityIcon(alert.severity)}
                      <div>
                        <div className="font-medium">{alert.title}</div>
                        <div className="text-sm text-gray-600">
                          {alert.description}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div
                        className={`px-2 py-1 rounded-full text-xs border ${getSeverityColor(alert.severity)}`}
                      >
                        {alert.severity}
                      </div>
                      {getStatusIcon(alert.status)}
                    </div>
                  </div>

                  <div className="text-xs text-gray-500 space-y-1">
                    <div>Category: {alert.category}</div>
                    <div>Date: {alert.date}</div>
                    {alert.studentName && (
                      <div>Student: {alert.studentName}</div>
                    )}
                    {alert.className && <div>Class: {alert.className}</div>}
                    {alert.schoolName && <div>School: {alert.schoolName}</div>}
                    {alert.assignedTo && (
                      <div>Assigned to: {alert.assignedTo}</div>
                    )}
                    {alert.dueDate && <div>Due: {alert.dueDate}</div>}
                  </div>

                  <div className="mt-3 flex gap-2">
                    {alert.status === 'active' && (
                      <Button size="sm" variant="outline">
                        Acknowledge
                      </Button>
                    )}
                    {alert.status !== 'resolved' && (
                      <Button size="sm" variant="outline">
                        Resolve
                      </Button>
                    )}
                    <Button size="sm" variant="ghost">
                      View Details
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Role-specific guidance */}
        <div className="mt-6 p-4 bg-gray-50 rounded-lg">
          <h4 className="font-medium mb-2 flex items-center gap-2">
            <Target className="w-4 h-4" />
            {role === 'parent'
              ? 'Alert Guidelines'
              : role === 'teacher'
                ? 'Response Protocol'
                : 'Management Overview'}
          </h4>
          <p className="text-sm text-gray-600">
            {role === 'parent'
              ? "Stay informed about important updates regarding your child's education, safety, and wellbeing."
              : role === 'teacher'
                ? 'Monitor and respond to classroom alerts to ensure optimal learning environment and student safety.'
                : 'Track district-wide alerts to maintain oversight and coordinate appropriate responses across schools.'}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export default AlertsChart
