/**
 * Notifications Digests Page (S5-07)
 * List and preview weekly wins and other digest notifications
 */
import React, { useState, useEffect } from 'react'
import {
  Calendar,
  Clock,
  Mail,
  Bell,
  Eye,
  Download,
  Settings,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Progress } from '@/components/ui/Progress'
import { useToast } from '@/hooks/useToast'
import { useAuth } from '@/app/providers/AuthProvider'

interface DigestItem {
  id: string
  type: 'weekly_wins' | 'monthly_summary' | 'progress_report'
  title: string
  generatedAt: string
  weekStart?: string
  weekEnd?: string
  status: 'generated' | 'sent' | 'failed'
  recipientCount: number
  previewUrl?: string
  downloadUrl?: string
  learnerData?: {
    learnerName: string
    hoursLearned: number
    subjectsAdvanced: number
    goalsCompleted: number
    streakDays: number
  }
}

interface DigestPreferences {
  weeklyWinsEnabled: boolean
  deliveryDay: 'sunday' | 'monday'
  deliveryTime: string
  timezone: string
  includeComparison: boolean
  language: string
}

export default function DigestsPage() {
  const [digests, setDigests] = useState<DigestItem[]>([])
  const [preferences, setPreferences] = useState<DigestPreferences>({
    weeklyWinsEnabled: true,
    deliveryDay: 'sunday',
    deliveryTime: '17:00',
    timezone: 'America/New_York',
    includeComparison: true,
    language: 'en',
  })
  const [loading, setLoading] = useState(true)
  const [selectedDigest, setSelectedDigest] = useState<DigestItem | null>(null)
  const [showPreferences, setShowPreferences] = useState(false)
  const [filterType, setFilterType] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')

  const { user } = useAuth()
  const { toast } = useToast()

  useEffect(() => {
    loadDigests()
    loadPreferences()
  }, [])

  const loadDigests = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/notifications/digests', {
        headers: {
          Authorization: `Bearer ${user?.token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setDigests(data.digests || [])
      } else {
        throw new Error('Failed to load digests')
      }
    } catch (error) {
      console.error('Error loading digests:', error)
      toast({
        title: 'Error',
        description: 'Failed to load digest history.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const loadPreferences = async () => {
    try {
      const response = await fetch('/api/notifications/digest-preferences', {
        headers: {
          Authorization: `Bearer ${user?.token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setPreferences(data.preferences || preferences)
      }
    } catch (error) {
      console.error('Error loading preferences:', error)
    }
  }

  const savePreferences = async () => {
    try {
      const response = await fetch('/api/notifications/digest-preferences', {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${user?.token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ preferences }),
      })

      if (response.ok) {
        toast({
          title: 'Success',
          description: 'Digest preferences updated successfully.',
        })
        setShowPreferences(false)
      } else {
        throw new Error('Failed to save preferences')
      }
    } catch (error) {
      console.error('Error saving preferences:', error)
      toast({
        title: 'Error',
        description: 'Failed to save preferences.',
        variant: 'destructive',
      })
    }
  }

  const generatePreviewDigest = async () => {
    try {
      const response = await fetch(
        '/api/notifications/digests/weekly-wins/preview',
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${user?.token}`,
            'Content-Type': 'application/json',
          },
        }
      )

      if (response.ok) {
        const data = await response.json()
        toast({
          title: 'Preview Generated',
          description: 'Weekly wins preview has been generated.',
        })
        loadDigests() // Refresh the list
      } else {
        throw new Error('Failed to generate preview')
      }
    } catch (error) {
      console.error('Error generating preview:', error)
      toast({
        title: 'Error',
        description: 'Failed to generate digest preview.',
        variant: 'destructive',
      })
    }
  }

  const filteredDigests = digests.filter(digest => {
    const matchesType = filterType === 'all' || digest.type === filterType
    const matchesSearch =
      searchTerm === '' ||
      digest.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      digest.learnerData?.learnerName
        .toLowerCase()
        .includes(searchTerm.toLowerCase())

    return matchesType && matchesSearch
  })

  const getDigestTypeLabel = (type: string) => {
    switch (type) {
      case 'weekly_wins':
        return 'Weekly Wins'
      case 'monthly_summary':
        return 'Monthly Summary'
      case 'progress_report':
        return 'Progress Report'
      default:
        return type
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'generated':
        return <Badge variant="outline">Generated</Badge>
      case 'sent':
        return <Badge>Sent</Badge>
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      weekday: 'short',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center space-x-2 mb-6">
          <Mail className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Digest Notifications</h1>
        </div>
        <div className="text-center py-8">
          <div className="animate-pulse">Loading digests...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Mail className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Digest Notifications</h1>
        </div>
        <div className="flex space-x-2">
          <Button
            variant="outline"
            onClick={generatePreviewDigest}
            className="flex items-center space-x-2"
          >
            <Eye className="h-4 w-4" />
            <span>Generate Preview</span>
          </Button>
          <Button
            variant="outline"
            onClick={() => setShowPreferences(!showPreferences)}
            className="flex items-center space-x-2"
          >
            <Settings className="h-4 w-4" />
            <span>Preferences</span>
          </Button>
        </div>
      </div>

      {/* Preferences Panel */}
      {showPreferences && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Settings className="h-5 w-5" />
              <span>Weekly Wins Preferences</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Enable Weekly Wins</Label>
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={preferences.weeklyWinsEnabled}
                    onChange={e =>
                      setPreferences({
                        ...preferences,
                        weeklyWinsEnabled: e.target.checked,
                      })
                    }
                    className="rounded"
                  />
                  <span className="text-sm text-gray-600">
                    Receive weekly progress digests
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Delivery Day</Label>
                <select
                  value={preferences.deliveryDay}
                  onChange={e =>
                    setPreferences({
                      ...preferences,
                      deliveryDay: e.target.value as 'sunday' | 'monday',
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="sunday">Sunday</option>
                  <option value="monday">Monday</option>
                </select>
              </div>

              <div className="space-y-2">
                <Label>Delivery Time</Label>
                <Input
                  type="time"
                  value={preferences.deliveryTime}
                  onChange={e =>
                    setPreferences({
                      ...preferences,
                      deliveryTime: e.target.value,
                    })
                  }
                />
              </div>

              <div className="space-y-2">
                <Label>Timezone</Label>
                <select
                  value={preferences.timezone}
                  onChange={e =>
                    setPreferences({
                      ...preferences,
                      timezone: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="America/New_York">Eastern Time</option>
                  <option value="America/Chicago">Central Time</option>
                  <option value="America/Denver">Mountain Time</option>
                  <option value="America/Los_Angeles">Pacific Time</option>
                  <option value="Europe/London">London</option>
                  <option value="Europe/Paris">Paris</option>
                </select>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={preferences.includeComparison}
                onChange={e =>
                  setPreferences({
                    ...preferences,
                    includeComparison: e.target.checked,
                  })
                }
                className="rounded"
              />
              <Label>Include week-over-week comparison</Label>
            </div>

            <div className="flex justify-end space-x-2">
              <Button
                variant="outline"
                onClick={() => setShowPreferences(false)}
              >
                Cancel
              </Button>
              <Button onClick={savePreferences}>Save Preferences</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Label>Search</Label>
              <Input
                placeholder="Search digests..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
              />
            </div>
            <div>
              <Label>Filter by Type</Label>
              <select
                value={filterType}
                onChange={e => setFilterType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              >
                <option value="all">All Types</option>
                <option value="weekly_wins">Weekly Wins</option>
                <option value="monthly_summary">Monthly Summary</option>
                <option value="progress_report">Progress Report</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Digests List */}
      <div className="space-y-4">
        {filteredDigests.length === 0 ? (
          <Card>
            <CardContent className="text-center py-8">
              <Mail className="h-12 w-12 mx-auto text-gray-400 mb-4" />
              <h3 className="text-lg font-semibold mb-2">No Digests Found</h3>
              <p className="text-gray-600 mb-4">
                {searchTerm || filterType !== 'all'
                  ? 'Try adjusting your search or filter criteria.'
                  : 'Weekly digests will appear here once generated.'}
              </p>
              {!searchTerm && filterType === 'all' && (
                <Button onClick={generatePreviewDigest}>
                  Generate Sample Digest
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          filteredDigests.map(digest => (
            <Card key={digest.id} className="hover:shadow-md transition-shadow">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <h3 className="text-lg font-semibold">{digest.title}</h3>
                      {getStatusBadge(digest.status)}
                      <Badge variant="outline">
                        {getDigestTypeLabel(digest.type)}
                      </Badge>
                    </div>

                    <div className="flex items-center space-x-4 text-sm text-gray-600 mb-3">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{formatDate(digest.generatedAt)}</span>
                      </div>
                      {digest.weekStart && digest.weekEnd && (
                        <div className="flex items-center space-x-1">
                          <Clock className="h-4 w-4" />
                          <span>
                            {new Date(digest.weekStart).toLocaleDateString()} -{' '}
                            {new Date(digest.weekEnd).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                      <div className="flex items-center space-x-1">
                        <Bell className="h-4 w-4" />
                        <span>{digest.recipientCount} recipients</span>
                      </div>
                    </div>

                    {/* Weekly Wins Summary */}
                    {digest.type === 'weekly_wins' && digest.learnerData && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                        <div className="text-center">
                          <div className="text-2xl font-bold text-blue-600">
                            {digest.learnerData.hoursLearned}h
                          </div>
                          <div className="text-xs text-gray-500">
                            Hours Learned
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-green-600">
                            {digest.learnerData.subjectsAdvanced}
                          </div>
                          <div className="text-xs text-gray-500">
                            Subjects Advanced
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-purple-600">
                            {digest.learnerData.goalsCompleted}
                          </div>
                          <div className="text-xs text-gray-500">
                            Goals Completed
                          </div>
                        </div>
                        <div className="text-center">
                          <div className="text-2xl font-bold text-orange-600">
                            {digest.learnerData.streakDays}
                          </div>
                          <div className="text-xs text-gray-500">
                            Day Streak
                          </div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="flex space-x-2 ml-4">
                    {digest.previewUrl && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => window.open(digest.previewUrl, '_blank')}
                        className="flex items-center space-x-1"
                      >
                        <Eye className="h-4 w-4" />
                        <span>Preview</span>
                      </Button>
                    )}
                    {digest.downloadUrl && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          window.open(digest.downloadUrl, '_blank')
                        }
                        className="flex items-center space-x-1"
                      >
                        <Download className="h-4 w-4" />
                        <span>Download</span>
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Pagination could go here if needed */}
    </div>
  )
}
