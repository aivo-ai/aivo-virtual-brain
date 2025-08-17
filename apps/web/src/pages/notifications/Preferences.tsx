/**
 * S3-14 Notifications Preferences
 * User preferences for notification management
 */

import { useState, useEffect } from 'react'
import { useNotificationPreferences, NotificationTypes, NotificationPreferences as NotificationPreferencesType } from '../../api/notificationClient'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Alert, AlertDescription } from '../../components/ui/Alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/Tabs'
import { 
  Settings,
  Bell,
  Mail,
  Smartphone,
  Volume2,
  VolumeX,
  Sun,
  Moon,
  CheckCircle,
  AlertTriangle,
  Info,
  Save,
  Loader2,
  ArrowLeft,
  User
} from '../../components/ui/Icons'

interface NotificationTypeToggleProps {
  type: NotificationTypes
  enabled: boolean
  onToggle: (type: NotificationTypes, enabled: boolean) => void
}

function NotificationTypeToggle({ type, enabled, onToggle }: NotificationTypeToggleProps) {
  const getTypeInfo = () => {
    switch (type) {
      case NotificationTypes.SYSTEM:
        return {
          label: 'System Updates',
          description: 'Important system announcements and maintenance notices',
          icon: <Settings className="w-5 h-5" />,
          color: 'text-gray-600'
        }
      case NotificationTypes.ACADEMIC:
        return {
          label: 'Academic Progress',
          description: 'Grade updates, assignment feedback, and academic milestones',
          icon: <CheckCircle className="w-5 h-5" />,
          color: 'text-blue-600'
        }
      case NotificationTypes.SOCIAL:
        return {
          label: 'Social Activities',
          description: 'Social interactions, group activities, and community updates',
          icon: <User className="w-5 h-5" />,
          color: 'text-teal-600'
        }
      case NotificationTypes.REMINDER:
        return {
          label: 'Reminders',
          description: 'Important reminders for tasks, deadlines, and activities',
          icon: <Bell className="w-5 h-5" />,
          color: 'text-amber-600'
        }
      case NotificationTypes.ALERT:
        return {
          label: 'Alerts',
          description: 'Urgent notifications and important alerts',
          icon: <AlertTriangle className="w-5 h-5" />,
          color: 'text-red-600'
        }
      case NotificationTypes.SEL:
        return {
          label: 'Social-Emotional Learning',
          description: 'Check-in reminders, emotional insights, and SEL activities',
          icon: <Info className="w-5 h-5" />,
          color: 'text-purple-600'
        }
      case NotificationTypes.ASSESSMENT:
        return {
          label: 'Assessments',
          description: 'Quiz reminders, assessment results, and feedback',
          icon: <AlertTriangle className="w-5 h-5" />,
          color: 'text-indigo-600'
        }
      case NotificationTypes.GAME:
        return {
          label: 'Game Activities',
          description: 'Game achievements, challenges, and educational game updates',
          icon: <CheckCircle className="w-5 h-5" />,
          color: 'text-green-600'
        }
      case NotificationTypes.PARENT:
        return {
          label: 'Parent Communications',
          description: 'Messages from parents and family engagement activities',
          icon: <Mail className="w-5 h-5" />,
          color: 'text-pink-600'
        }
      case NotificationTypes.TEACHER:
        return {
          label: 'Teacher Messages',
          description: 'Direct messages and announcements from teachers',
          icon: <Mail className="w-5 h-5" />,
          color: 'text-orange-600'
        }
      case NotificationTypes.DISTRICT:
        return {
          label: 'District Announcements',
          description: 'School district news, policies, and important updates',
          icon: <AlertTriangle className="w-5 h-5" />,
          color: 'text-red-600'
        }
      case NotificationTypes.PAYMENT:
        return {
          label: 'Payment & Billing',
          description: 'Payment confirmations, billing reminders, and transaction updates',
          icon: <AlertTriangle className="w-5 h-5" />,
          color: 'text-yellow-600'
        }
      case NotificationTypes.SECURITY:
        return {
          label: 'Security Alerts',
          description: 'Login attempts, security warnings, and account protection',
          icon: <AlertTriangle className="w-5 h-5" />,
          color: 'text-red-600'
        }
      default:
        return {
          label: 'Notifications',
          description: 'General notifications',
          icon: <Bell className="w-5 h-5" />,
          color: 'text-gray-600'
        }
    }
  }

  const info = getTypeInfo()

  return (
    <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 mt-1 ${info.color}`}>
          {info.icon}
        </div>
        <div>
          <h3 className="font-medium text-gray-900 dark:text-white">
            {info.label}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            {info.description}
          </p>
        </div>
      </div>
      
      <button
        onClick={() => onToggle(type, !enabled)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          enabled ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
        }`}
        role="switch"
        aria-checked={enabled}
        aria-label={`Toggle ${info.label} notifications`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            enabled ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  )
}

interface TimePickerProps {
  value: string
  onChange: (time: string) => void
  label: string
}

function TimePicker({ value, onChange, label }: TimePickerProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {label}
      </label>
      <input
        type="time"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-800 dark:text-white"
      />
    </div>
  )
}

export function Preferences() {
  const { preferences, loading, error, updatePreferences } = useNotificationPreferences()
  const [localPreferences, setLocalPreferences] = useState<NotificationPreferencesType | null>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [saving, setSaving] = useState(false)

  // Initialize local preferences when data loads
  useEffect(() => {
    if (preferences && !localPreferences) {
      setLocalPreferences(preferences)
    }
  }, [preferences, localPreferences])

  const handleTypeToggle = (type: NotificationTypes, enabled: boolean) => {
    if (!localPreferences) return

    const updatedPreferences = {
      ...localPreferences,
      enabledTypes: enabled
        ? [...localPreferences.enabledTypes, type]
        : localPreferences.enabledTypes.filter(t => t !== type)
    }

    setLocalPreferences(updatedPreferences)
    setHasChanges(true)
  }

  const handleChannelToggle = (channel: keyof NotificationPreferencesType, enabled: boolean) => {
    if (!localPreferences) return

    setLocalPreferences({
      ...localPreferences,
      [channel]: enabled
    })
    setHasChanges(true)
  }

  const handleTimeChange = (field: 'digestTime' | 'quietStart' | 'quietEnd', time: string) => {
    if (!localPreferences) return

    setLocalPreferences({
      ...localPreferences,
      [field]: time
    })
    setHasChanges(true)
  }

  const handleSave = async () => {
    if (!localPreferences || !hasChanges) return

    setSaving(true)
    try {
      await updatePreferences(localPreferences)
      setHasChanges(false)
    } catch (err) {
      console.error('Failed to save preferences:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleReset = () => {
    if (preferences) {
      setLocalPreferences(preferences)
      setHasChanges(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center min-h-64">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
            <p className="text-gray-600 dark:text-gray-400">Loading preferences...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!localPreferences) {
    return (
      <div className="container mx-auto px-4 py-8">
        <Alert variant="destructive">
          <AlertTriangle className="w-4 h-4" />
          <AlertDescription>
            Failed to load notification preferences. Please try refreshing the page.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => window.history.back()}
              className="p-2"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              Notification Preferences
            </h1>
          </div>
          <p className="text-gray-600 dark:text-gray-400 ml-11">
            Customize how and when you receive notifications
          </p>
        </div>
        
        {hasChanges && (
          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={saving}
            >
              Reset
            </Button>
            <Button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center gap-2"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin" />}
              <Save className="w-4 h-4" />
              Save Changes
            </Button>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="w-4 h-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="channels" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="channels">Delivery Channels</TabsTrigger>
          <TabsTrigger value="types">Notification Types</TabsTrigger>
          <TabsTrigger value="schedule">Schedule & Timing</TabsTrigger>
          <TabsTrigger value="advanced">Advanced Settings</TabsTrigger>
        </TabsList>

        {/* Delivery Channels */}
        <TabsContent value="channels" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5" />
                Delivery Channels
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Real-time Notifications */}
              <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="flex items-start gap-3">
                  <Bell className="w-5 h-5 text-blue-600 mt-1" />
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      Real-time Notifications
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Instant toast notifications while using the platform
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleChannelToggle('enableInApp', !localPreferences.enableInApp)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    localPreferences.enableInApp ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                  role="switch"
                  aria-checked={localPreferences.enableInApp}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      localPreferences.enableInApp ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              {/* Push Notifications */}
              <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="flex items-start gap-3">
                  <Smartphone className="w-5 h-5 text-green-600 mt-1" />
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      Push Notifications
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Browser push notifications even when not on the site
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleChannelToggle('enablePush', !localPreferences.enablePush)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    localPreferences.enablePush ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                  role="switch"
                  aria-checked={localPreferences.enablePush}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      localPreferences.enablePush ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              {/* Email Notifications */}
              <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="flex items-start gap-3">
                  <Mail className="w-5 h-5 text-purple-600 mt-1" />
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      Email Notifications
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Important notifications sent to your email address
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleChannelToggle('enableEmail', !localPreferences.enableEmail)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    localPreferences.enableEmail ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                  role="switch"
                  aria-checked={localPreferences.enableEmail}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      localPreferences.enableEmail ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>

              {/* Sound Notifications */}
              <div className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <div className="flex items-start gap-3">
                  {localPreferences.enableSound ? (
                    <Volume2 className="w-5 h-5 text-orange-600 mt-1" />
                  ) : (
                    <VolumeX className="w-5 h-5 text-gray-400 mt-1" />
                  )}
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      Sound Notifications
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Play sounds when receiving notifications
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleChannelToggle('enableSound', !localPreferences.enableSound)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    localPreferences.enableSound ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
                  }`}
                  role="switch"
                  aria-checked={localPreferences.enableSound}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      localPreferences.enableSound ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notification Types */}
        <TabsContent value="types" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="w-5 h-5" />
                Notification Types
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.values(NotificationTypes).map((type) => (
                <NotificationTypeToggle
                  key={type}
                  type={type}
                  enabled={localPreferences.enabledTypes.includes(type)}
                  onToggle={handleTypeToggle}
                />
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Schedule & Timing */}
        <TabsContent value="schedule" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Daily Digest */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Sun className="w-5 h-5" />
                  Daily Digest
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      Enable Daily Digest
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Receive a summary of notifications each day
                    </p>
                  </div>
                  <button
                    onClick={() => handleChannelToggle('enableDigest', !localPreferences.enableDigest)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      localPreferences.enableDigest ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
                    }`}
                    role="switch"
                    aria-checked={localPreferences.enableDigest}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        localPreferences.enableDigest ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                {localPreferences.enableDigest && (
                  <TimePicker
                    value={localPreferences.digestTime}
                    onChange={(time) => handleTimeChange('digestTime', time)}
                    label="Digest Time"
                  />
                )}
              </CardContent>
            </Card>

            {/* Quiet Hours */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Moon className="w-5 h-5" />
                  Quiet Hours
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      Enable Quiet Hours
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Reduce notifications during specified hours
                    </p>
                  </div>
                  <button
                    onClick={() => handleChannelToggle('enableQuietHours', !localPreferences.enableQuietHours)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                      localPreferences.enableQuietHours ? 'bg-blue-600' : 'bg-gray-200 dark:bg-gray-700'
                    }`}
                    role="switch"
                    aria-checked={localPreferences.enableQuietHours}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        localPreferences.enableQuietHours ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                {localPreferences.enableQuietHours && (
                  <div className="grid grid-cols-2 gap-4">
                    <TimePicker
                      value={localPreferences.quietStart}
                      onChange={(time) => handleTimeChange('quietStart', time)}
                      label="Start Time"
                    />
                    <TimePicker
                      value={localPreferences.quietEnd}
                      onChange={(time) => handleTimeChange('quietEnd', time)}
                      label="End Time"
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Advanced Settings */}
        <TabsContent value="advanced" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="w-5 h-5" />
                Advanced Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Coming Soon */}
              <div className="text-center py-8">
                <Settings className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  Advanced Settings
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Additional notification customization options coming soon.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Save Changes Banner */}
      {hasChanges && (
        <div className="fixed bottom-4 right-4 bg-blue-600 text-white p-4 rounded-lg shadow-lg">
          <div className="flex items-center gap-3">
            <Info className="w-5 h-5" />
            <span>You have unsaved changes</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleSave}
              disabled={saving}
              className="text-white hover:bg-blue-700"
            >
              {saving && <Loader2 className="w-4 h-4 animate-spin mr-1" />}
              Save
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Preferences
