import React, { useState } from 'react'
import { useTeacherAnalytics } from '../../api/analyticsClient'
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
import { Avatar, AvatarImage, AvatarFallback } from '../../components/ui/Avatar'
import {
  Users,
  Trophy,
  Target,
  Settings,
  Download,
  RefreshCw,
  UserCheck,
  AlertTriangle,
  CheckCircle,
  BarChart3,
} from '../../components/ui/Icons'

export interface ClassroomData {
  id: string
  name: string
  grade: string
  studentCount: number
  averageProgress: number
  activeStudents: number
  completionRate: number
  needsAttention: Array<{
    studentId: string
    studentName: string
    issue: string
    severity: 'low' | 'medium' | 'high'
  }>
}

export interface StudentSummary {
  id: string
  name: string
  avatar?: string
  progress: number
  lastActive: string
  strugglingSubjects: string[]
  achievements: number
  status: 'on-track' | 'needs-help' | 'excelling'
}

const TeacherDashboard: React.FC = () => {
  const [selectedClass, setSelectedClass] = useState<string>('')
  const [refreshing, setRefreshing] = useState(false)
  const [viewMode, setViewMode] = useState<'overview' | 'detailed'>('overview')

  const {
    data: analyticsData,
    isLoading,
    error,
    refetch,
  } = useTeacherAnalytics()

  // Mock classroom data (in real app, this would come from the API)
  const classrooms: ClassroomData[] = [
    {
      id: '1',
      name: 'Math 5A',
      grade: '5th Grade',
      studentCount: 24,
      averageProgress: 78,
      activeStudents: 22,
      completionRate: 85,
      needsAttention: [
        {
          studentId: '1',
          studentName: 'Sarah M.',
          issue: 'Missing assignments',
          severity: 'medium',
        },
        {
          studentId: '2',
          studentName: 'James K.',
          issue: 'Low engagement',
          severity: 'high',
        },
      ],
    },
    {
      id: '2',
      name: 'Reading 5B',
      grade: '5th Grade',
      studentCount: 26,
      averageProgress: 82,
      activeStudents: 25,
      completionRate: 91,
      needsAttention: [
        {
          studentId: '3',
          studentName: 'Emma R.',
          issue: 'Difficulty with comprehension',
          severity: 'medium',
        },
      ],
    },
  ]

  const students: StudentSummary[] = [
    {
      id: '1',
      name: 'Sarah Mitchell',
      progress: 65,
      lastActive: '2025-08-16',
      strugglingSubjects: ['Math', 'Science'],
      achievements: 3,
      status: 'needs-help',
    },
    {
      id: '2',
      name: 'James Kim',
      progress: 45,
      lastActive: '2025-08-14',
      strugglingSubjects: ['Math', 'Reading'],
      achievements: 1,
      status: 'needs-help',
    },
    {
      id: '3',
      name: 'Emma Rodriguez',
      progress: 88,
      lastActive: '2025-08-17',
      strugglingSubjects: [],
      achievements: 8,
      status: 'excelling',
    },
    {
      id: '4',
      name: 'Alex Chen',
      progress: 76,
      lastActive: '2025-08-17',
      strugglingSubjects: ['Social Studies'],
      achievements: 5,
      status: 'on-track',
    },
  ]

  const currentClass =
    classrooms.find(c => c.id === selectedClass) || classrooms[0]

  const handleRefresh = async () => {
    setRefreshing(true)
    await refetch()
    setTimeout(() => setRefreshing(false), 1000)
  }

  const getStatusColor = (status: StudentSummary['status']) => {
    switch (status) {
      case 'excelling':
        return 'bg-green-100 text-green-700 border-green-200'
      case 'on-track':
        return 'bg-blue-100 text-blue-700 border-blue-200'
      case 'needs-help':
        return 'bg-red-100 text-red-700 border-red-200'
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  const getStatusIcon = (status: StudentSummary['status']) => {
    switch (status) {
      case 'excelling':
        return <Trophy className="w-4 h-4" />
      case 'on-track':
        return <CheckCircle className="w-4 h-4" />
      case 'needs-help':
        return <AlertTriangle className="w-4 h-4" />
      default:
        return <UserCheck className="w-4 h-4" />
    }
  }

  const getSeverityColor = (severity: 'low' | 'medium' | 'high') => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-700'
      case 'medium':
        return 'bg-yellow-100 text-yellow-700'
      case 'low':
        return 'bg-blue-100 text-blue-700'
    }
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
            Teacher Dashboard
          </h1>
          <p className="text-gray-600 mt-1">
            Manage your classrooms and track student progress
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Class Selector */}
          <select
            value={selectedClass || classrooms[0]?.id}
            onChange={e => setSelectedClass(e.target.value)}
            className="px-3 py-2 border rounded-lg bg-white"
            aria-label="Select classroom"
          >
            {classrooms.map(classroom => (
              <option key={classroom.id} value={classroom.id}>
                {classroom.name}
              </option>
            ))}
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

      {/* Classroom Overview Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold">{currentClass.name}</h2>
              <p className="text-gray-600">{currentClass.grade}</p>
            </div>

            <div className="grid grid-cols-4 gap-6 text-center">
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {currentClass.studentCount}
                </div>
                <div className="text-sm text-gray-500">Total Students</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {currentClass.activeStudents}
                </div>
                <div className="text-sm text-gray-500">Active Today</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-purple-600">
                  {currentClass.averageProgress}%
                </div>
                <div className="text-sm text-gray-500">Avg Progress</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-orange-600">
                  {currentClass.completionRate}%
                </div>
                <div className="text-sm text-gray-500">Completion Rate</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Attention Required */}
      {currentClass.needsAttention.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              Students Needing Attention ({currentClass.needsAttention.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {currentClass.needsAttention.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-orange-50 border border-orange-200 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <Avatar className="w-8 h-8">
                      <AvatarFallback className="text-sm">
                        {item.studentName
                          .split(' ')
                          .map(n => n[0])
                          .join('')}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <div className="font-medium">{item.studentName}</div>
                      <div className="text-sm text-gray-600">{item.issue}</div>
                    </div>
                  </div>
                  <div
                    className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(item.severity)}`}
                  >
                    {item.severity}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content Tabs */}
      <Tabs defaultValue="students" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="students">Students</TabsTrigger>
          <TabsTrigger value="progress">Progress</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="students" className="space-y-6">
          {viewMode === 'overview' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {students.map(student => (
                <Card key={student.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3 mb-3">
                      <Avatar className="w-10 h-10">
                        <AvatarImage src={student.avatar} alt={student.name} />
                        <AvatarFallback>
                          {student.name
                            .split(' ')
                            .map(n => n[0])
                            .join('')}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className="font-medium">{student.name}</div>
                        <div className="text-sm text-gray-500">
                          Last active: {student.lastActive}
                        </div>
                      </div>
                      <div
                        className={`px-2 py-1 rounded-full text-xs border flex items-center gap-1 ${getStatusColor(student.status)}`}
                      >
                        {getStatusIcon(student.status)}
                        {student.status.replace('-', ' ')}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Progress</span>
                        <span>{student.progress}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${student.progress}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex justify-between items-center mt-3 pt-3 border-t">
                      <div className="flex items-center gap-1 text-sm text-gray-600">
                        <Trophy className="w-4 h-4" />
                        {student.achievements} achievements
                      </div>
                      {student.strugglingSubjects.length > 0 && (
                        <div className="text-xs text-orange-600">
                          Needs help: {student.strugglingSubjects.join(', ')}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Detailed Student View</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-2">Student</th>
                        <th className="text-left p-2">Progress</th>
                        <th className="text-left p-2">Status</th>
                        <th className="text-left p-2">Last Active</th>
                        <th className="text-left p-2">Achievements</th>
                        <th className="text-left p-2">Struggling With</th>
                        <th className="text-left p-2">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {students.map(student => (
                        <tr
                          key={student.id}
                          className="border-b hover:bg-gray-50"
                        >
                          <td className="p-2">
                            <div className="flex items-center gap-2">
                              <Avatar className="w-8 h-8">
                                <AvatarImage
                                  src={student.avatar}
                                  alt={student.name}
                                />
                                <AvatarFallback className="text-xs">
                                  {student.name
                                    .split(' ')
                                    .map(n => n[0])
                                    .join('')}
                                </AvatarFallback>
                              </Avatar>
                              {student.name}
                            </div>
                          </td>
                          <td className="p-2">
                            <div className="flex items-center gap-2">
                              <div className="w-16 bg-gray-200 rounded-full h-2">
                                <div
                                  className="bg-blue-600 h-2 rounded-full"
                                  style={{ width: `${student.progress}%` }}
                                />
                              </div>
                              <span className="text-sm">
                                {student.progress}%
                              </span>
                            </div>
                          </td>
                          <td className="p-2">
                            <div
                              className={`px-2 py-1 rounded-full text-xs border inline-flex items-center gap-1 ${getStatusColor(student.status)}`}
                            >
                              {getStatusIcon(student.status)}
                              {student.status.replace('-', ' ')}
                            </div>
                          </td>
                          <td className="p-2 text-sm">{student.lastActive}</td>
                          <td className="p-2 text-sm">
                            {student.achievements}
                          </td>
                          <td className="p-2 text-sm">
                            {student.strugglingSubjects.length > 0
                              ? student.strugglingSubjects.join(', ')
                              : 'None'}
                          </td>
                          <td className="p-2">
                            <Button size="sm" variant="outline">
                              View Details
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="progress" className="space-y-6">
          {analyticsData && (
            <ProgressChart
              data={analyticsData.progressData}
              subjects={analyticsData.subjects}
              role="teacher"
            />
          )}
        </TabsContent>

        <TabsContent value="activity" className="space-y-6">
          {analyticsData && (
            <UsageChart
              data={analyticsData.usageData}
              metrics={analyticsData.usageMetrics}
              role="teacher"
            />
          )}
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          {analyticsData && (
            <AlertsChart alerts={analyticsData.alerts} role="teacher" />
          )}

          {/* Quick Action Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <BarChart3 className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <div className="font-medium">Generate Report</div>
                    <div className="text-sm text-gray-500">
                      Class performance summary
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Users className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <div className="font-medium">Parent Updates</div>
                    <div className="text-sm text-gray-500">
                      Send progress notifications
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-100 rounded-lg">
                    <Target className="w-5 h-5 text-purple-600" />
                  </div>
                  <div>
                    <div className="font-medium">Set Goals</div>
                    <div className="text-sm text-gray-500">
                      Create learning objectives
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

export default TeacherDashboard
