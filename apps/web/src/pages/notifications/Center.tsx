/**
 * S3-14 Notifications Center
 * Central hub for viewing and managing notifications
 */

import { useState, useMemo } from 'react'
import { useNotifications, NotificationItem, NotificationTypes, NotificationCategory, NotificationPriority } from '../../api/notificationClient'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Badge } from '../../components/ui/Badge'
import { Alert, AlertDescription } from '../../components/ui/Alert'
import { Input } from '../../components/ui/Input'
import { 
  BellOff,
  CheckCircle,
  XCircle,
  Search,
  Filter,
  Trash2,
  ExternalLink,
  RefreshCw,
  Settings,
  Clock,
  AlertTriangle,
  Info,
  Loader2
} from '../../components/ui/Icons'

interface NotificationCardProps {
  notification: NotificationItem
  onMarkAsRead: (id: string) => void
  onDelete: (id: string) => void
}

function NotificationCard({ notification, onMarkAsRead, onDelete }: NotificationCardProps) {
  const getIcon = () => {
    switch (notification.category) {
      case NotificationCategory.SUCCESS:
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case NotificationCategory.WARNING:
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      case NotificationCategory.ERROR:
      case NotificationCategory.ALERT:
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <Info className="w-5 h-5 text-blue-500" />
    }
  }

  const getPriorityBadge = () => {
    const variant = notification.priority === NotificationPriority.URGENT ? 'destructive' :
                   notification.priority === NotificationPriority.HIGH ? 'warning' :
                   notification.priority === NotificationPriority.MEDIUM ? 'default' : 'secondary'
    
    return (
      <Badge variant={variant} size="sm">
        {notification.priority.toLowerCase()}
      </Badge>
    )
  }

  const getTypeBadge = () => {
    const typeColors = {
      [NotificationTypes.SYSTEM]: 'bg-gray-100 text-gray-800',
      [NotificationTypes.ACADEMIC]: 'bg-blue-100 text-blue-800',
      [NotificationTypes.SOCIAL]: 'bg-teal-100 text-teal-800',
      [NotificationTypes.REMINDER]: 'bg-amber-100 text-amber-800',
      [NotificationTypes.ALERT]: 'bg-red-100 text-red-800',
      [NotificationTypes.SEL]: 'bg-purple-100 text-purple-800',
      [NotificationTypes.ASSESSMENT]: 'bg-indigo-100 text-indigo-800',
      [NotificationTypes.GAME]: 'bg-green-100 text-green-800',
      [NotificationTypes.PARENT]: 'bg-pink-100 text-pink-800',
      [NotificationTypes.TEACHER]: 'bg-orange-100 text-orange-800',
      [NotificationTypes.DISTRICT]: 'bg-red-100 text-red-800',
      [NotificationTypes.PAYMENT]: 'bg-yellow-100 text-yellow-800',
      [NotificationTypes.SECURITY]: 'bg-red-100 text-red-800'
    }

    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${typeColors[notification.type]}`}>
        {notification.type.toLowerCase()}
      </span>
    )
  }

  const handleAction = () => {
    if (notification.actionUrl) {
      if (notification.actionUrl.startsWith('/')) {
        window.location.href = notification.actionUrl
      } else {
        window.open(notification.actionUrl, '_blank', 'noopener,noreferrer')
      }
    }
  }

  const isExpired = notification.expiresAt && new Date(notification.expiresAt) < new Date()

  return (
    <Card className={`${notification.isRead ? 'bg-gray-50 dark:bg-gray-800' : 'bg-white dark:bg-gray-900'} ${isExpired ? 'opacity-60' : ''}`}>
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 mt-1">
            {getIcon()}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1">
                <h3 className={`text-sm font-semibold ${notification.isRead ? 'text-gray-600 dark:text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                  {notification.title}
                </h3>
                <p className={`mt-1 text-sm ${notification.isRead ? 'text-gray-500 dark:text-gray-500' : 'text-gray-700 dark:text-gray-300'}`}>
                  {notification.message}
                </p>
              </div>
              
              <div className="flex flex-col items-end gap-2">
                {getPriorityBadge()}
                {getTypeBadge()}
              </div>
            </div>
            
            <div className="flex items-center justify-between mt-3">
              <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <Clock className="w-3 h-3" />
                <time dateTime={notification.createdAt}>
                  {new Date(notification.createdAt).toLocaleString()}
                </time>
                {isExpired && (
                  <Badge variant="outline" size="sm" className="text-red-600 border-red-200">
                    Expired
                  </Badge>
                )}
              </div>
              
              <div className="flex items-center gap-1">
                {notification.actionUrl && notification.actionLabel && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleAction}
                    className="h-7 px-2 text-blue-600 hover:text-blue-800"
                  >
                    {notification.actionLabel}
                    <ExternalLink className="w-3 h-3 ml-1" />
                  </Button>
                )}
                
                {!notification.isRead && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onMarkAsRead(notification.id)}
                    className="h-7 px-2"
                    title="Mark as read"
                  >
                    <CheckCircle className="w-4 h-4" />
                  </Button>
                )}
                
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDelete(notification.id)}
                  className="h-7 px-2 text-red-600 hover:text-red-800"
                  title="Delete notification"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function Center() {
  const { notifications, loading, error, unreadCount, markAsRead, deleteNotification, markAllAsRead, refetch } = useNotifications()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedType, setSelectedType] = useState<NotificationTypes | 'all'>('all')
  const [selectedCategory, setSelectedCategory] = useState<NotificationCategory | 'all'>('all')
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)

  // Filter notifications
  const filteredNotifications = useMemo(() => {
    return notifications.filter(notification => {
      // Search filter
      if (searchTerm) {
        const searchLower = searchTerm.toLowerCase()
        if (!notification.title.toLowerCase().includes(searchLower) && 
            !notification.message.toLowerCase().includes(searchLower)) {
          return false
        }
      }

      // Type filter
      if (selectedType !== 'all' && notification.type !== selectedType) {
        return false
      }

      // Category filter
      if (selectedCategory !== 'all' && notification.category !== selectedCategory) {
        return false
      }

      // Unread filter
      if (showUnreadOnly && notification.isRead) {
        return false
      }

      return true
    })
  }, [notifications, searchTerm, selectedType, selectedCategory, showUnreadOnly])

  const handleRefresh = () => {
    refetch()
  }

  if (loading && notifications.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center min-h-64">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-500" />
            <p className="text-gray-600 dark:text-gray-400">Loading notifications...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Notifications
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Stay updated with your latest notifications
            {unreadCount > 0 && (
              <Badge variant="destructive" className="ml-2">
                {unreadCount} unread
              </Badge>
            )}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          
          <Button
            variant="outline"
            onClick={() => window.location.href = '/notifications/preferences'}
            className="flex items-center gap-2"
          >
            <Settings className="w-4 h-4" />
            Settings
          </Button>
          
          {unreadCount > 0 && (
            <Button
              onClick={markAllAsRead}
              className="flex items-center gap-2"
            >
              <CheckCircle className="w-4 h-4" />
              Mark All Read
            </Button>
          )}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="w-4 h-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search notifications..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Type Filter */}
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value as NotificationTypes | 'all')}
              className="px-3 py-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-800"
            >
              <option value="all">All Types</option>
              {Object.values(NotificationTypes).map(type => (
                <option key={type} value={type}>
                  {type.toLowerCase().replace('_', ' ')}
                </option>
              ))}
            </select>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as NotificationCategory | 'all')}
              className="px-3 py-2 border border-gray-300 rounded-md dark:border-gray-600 dark:bg-gray-800"
            >
              <option value="all">All Categories</option>
              {Object.values(NotificationCategory).map(category => (
                <option key={category} value={category}>
                  {category.toLowerCase()}
                </option>
              ))}
            </select>

            {/* Unread Filter */}
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={showUnreadOnly}
                onChange={(e) => setShowUnreadOnly(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">Unread only</span>
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Notifications List */}
      {filteredNotifications.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <BellOff className="w-12 h-12 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                No notifications found
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                {searchTerm || selectedType !== 'all' || selectedCategory !== 'all' || showUnreadOnly
                  ? 'Try adjusting your filters to see more notifications.'
                  : 'You\'re all caught up! New notifications will appear here.'
                }
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredNotifications.map((notification) => (
            <NotificationCard
              key={notification.id}
              notification={notification}
              onMarkAsRead={markAsRead}
              onDelete={deleteNotification}
            />
          ))}
        </div>
      )}

      {/* Load More */}
      {filteredNotifications.length > 0 && filteredNotifications.length % 50 === 0 && (
        <div className="mt-8 text-center">
          <Button
            variant="outline"
            onClick={() => refetch()}
            disabled={loading}
            className="flex items-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Load More
          </Button>
        </div>
      )}
    </div>
  )
}

export default Center
