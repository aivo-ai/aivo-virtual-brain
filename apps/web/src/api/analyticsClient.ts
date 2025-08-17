import { useQuery } from '@tanstack/react-query'
import { ProgressData, Subject } from '../components/charts/ProgressChart'
import { UsageData, UsageMetric } from '../components/charts/UsageChart'
import { Alert } from '../components/charts/AlertsChart'

// API endpoints (these would be real endpoints in production)
const API_BASE = '/api/analytics'

// Mock data generators for development
const generateMockProgressData = (): ProgressData[] => {
  const data: ProgressData[] = []
  const today = new Date()

  for (let i = 29; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)

    data.push({
      date: date.toISOString().split('T')[0],
      overall: Math.floor(Math.random() * 20) + 70, // 70-90%
      math: Math.floor(Math.random() * 25) + 65, // 65-90%
      reading: Math.floor(Math.random() * 30) + 60, // 60-90%
      science: Math.floor(Math.random() * 25) + 70, // 70-95%
      socialStudies: Math.floor(Math.random() * 20) + 75, // 75-95%
    })
  }

  return data
}

const generateMockSubjects = (): Subject[] => [
  {
    name: 'Math',
    color: '#3B82F6',
    target: 85,
    current: 78,
    trend: 'up',
  },
  {
    name: 'Reading',
    color: '#10B981',
    target: 80,
    current: 72,
    trend: 'stable',
  },
  {
    name: 'Science',
    color: '#F59E0B',
    target: 75,
    current: 81,
    trend: 'up',
  },
  {
    name: 'Social Studies',
    color: '#8B5CF6',
    target: 70,
    current: 68,
    trend: 'down',
  },
]

const generateMockUsageData = (): UsageData[] => {
  const data: UsageData[] = []
  const today = new Date()

  for (let i = 29; i >= 0; i--) {
    const date = new Date(today)
    date.setDate(date.getDate() - i)

    data.push({
      date: date.toISOString().split('T')[0],
      activeUsers: Math.floor(Math.random() * 50) + 100,
      sessionsCompleted: Math.floor(Math.random() * 30) + 40,
      avgSessionTime: Math.floor(Math.random() * 20) + 25, // minutes
      engagementScore: Math.floor(Math.random() * 20) + 75,
      completionRate: Math.floor(Math.random() * 15) + 80,
    })
  }

  return data
}

const generateMockUsageMetrics = (): UsageMetric[] => [
  {
    name: 'Daily Active Users',
    current: 1247,
    previous: 1189,
    trend: 'up',
    description: 'Students who logged in today',
    category: 'engagement',
  },
  {
    name: 'Session Completion Rate',
    current: 87,
    previous: 82,
    trend: 'up',
    description: 'Percentage of completed sessions',
    category: 'performance',
  },
  {
    name: 'Average Session Time',
    current: 28,
    previous: 25,
    trend: 'up',
    description: 'Minutes per learning session',
    category: 'engagement',
  },
  {
    name: 'Weekly Goals Met',
    current: 73,
    previous: 79,
    trend: 'down',
    description: 'Percentage of weekly targets achieved',
    category: 'performance',
  },
  {
    name: 'Content Interactions',
    current: 2456,
    previous: 2301,
    trend: 'up',
    description: 'Total content interactions today',
    category: 'activity',
  },
  {
    name: 'Assessment Scores',
    current: 84,
    previous: 81,
    trend: 'up',
    description: 'Average assessment performance',
    category: 'performance',
  },
]

const generateMockAlerts = (): Alert[] => [
  {
    id: '1',
    title: 'Low Reading Comprehension',
    description: 'Student showing declining performance in reading assessments',
    severity: 'medium',
    category: 'academic',
    studentId: '1',
    studentName: 'Emma Rodriguez',
    classId: '1',
    className: 'Reading 5A',
    date: '2025-08-17',
    status: 'active',
    assignedTo: 'Ms. Johnson',
  },
  {
    id: '2',
    title: 'Attendance Pattern Concern',
    description: 'Student has missed 3 consecutive days without notification',
    severity: 'high',
    category: 'attendance',
    studentId: '2',
    studentName: 'James Kim',
    classId: '2',
    className: 'Math 5B',
    date: '2025-08-16',
    status: 'acknowledged',
    assignedTo: 'Mr. Chen',
  },
  {
    id: '3',
    title: 'System Performance Issue',
    description: 'Learning platform experiencing slow response times',
    severity: 'medium',
    category: 'technical',
    schoolId: '1',
    schoolName: 'Lincoln Elementary',
    date: '2025-08-15',
    status: 'resolved',
    assignedTo: 'IT Support',
  },
  {
    id: '4',
    title: 'Behavior Incident Report',
    description: 'Disruptive behavior affecting classroom learning environment',
    severity: 'high',
    category: 'behavior',
    studentId: '3',
    studentName: 'Alex Thompson',
    classId: '1',
    className: 'Science 5A',
    date: '2025-08-14',
    status: 'active',
    assignedTo: 'Principal Davis',
  },
  {
    id: '5',
    title: 'Safety Protocol Update',
    description: 'Emergency drill procedures updated, requires acknowledgment',
    severity: 'medium',
    category: 'safety',
    schoolId: '2',
    schoolName: 'Washington Middle School',
    date: '2025-08-13',
    status: 'acknowledged',
    assignedTo: 'Safety Officer',
  },
]

export interface AnalyticsData {
  progressData: ProgressData[]
  subjects: Subject[]
  usageData: UsageData[]
  usageMetrics: UsageMetric[]
  alerts: Alert[]
}

// Parent Analytics Hook
export const useParentAnalytics = () => {
  return useQuery<AnalyticsData>({
    queryKey: ['analytics', 'parent'],
    queryFn: async (): Promise<AnalyticsData> => {
      // In production, this would be a real API call
      // const response = await fetch(`${API_BASE}/parent`);
      // return response.json();

      // Mock data for development
      return new Promise(resolve => {
        setTimeout(() => {
          resolve({
            progressData: generateMockProgressData(),
            subjects: generateMockSubjects(),
            usageData: generateMockUsageData(),
            usageMetrics: generateMockUsageMetrics(),
            alerts: generateMockAlerts().filter(
              alert =>
                alert.category === 'academic' || alert.category === 'attendance'
            ),
          })
        }, 1000)
      })
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // 10 minutes
  })
}

// Teacher Analytics Hook
export const useTeacherAnalytics = () => {
  return useQuery<AnalyticsData>({
    queryKey: ['analytics', 'teacher'],
    queryFn: async (): Promise<AnalyticsData> => {
      // In production, this would be a real API call
      // const response = await fetch(`${API_BASE}/teacher`);
      // return response.json();

      // Mock data for development
      return new Promise(resolve => {
        setTimeout(() => {
          resolve({
            progressData: generateMockProgressData(),
            subjects: generateMockSubjects(),
            usageData: generateMockUsageData(),
            usageMetrics: generateMockUsageMetrics().map(metric => ({
              ...metric,
              // Adjust metrics for teacher perspective
              current: Math.floor(metric.current * 1.1),
              previous: Math.floor(metric.previous * 1.05),
            })),
            alerts: generateMockAlerts().filter(
              alert => alert.category !== 'technical'
            ),
          })
        }, 1000)
      })
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 10 * 60 * 1000, // 10 minutes
  })
}

// District Analytics Hook
export const useDistrictAnalytics = () => {
  return useQuery<AnalyticsData>({
    queryKey: ['analytics', 'district'],
    queryFn: async (): Promise<AnalyticsData> => {
      // In production, this would be a real API call
      // const response = await fetch(`${API_BASE}/district`);
      // return response.json();

      // Mock data for development
      return new Promise(resolve => {
        setTimeout(() => {
          resolve({
            progressData: generateMockProgressData().map(data => ({
              ...data,
              // Scale up numbers for district view
              overall: Math.floor(data.overall * 10),
              math: Math.floor(data.math * 12),
              reading: Math.floor(data.reading * 11),
              science: Math.floor(data.science * 9),
              socialStudies: Math.floor(data.socialStudies * 8),
            })),
            subjects: generateMockSubjects().map(subject => ({
              ...subject,
              current: Math.floor(subject.current * 1.2),
              target: Math.floor(subject.target * 1.15),
            })),
            usageData: generateMockUsageData().map(data => ({
              ...data,
              // Scale up for district view
              activeUsers: data.activeUsers * 50,
              sessionsCompleted: data.sessionsCompleted * 100,
              avgSessionTime: data.avgSessionTime,
              engagementScore: data.engagementScore,
              completionRate: data.completionRate,
            })),
            usageMetrics: generateMockUsageMetrics().map(metric => ({
              ...metric,
              // Scale up for district view
              current: Math.floor(metric.current * 100),
              previous: Math.floor(metric.previous * 95),
            })),
            alerts: generateMockAlerts(), // All alerts for district view
          })
        }, 1200)
      })
    },
    staleTime: 3 * 60 * 1000, // 3 minutes
    refetchInterval: 5 * 60 * 1000, // 5 minutes
  })
}

// Individual hooks for specific data types
export const useProgressData = (role: 'parent' | 'teacher' | 'district') => {
  return useQuery<ProgressData[]>({
    queryKey: ['progress', role],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/${role}/progress`)
      return response.json()
    },
    staleTime: 5 * 60 * 1000,
  })
}

export const useUsageData = (role: 'parent' | 'teacher' | 'district') => {
  return useQuery<UsageData[]>({
    queryKey: ['usage', role],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/${role}/usage`)
      return response.json()
    },
    staleTime: 2 * 60 * 1000,
  })
}

export const useAlertsData = (role: 'parent' | 'teacher' | 'district') => {
  return useQuery<Alert[]>({
    queryKey: ['alerts', role],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/${role}/alerts`)
      return response.json()
    },
    staleTime: 1 * 60 * 1000, // 1 minute for alerts
    refetchInterval: 2 * 60 * 1000, // 2 minutes
  })
}
