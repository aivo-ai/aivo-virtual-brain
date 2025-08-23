/**
 * Notification Preferences Page (S5-07)
 * Manage notification settings including Weekly Wins digest preferences
 */
import { useState, useEffect } from 'react'
import { Bell, Mail, Smartphone, Clock, Calendar, Save, X } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { useToast } from '@/hooks/useToast'
import { useAuth } from '@/app/providers/AuthProvider'

interface NotificationPreferences {
  // General notification preferences
  emailNotifications: boolean
  pushNotifications: boolean

  // Weekly Wins specific preferences
  weeklyWinsEnabled: boolean
  weeklyWinsDay: 'sunday' | 'monday'
  weeklyWinsTime: string
  weeklyWinsTimezone: string
  weeklyWinsLanguage: string
  weeklyWinsIncludeComparison: boolean

  // Other digest preferences
  monthlyReportsEnabled: boolean
  iepUpdateNotifications: boolean
  assessmentNotifications: boolean
  goalCompletionNotifications: boolean

  // Delivery preferences
  quietHoursEnabled: boolean
  quietHoursStart: string
  quietHoursEnd: string

  // Frequency preferences
  digestFrequency: 'weekly' | 'biweekly' | 'monthly'
  reminderFrequency: 'daily' | 'weekly' | 'never'
}

export default function NotificationPreferencesPage() {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    emailNotifications: true,
    pushNotifications: false,
    weeklyWinsEnabled: true,
    weeklyWinsDay: 'sunday',
    weeklyWinsTime: '17:00',
    weeklyWinsTimezone: 'America/New_York',
    weeklyWinsLanguage: 'en',
    weeklyWinsIncludeComparison: true,
    monthlyReportsEnabled: true,
    iepUpdateNotifications: true,
    assessmentNotifications: true,
    goalCompletionNotifications: true,
    quietHoursEnabled: false,
    quietHoursStart: '22:00',
    quietHoursEnd: '08:00',
    digestFrequency: 'weekly',
    reminderFrequency: 'weekly',
  })

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [isDirty, setIsDirty] = useState(false)

  const { user } = useAuth()
  const { toast } = useToast()

  useEffect(() => {
    loadPreferences()
  }, [])

  useEffect(() => {
    // Detect changes to mark form as dirty
    setIsDirty(true)
  }, [preferences])

  const loadPreferences = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/notifications/preferences', {
        headers: {
          Authorization: `Bearer ${user?.token}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setPreferences({ ...preferences, ...data.preferences })
        setIsDirty(false)
      } else {
        throw new Error('Failed to load preferences')
      }
    } catch (error) {
      console.error('Error loading preferences:', error)
      toast({
        title: 'Error',
        description: 'Failed to load notification preferences.',
        variant: 'destructive',
      })
    } finally {
      setLoading(false)
    }
  }

  const savePreferences = async () => {
    try {
      setSaving(true)
      const response = await fetch('/api/notifications/preferences', {
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
          description: 'Notification preferences updated successfully.',
        })
        setIsDirty(false)
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
    } finally {
      setSaving(false)
    }
  }

  const resetPreferences = () => {
    loadPreferences()
    setIsDirty(false)
  }

  const updatePreference = (key: keyof NotificationPreferences, value: any) => {
    setPreferences(prev => ({
      ...prev,
      [key]: value,
    }))
  }

  const timezoneOptions = [
    { value: 'America/New_York', label: 'Eastern Time (ET)' },
    { value: 'America/Chicago', label: 'Central Time (CT)' },
    { value: 'America/Denver', label: 'Mountain Time (MT)' },
    { value: 'America/Los_Angeles', label: 'Pacific Time (PT)' },
    { value: 'Europe/London', label: 'London (GMT)' },
    { value: 'Europe/Paris', label: 'Paris (CET)' },
    { value: 'Europe/Berlin', label: 'Berlin (CET)' },
    { value: 'Asia/Tokyo', label: 'Tokyo (JST)' },
    { value: 'Asia/Shanghai', label: 'Shanghai (CST)' },
    { value: 'Australia/Sydney', label: 'Sydney (AEDT)' },
  ]

  const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'es', label: 'Español' },
    { value: 'fr', label: 'Français' },
    { value: 'de', label: 'Deutsch' },
  ]

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center space-x-2 mb-6">
          <Bell className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Notification Preferences</h1>
        </div>
        <div className="text-center py-8">
          <div className="animate-pulse">Loading preferences...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <Bell className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Notification Preferences</h1>
        </div>
        {isDirty && (
          <div className="flex space-x-2">
            <Button
              variant="outline"
              onClick={resetPreferences}
              disabled={saving}
            >
              <X className="h-4 w-4 mr-2" />
              Cancel
            </Button>
            <Button onClick={savePreferences} disabled={saving}>
              <Save className="h-4 w-4 mr-2" />
              {saving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        )}
      </div>

      <div className="space-y-6">
        {/* General Notification Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Bell className="h-5 w-5" />
              <span>General Notifications</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center space-x-3">
                <Mail className="h-5 w-5 text-gray-500" />
                <div className="flex-1">
                  <Label>Email Notifications</Label>
                  <p className="text-sm text-gray-600">
                    Receive notifications via email
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={preferences.emailNotifications}
                  onChange={e =>
                    updatePreference('emailNotifications', e.target.checked)
                  }
                  className="rounded"
                />
              </div>

              <div className="flex items-center space-x-3">
                <Smartphone className="h-5 w-5 text-gray-500" />
                <div className="flex-1">
                  <Label>Push Notifications</Label>
                  <p className="text-sm text-gray-600">
                    Receive push notifications on your device
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={preferences.pushNotifications}
                  onChange={e =>
                    updatePreference('pushNotifications', e.target.checked)
                  }
                  className="rounded"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Weekly Wins Digest Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Calendar className="h-5 w-5" />
              <span>Weekly Wins Digest</span>
              <Badge variant="outline">Featured</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-3 mb-4">
              <div className="flex-1">
                <Label>Enable Weekly Wins</Label>
                <p className="text-sm text-gray-600">
                  Get a personalized weekly digest highlighting your learner's
                  progress, achievements, and wins
                </p>
              </div>
              <input
                type="checkbox"
                checked={preferences.weeklyWinsEnabled}
                onChange={e =>
                  updatePreference('weeklyWinsEnabled', e.target.checked)
                }
                className="rounded"
              />
            </div>

            {preferences.weeklyWinsEnabled && (
              <div className="pl-4 border-l-2 border-blue-200 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Delivery Day</Label>
                    <select
                      value={preferences.weeklyWinsDay}
                      onChange={e =>
                        updatePreference('weeklyWinsDay', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="sunday">Sunday</option>
                      <option value="monday">Monday</option>
                    </select>
                    <p className="text-xs text-gray-500">
                      When to receive your weekly digest
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Delivery Time</Label>
                    <Input
                      type="time"
                      value={preferences.weeklyWinsTime}
                      onChange={e =>
                        updatePreference('weeklyWinsTime', e.target.value)
                      }
                    />
                    <p className="text-xs text-gray-500">
                      Your local time for digest delivery
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Timezone</Label>
                    <select
                      value={preferences.weeklyWinsTimezone}
                      onChange={e =>
                        updatePreference('weeklyWinsTimezone', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {timezoneOptions.map(tz => (
                        <option key={tz.value} value={tz.value}>
                          {tz.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="space-y-2">
                    <Label>Language</Label>
                    <select
                      value={preferences.weeklyWinsLanguage}
                      onChange={e =>
                        updatePreference('weeklyWinsLanguage', e.target.value)
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {languageOptions.map(lang => (
                        <option key={lang.value} value={lang.value}>
                          {lang.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={preferences.weeklyWinsIncludeComparison}
                    onChange={e =>
                      updatePreference(
                        'weeklyWinsIncludeComparison',
                        e.target.checked
                      )
                    }
                    className="rounded"
                  />
                  <div>
                    <Label>Include Week-over-Week Comparison</Label>
                    <p className="text-sm text-gray-600">
                      Show how this week compares to the previous week
                    </p>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Other Notification Types */}
        <Card>
          <CardHeader>
            <CardTitle>Notification Types</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="flex items-center space-x-3">
                <div className="flex-1">
                  <Label>Monthly Progress Reports</Label>
                  <p className="text-sm text-gray-600">
                    Comprehensive monthly analytics
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={preferences.monthlyReportsEnabled}
                  onChange={e =>
                    updatePreference('monthlyReportsEnabled', e.target.checked)
                  }
                  className="rounded"
                />
              </div>

              <div className="flex items-center space-x-3">
                <div className="flex-1">
                  <Label>IEP Updates</Label>
                  <p className="text-sm text-gray-600">
                    IEP plan changes and progress
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={preferences.iepUpdateNotifications}
                  onChange={e =>
                    updatePreference('iepUpdateNotifications', e.target.checked)
                  }
                  className="rounded"
                />
              </div>

              <div className="flex items-center space-x-3">
                <div className="flex-1">
                  <Label>Assessment Completions</Label>
                  <p className="text-sm text-gray-600">
                    When assessments are completed
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={preferences.assessmentNotifications}
                  onChange={e =>
                    updatePreference(
                      'assessmentNotifications',
                      e.target.checked
                    )
                  }
                  className="rounded"
                />
              </div>

              <div className="flex items-center space-x-3">
                <div className="flex-1">
                  <Label>Goal Achievements</Label>
                  <p className="text-sm text-gray-600">
                    When learning goals are achieved
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={preferences.goalCompletionNotifications}
                  onChange={e =>
                    updatePreference(
                      'goalCompletionNotifications',
                      e.target.checked
                    )
                  }
                  className="rounded"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Quiet Hours */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Clock className="h-5 w-5" />
              <span>Quiet Hours</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-3 mb-4">
              <div className="flex-1">
                <Label>Enable Quiet Hours</Label>
                <p className="text-sm text-gray-600">
                  Pause non-urgent notifications during specified hours
                </p>
              </div>
              <input
                type="checkbox"
                checked={preferences.quietHoursEnabled}
                onChange={e =>
                  updatePreference('quietHoursEnabled', e.target.checked)
                }
                className="rounded"
              />
            </div>

            {preferences.quietHoursEnabled && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Start Time</Label>
                  <Input
                    type="time"
                    value={preferences.quietHoursStart}
                    onChange={e =>
                      updatePreference('quietHoursStart', e.target.value)
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>End Time</Label>
                  <Input
                    type="time"
                    value={preferences.quietHoursEnd}
                    onChange={e =>
                      updatePreference('quietHoursEnd', e.target.value)
                    }
                  />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Save Button (mobile) */}
        {isDirty && (
          <div className="md:hidden fixed bottom-4 left-4 right-4 z-50">
            <div className="flex space-x-2">
              <Button
                variant="outline"
                onClick={resetPreferences}
                disabled={saving}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={savePreferences}
                disabled={saving}
                className="flex-1"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
