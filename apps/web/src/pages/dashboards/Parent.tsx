import React, { useState } from 'react'
import { useParentAnalytics } from '../../api/analyticsClient'
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
  Trophy,
  Clock,
  Target,
  TrendingUp,
  BookOpen,
  Award,
  Activity,
  Settings,
  Download,
  RefreshCw,
} from '../../components/ui/Icons'

export interface StudentProgress {
  id: string
  name: string
  avatar?: string
  grade: string
  overallProgress: number
  subjectProgress: Array<{
    subject: string
    progress: number
    trend: 'up' | 'down' | 'stable'
  }>
  recentAchievements: Array<{
    title: string
    date: string
    icon: string
  }>
  weeklyGoals: Array<{
    goal: string
    progress: number
    target: number
  }>
}

const ParentDashboard: React.FC = () => {
  const [selectedChild, setSelectedChild] = useState<string>('')
  const [refreshing, setRefreshing] = useState(false)

  const {
    data: analyticsData,
    isLoading,
    error,
    refetch,
  } = useParentAnalytics()

  // Mock student data (in real app, this would come from the API)
  const students: StudentProgress[] = [
    {
      id: '1',
      name: 'Emma Johnson',
      grade: '5th Grade',
      overallProgress: 85,
      subjectProgress: [
        { subject: 'Math', progress: 92, trend: 'up' },
        { subject: 'Reading', progress: 78, trend: 'stable' },
        { subject: 'Science', progress: 88, trend: 'up' },
        { subject: 'Social Studies', progress: 82, trend: 'down' },
      ],
      recentAchievements: [
        { title: 'Math Star', date: '2025-08-15', icon: 'trophy' },
        { title: 'Reading Milestone', date: '2025-08-12', icon: 'book' },
        { title: 'Perfect Week', date: '2025-08-10', icon: 'star' },
      ],
      weeklyGoals: [
        { goal: 'Complete 5 Math lessons', progress: 4, target: 5 },
        { goal: 'Read 3 books', progress: 2, target: 3 },
        { goal: '30 min daily practice', progress: 6, target: 7 },
      ],
    },
    {
      id: '2',
      name: 'Alex Johnson',
      grade: '3rd Grade',
      overallProgress: 78,
      subjectProgress: [
        { subject: 'Math', progress: 75, trend: 'up' },
        { subject: 'Reading', progress: 82, trend: 'up' },
        { subject: 'Science', progress: 76, trend: 'stable' },
        { subject: 'Art', progress: 85, trend: 'up' },
      ],
      recentAchievements: [
        { title: 'Reading Champion', date: '2025-08-14', icon: 'book' },
        { title: 'Creative Artist', date: '2025-08-11', icon: 'palette' },
      ],
      weeklyGoals: [
        { goal: 'Complete 4 Reading sessions', progress: 3, target: 4 },
        { goal: 'Art project completion', progress: 1, target: 1 },
        { goal: '20 min math practice', progress: 5, target: 7 },
      ],
    },
  ]

  const currentStudent =
    students.find(s => s.id === selectedChild) || students[0]

  const handleRefresh = async () => {
    setRefreshing(true)
    await refetch()
    setTimeout(() => setRefreshing(false), 1000)
  }

  const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-500" />
      case 'down':
        return <TrendingUp className="w-4 h-4 text-red-500 rotate-180" />
      default:
        return <div className="w-2 h-2 bg-gray-400 rounded-full" />
    }
  }

  const getAchievementIcon = (icon: string) => {
    switch (icon) {
      case 'trophy':
        return <Trophy className="w-5 h-5 text-yellow-500" />
      case 'book':
        return <BookOpen className="w-5 h-5 text-blue-500" />
      case 'star':
        return <Award className="w-5 h-5 text-purple-500" />
      default:
        return <Award className="w-5 h-5 text-gray-500" />
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
          <h1 className="text-3xl font-bold text-gray-900">Parent Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Monitor your children's learning progress
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Child Selector */}
          <select
            value={selectedChild || students[0]?.id}
            onChange={e => setSelectedChild(e.target.value)}
            className="px-3 py-2 border rounded-lg bg-white"
            aria-label="Select child"
          >
            {students.map(student => (
              <option key={student.id} value={student.id}>
                {student.name}
              </option>
            ))}
          </select>

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

      {/* Student Overview Card */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <Avatar className="w-16 h-16">
              <AvatarImage
                src={currentStudent.avatar}
                alt={currentStudent.name}
              />
              <AvatarFallback>
                {currentStudent.name
                  .split(' ')
                  .map(n => n[0])
                  .join('')}
              </AvatarFallback>
            </Avatar>

            <div className="flex-1">
              <h2 className="text-xl font-semibold">{currentStudent.name}</h2>
              <p className="text-gray-600">{currentStudent.grade}</p>
              <div className="flex items-center gap-2 mt-2">
                <div className="text-sm text-gray-500">Overall Progress:</div>
                <div className="flex items-center gap-2">
                  <div className="w-32 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${currentStudent.overallProgress}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">
                    {currentStudent.overallProgress}%
                  </span>
                </div>
              </div>
            </div>

            <div className="text-right">
              <div className="text-sm text-gray-500">Last Activity</div>
              <div className="flex items-center gap-1 text-sm">
                <Clock className="w-4 h-4 text-gray-400" />
                Today, 3:30 PM
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="progress">Progress</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="goals">Goals</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Activity className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">This Week</div>
                    <div className="text-xl font-semibold">12 hours</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <Trophy className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Achievements</div>
                    <div className="text-xl font-semibold">3 new</div>
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
                    <div className="text-sm text-gray-500">Goals Met</div>
                    <div className="text-xl font-semibold">7 of 10</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-yellow-100 rounded-lg">
                    <BookOpen className="w-5 h-5 text-yellow-600" />
                  </div>
                  <div>
                    <div className="text-sm text-gray-500">Lessons</div>
                    <div className="text-xl font-semibold">18 done</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Subject Progress */}
          <Card>
            <CardHeader>
              <CardTitle>Subject Progress</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {currentStudent.subjectProgress.map((subject, index) => (
                  <div key={index} className="flex items-center gap-4">
                    <div className="w-24 text-sm font-medium">
                      {subject.subject}
                    </div>
                    <div className="flex-1 flex items-center gap-3">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${subject.progress}%` }}
                        />
                      </div>
                      <div className="text-sm font-medium w-12">
                        {subject.progress}%
                      </div>
                      {getTrendIcon(subject.trend)}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recent Achievements */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Achievements</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {currentStudent.recentAchievements.map((achievement, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
                  >
                    {getAchievementIcon(achievement.icon)}
                    <div className="flex-1">
                      <div className="font-medium">{achievement.title}</div>
                      <div className="text-sm text-gray-500">
                        {achievement.date}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="progress" className="space-y-6">
          {analyticsData && (
            <ProgressChart
              data={analyticsData.progressData}
              subjects={analyticsData.subjects}
              role="parent"
            />
          )}
        </TabsContent>

        <TabsContent value="activity" className="space-y-6">
          {analyticsData && (
            <UsageChart
              data={analyticsData.usageData}
              metrics={analyticsData.usageMetrics}
              role="parent"
            />
          )}
        </TabsContent>

        <TabsContent value="goals" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Weekly Goals</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {currentStudent.weeklyGoals.map((goal, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-medium">{goal.goal}</span>
                      <span className="text-sm text-gray-500">
                        {goal.progress} / {goal.target}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          goal.progress >= goal.target
                            ? 'bg-green-600'
                            : 'bg-blue-600'
                        }`}
                        style={{
                          width: `${Math.min((goal.progress / goal.target) * 100, 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {analyticsData && (
            <AlertsChart alerts={analyticsData.alerts} role="parent" />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ParentDashboard
