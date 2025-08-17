import React, { useState } from 'react'
import { useDistrictAnalytics } from '../../api/analyticsClient'
import ProgressChart from '../../components/charts/ProgressChart'
import UsageChart from '../../components/charts/UsageChart'
import AlertsChart from '../../components/charts/AlertsChart'
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from '../../components/ui/Tabs'
import {
  Users,
  School,
  TrendingUp,
  Target,
  Award,
  BarChart3,
  Download,
  RefreshCw,
  Settings,
  AlertTriangle,
  CheckCircle,
  Clock,
  DollarSign,
  BookOpen,
  UserCheck,
} from '../../components/ui/Icons'

export interface SchoolData {
  id: string
  name: string
  address: string
  principalName: string
  studentCount: number
  teacherCount: number
  averageProgress: number
  engagementRate: number
  completionRate: number
  budgetUtilization: number
  lastUpdated: string
  status: 'excellent' | 'good' | 'needs-improvement' | 'critical'
  alerts: number
}

export interface DistrictMetrics {
  totalStudents: number
  totalTeachers: number
  totalSchools: number
  districtProgress: number
  budgetAllocated: number
  budgetUtilized: number
  activePrograms: number
  monthlyGrowth: number
}

const DistrictDashboard: React.FC = () => {
  const [refreshing, setRefreshing] = useState(false)
  const [timeRange, setTimeRange] = useState<
    'week' | 'month' | 'quarter' | 'year'
  >('month')
  const [viewMode, setViewMode] = useState<'schools' | 'metrics' | 'budget'>(
    'schools'
  )

  const {
    data: analyticsData,
    isLoading,
    error,
    refetch,
  } = useDistrictAnalytics()

  // Mock district data (in real app, this would come from the API)
  const districtMetrics: DistrictMetrics = {
    totalStudents: 12847,
    totalTeachers: 756,
    totalSchools: 32,
    districtProgress: 81,
    budgetAllocated: 2500000,
    budgetUtilized: 1875000,
    activePrograms: 18,
    monthlyGrowth: 3.2,
  }

  const schools: SchoolData[] = [
    {
      id: '1',
      name: 'Lincoln Elementary',
      address: '123 Oak Street',
      principalName: 'Dr. Sarah Johnson',
      studentCount: 485,
      teacherCount: 28,
      averageProgress: 87,
      engagementRate: 92,
      completionRate: 89,
      budgetUtilization: 78,
      lastUpdated: '2025-08-17',
      status: 'excellent',
      alerts: 0,
    },
    {
      id: '2',
      name: 'Washington Middle School',
      address: '456 Pine Avenue',
      principalName: 'Mr. Michael Chen',
      studentCount: 672,
      teacherCount: 35,
      averageProgress: 75,
      engagementRate: 82,
      completionRate: 76,
      budgetUtilization: 85,
      lastUpdated: '2025-08-17',
      status: 'good',
      alerts: 2,
    },
    {
      id: '3',
      name: 'Roosevelt High School',
      address: '789 Maple Drive',
      principalName: 'Ms. Emily Rodriguez',
      studentCount: 1234,
      teacherCount: 68,
      averageProgress: 68,
      engagementRate: 71,
      completionRate: 65,
      budgetUtilization: 92,
      lastUpdated: '2025-08-16',
      status: 'needs-improvement',
      alerts: 5,
    },
    {
      id: '4',
      name: 'Jefferson Elementary',
      address: '321 Elm Street',
      principalName: 'Dr. Robert Kim',
      studentCount: 398,
      teacherCount: 22,
      averageProgress: 52,
      engagementRate: 58,
      completionRate: 48,
      budgetUtilization: 67,
      lastUpdated: '2025-08-15',
      status: 'critical',
      alerts: 8,
    },
  ]

  const handleRefresh = async () => {
    setRefreshing(true)
    await refetch()
    setTimeout(() => setRefreshing(false), 1000)
  }

  const getStatusColor = (status: SchoolData['status']) => {
    switch (status) {
      case 'excellent':
        return 'bg-green-100 text-green-700 border-green-200'
      case 'good':
        return 'bg-blue-100 text-blue-700 border-blue-200'
      case 'needs-improvement':
        return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      case 'critical':
        return 'bg-red-100 text-red-700 border-red-200'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  const getStatusIcon = (status: SchoolData['status']) => {
    switch (status) {
      case 'excellent':
        return <Award className="w-4 h-4" />
      case 'good':
        return <CheckCircle className="w-4 h-4" />
      case 'needs-improvement':
        return <Clock className="w-4 h-4" />
      case 'critical':
        return <AlertTriangle className="w-4 h-4" />
      default:
        return <School className="w-4 h-4" />
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('en-US').format(num)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Loading dashboard...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-red-600 mb-4">Error loading dashboard data</div>
        <Button onClick={handleRefresh} variant="outline">
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            District Dashboard
          </h1>
          <p className="text-gray-600 mt-1">
            Comprehensive overview of district performance
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Time Range Filter */}
          <select
            value={timeRange}
            onChange={e => setTimeRange(e.target.value as any)}
            className="px-3 py-2 border rounded-lg bg-white"
            aria-label="Select time range"
          >
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
          </select>

          {/* View Mode */}
          <div className="flex rounded-lg border">
            <Button
              size="sm"
              variant={viewMode === 'schools' ? 'primary' : 'ghost'}
              onClick={() => setViewMode('schools')}
              className="rounded-none rounded-l-lg"
            >
              Schools
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'metrics' ? 'primary' : 'ghost'}
              onClick={() => setViewMode('metrics')}
              className="rounded-none"
            >
              Metrics
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'budget' ? 'primary' : 'ghost'}
              onClick={() => setViewMode('budget')}
              className="rounded-none rounded-r-lg"
            >
              Budget
            </Button>
          </div>

          <Button
            onClick={handleRefresh}
            variant="outline"
            size="sm"
            disabled={refreshing}
          >
            <RefreshCw
              className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`}
            />
            Refresh
          </Button>

          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>

          <Button variant="outline" size="sm">
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* District Overview Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <div className="text-sm text-gray-500">Total Students</div>
                <div className="text-2xl font-bold">
                  {formatNumber(districtMetrics.totalStudents)}
                </div>
                <div className="flex items-center gap-1 text-sm text-green-600">
                  <TrendingUp className="w-3 h-3" />+
                  {districtMetrics.monthlyGrowth}% this month
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <UserCheck className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <div className="text-sm text-gray-500">Total Teachers</div>
                <div className="text-2xl font-bold">
                  {formatNumber(districtMetrics.totalTeachers)}
                </div>
                <div className="text-sm text-gray-600">
                  Across {districtMetrics.totalSchools} schools
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded-lg">
                <Target className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <div className="text-sm text-gray-500">District Progress</div>
                <div className="text-2xl font-bold">
                  {districtMetrics.districtProgress}%
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                  <div
                    className="bg-purple-600 h-2 rounded-full transition-all duration-300"
                    style={{ width: `${districtMetrics.districtProgress}%` }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <DollarSign className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <div className="text-sm text-gray-500">Budget Utilization</div>
                <div className="text-2xl font-bold">
                  {Math.round(
                    (districtMetrics.budgetUtilized /
                      districtMetrics.budgetAllocated) *
                      100
                  )}
                  %
                </div>
                <div className="text-sm text-gray-600">
                  {formatCurrency(districtMetrics.budgetUtilized)} /{' '}
                  {formatCurrency(districtMetrics.budgetAllocated)}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Critical Alerts */}
      {schools.some(school => school.alerts > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              Schools Requiring Attention
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {schools
                .filter(school => school.alerts > 0)
                .map(school => (
                  <div
                    key={school.id}
                    className="p-3 bg-red-50 border border-red-200 rounded-lg"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium">{school.name}</div>
                      <div className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs">
                        {school.alerts} alerts
                      </div>
                    </div>
                    <div className="text-sm text-gray-600">
                      Progress: {school.averageProgress}% | Engagement:{' '}
                      {school.engagementRate}%
                    </div>
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="schools">Schools</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {viewMode === 'schools' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {schools.map(school => (
                <Card
                  key={school.id}
                  className="hover:shadow-md transition-shadow"
                >
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold text-lg">{school.name}</h3>
                        <p className="text-sm text-gray-600">
                          {school.address}
                        </p>
                        <p className="text-sm text-gray-600">
                          Principal: {school.principalName}
                        </p>
                      </div>
                      <div
                        className={`px-2 py-1 rounded-full text-xs border flex items-center gap-1 ${getStatusColor(school.status)}`}
                      >
                        {getStatusIcon(school.status)}
                        {school.status.replace('-', ' ')}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mb-3">
                      <div>
                        <div className="text-sm text-gray-500">Students</div>
                        <div className="font-semibold">
                          {formatNumber(school.studentCount)}
                        </div>
                      </div>
                      <div>
                        <div className="text-sm text-gray-500">Teachers</div>
                        <div className="font-semibold">
                          {school.teacherCount}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-sm">
                        <span>Progress</span>
                        <span>{school.averageProgress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${school.averageProgress}%` }}
                        />
                      </div>

                      <div className="flex justify-between items-center text-sm">
                        <span>Engagement</span>
                        <span>{school.engagementRate}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-green-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${school.engagementRate}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex justify-between items-center mt-3 pt-3 border-t">
                      <div className="text-xs text-gray-500">
                        Updated: {school.lastUpdated}
                      </div>
                      <Button size="sm" variant="outline">
                        View Details
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {viewMode === 'metrics' && analyticsData && (
            <div className="space-y-6">
              <ProgressChart
                data={analyticsData.progressData}
                subjects={analyticsData.subjects}
                role="district"
              />
              <UsageChart
                data={analyticsData.usageData}
                metrics={analyticsData.usageMetrics}
                role="district"
              />
            </div>
          )}

          {viewMode === 'budget' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Budget Allocation by School</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {schools.map(school => (
                      <div key={school.id}>
                        <div className="flex justify-between items-center text-sm">
                          <span>{school.name}</span>
                          <span>{school.budgetUtilization}%</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full transition-all duration-300 ${
                              school.budgetUtilization > 90
                                ? 'bg-red-600'
                                : school.budgetUtilization > 75
                                  ? 'bg-yellow-600'
                                  : 'bg-green-600'
                            }`}
                            style={{ width: `${school.budgetUtilization}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Program Funding</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span>STEM Programs</span>
                      <span className="font-semibold">
                        {formatCurrency(350000)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Reading Initiatives</span>
                      <span className="font-semibold">
                        {formatCurrency(280000)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Technology</span>
                      <span className="font-semibold">
                        {formatCurrency(450000)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Special Education</span>
                      <span className="font-semibold">
                        {formatCurrency(320000)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Arts & Music</span>
                      <span className="font-semibold">
                        {formatCurrency(180000)}
                      </span>
                    </div>
                    <div className="border-t pt-2 flex justify-between font-semibold">
                      <span>Total Allocated</span>
                      <span>{formatCurrency(1580000)}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        <TabsContent value="schools" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>School Performance Comparison</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">School</th>
                      <th className="text-left p-2">Students</th>
                      <th className="text-left p-2">Teachers</th>
                      <th className="text-left p-2">Progress</th>
                      <th className="text-left p-2">Engagement</th>
                      <th className="text-left p-2">Completion</th>
                      <th className="text-left p-2">Budget</th>
                      <th className="text-left p-2">Status</th>
                      <th className="text-left p-2">Alerts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schools.map(school => (
                      <tr key={school.id} className="border-b hover:bg-gray-50">
                        <td className="p-2 font-medium">{school.name}</td>
                        <td className="p-2">
                          {formatNumber(school.studentCount)}
                        </td>
                        <td className="p-2">{school.teacherCount}</td>
                        <td className="p-2">{school.averageProgress}%</td>
                        <td className="p-2">{school.engagementRate}%</td>
                        <td className="p-2">{school.completionRate}%</td>
                        <td className="p-2">{school.budgetUtilization}%</td>
                        <td className="p-2">
                          <div
                            className={`px-2 py-1 rounded-full text-xs border inline-flex items-center gap-1 ${getStatusColor(school.status)}`}
                          >
                            {getStatusIcon(school.status)}
                            {school.status.replace('-', ' ')}
                          </div>
                        </td>
                        <td className="p-2">
                          {school.alerts > 0 ? (
                            <span className="bg-red-100 text-red-700 px-2 py-1 rounded-full text-xs">
                              {school.alerts}
                            </span>
                          ) : (
                            <span className="text-gray-400">None</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          {analyticsData && (
            <>
              <UsageChart
                data={analyticsData.usageData}
                metrics={analyticsData.usageMetrics}
                role="district"
              />
              <AlertsChart alerts={analyticsData.alerts} role="district" />
            </>
          )}
        </TabsContent>

        <TabsContent value="reports" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <BarChart3 className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <div className="font-medium">
                      District Performance Report
                    </div>
                    <div className="text-sm text-gray-500">
                      Comprehensive analysis
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <DollarSign className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <div className="font-medium">Budget Analysis</div>
                    <div className="text-sm text-gray-500">
                      Financial overview
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <Users className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <div className="font-medium">Enrollment Report</div>
                    <div className="text-sm text-gray-500">
                      Student demographics
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-orange-100 rounded-lg">
                    <BookOpen className="w-5 h-5 text-orange-600" />
                  </div>
                  <div>
                    <div className="font-medium">Curriculum Analysis</div>
                    <div className="text-sm text-gray-500">
                      Program effectiveness
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-100 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-red-600" />
                  </div>
                  <div>
                    <div className="font-medium">Risk Assessment</div>
                    <div className="text-sm text-gray-500">
                      Identify concerns
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-yellow-100 rounded-lg">
                    <Target className="w-5 h-5 text-yellow-600" />
                  </div>
                  <div>
                    <div className="font-medium">Goal Tracking</div>
                    <div className="text-sm text-gray-500">
                      Progress monitoring
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default DistrictDashboard
