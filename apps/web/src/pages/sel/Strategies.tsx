/**
 * S3-13 SEL Strategies Page
 * Strategy board for SEL coping mechanisms and activities
 */

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../components/ui/Card'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { Alert, AlertDescription } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../../components/ui/Tabs'
import { StrategyCard } from '../../components/sel/StrategyCard'
import {
  SELStudent,
  SELStrategy,
  SELAlert,
  StrategyCategory,
  AlertType,
  useSELQueries,
  useSELMutations,
  getLocalizedCopy,
} from '../../api/selClient'
import {
  Search,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
} from '../../components/ui/Icons'

export function Strategies() {
  const { studentId } = useParams<{ studentId: string }>()
  const navigate = useNavigate()

  const [student, setStudent] = useState<SELStudent | null>(null)
  const [strategies, setStrategies] = useState<SELStrategy[]>([])
  const [filteredStrategies, setFilteredStrategies] = useState<SELStrategy[]>(
    []
  )
  const [activeAlerts, setActiveAlerts] = useState<SELAlert[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<
    StrategyCategory | 'ALL'
  >('ALL')
  const [sortBy, setSortBy] = useState<
    'recommended' | 'effectiveness' | 'recent' | 'duration'
  >('recommended')
  const [consentError, setConsentError] = useState<string | null>(null)

  const { getStudent, getStrategies, getActiveAlerts, loading, error } =
    useSELQueries()
  const { acknowledgeAlert, resolveAlert } = useSELMutations()

  useEffect(() => {
    if (studentId) {
      loadData()
    }
  }, [studentId])

  useEffect(() => {
    filterStrategies()
  }, [strategies, searchTerm, selectedCategory, sortBy])

  const loadData = async () => {
    if (!studentId) return

    try {
      const studentData = await getStudent(studentId)
      setStudent(studentData)

      // Check consent
      if (!studentData.selConsent.granted) {
        setConsentError(getLocalizedCopy('consent.required'))
        return
      }

      const [strategiesData, alertsData] = await Promise.all([
        getStrategies(studentData.gradeLevel),
        getActiveAlerts(studentId),
      ])

      setStrategies(strategiesData)
      setActiveAlerts(alertsData)
    } catch (err) {
      console.error('Failed to load data:', err)
    }
  }

  const filterStrategies = () => {
    let filtered = [...strategies]

    // Filter by search term
    if (searchTerm) {
      const term = searchTerm.toLowerCase()
      filtered = filtered.filter(
        strategy =>
          strategy.title.toLowerCase().includes(term) ||
          strategy.description.toLowerCase().includes(term) ||
          strategy.tags.some(tag => tag.toLowerCase().includes(term))
      )
    }

    // Filter by category
    if (selectedCategory !== 'ALL') {
      filtered = filtered.filter(
        strategy => strategy.category === selectedCategory
      )
    }

    // Sort strategies
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'recommended':
          if (a.isRecommended && !b.isRecommended) return -1
          if (!a.isRecommended && b.isRecommended) return 1
          return b.effectiveness - a.effectiveness
        case 'effectiveness':
          return b.effectiveness - a.effectiveness
        case 'recent':
          if (!a.lastUsed && !b.lastUsed) return 0
          if (!a.lastUsed) return 1
          if (!b.lastUsed) return -1
          return new Date(b.lastUsed).getTime() - new Date(a.lastUsed).getTime()
        case 'duration':
          return a.estimatedDuration - b.estimatedDuration
        default:
          return 0
      }
    })

    setFilteredStrategies(filtered)
  }

  const handleStrategyUse = (_strategy: SELStrategy) => {
    // Refresh strategies to update usage stats
    if (student) {
      getStrategies(student.gradeLevel).then(setStrategies)
    }
  }

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId, 'student')
      setActiveAlerts(prev =>
        prev.map(alert =>
          alert.id === alertId
            ? {
                ...alert,
                acknowledged: true,
                acknowledgedAt: new Date().toISOString(),
              }
            : alert
        )
      )
    } catch (err) {
      console.error('Failed to acknowledge alert:', err)
    }
  }

  const handleResolveAlert = async (alertId: string) => {
    try {
      await resolveAlert(alertId, 'student')
      setActiveAlerts(prev => prev.filter(alert => alert.id !== alertId))
    } catch (err) {
      console.error('Failed to resolve alert:', err)
    }
  }

  const getRecommendedStrategiesForAlerts = () => {
    const alertTypes = activeAlerts.map(alert => alert.alertType)

    return strategies
      .filter(strategy => {
        if (
          alertTypes.includes(AlertType.MOOD_LOW) &&
          strategy.category === StrategyCategory.MINDFULNESS
        )
          return true
        if (
          alertTypes.includes(AlertType.STRESS_HIGH) &&
          strategy.category === StrategyCategory.BREATHING
        )
          return true
        if (
          alertTypes.includes(AlertType.SOCIAL_ISOLATION) &&
          strategy.category === StrategyCategory.SOCIAL
        )
          return true
        if (
          alertTypes.includes(AlertType.ACADEMIC_STRUGGLE) &&
          strategy.category === StrategyCategory.COGNITIVE
        )
          return true
        if (
          alertTypes.includes(AlertType.ENERGY_CRASH) &&
          strategy.category === StrategyCategory.MOVEMENT
        )
          return true
        return false
      })
      .slice(0, 3)
  }

  if (loading || !student) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  const recommendedForAlerts = getRecommendedStrategiesForAlerts()

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {getLocalizedCopy('strategies.title')}
          </h1>
          <p className="text-gray-600 mt-1">
            Find strategies to help you feel better, {student.firstName}
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => navigate(`/sel/checkin/${studentId}`)}
        >
          Back to Check-in
        </Button>
      </div>

      {/* Consent Error */}
      {consentError && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {consentError}
            <Button
              variant="outline"
              size="sm"
              className="ml-2"
              onClick={() => navigate(`/consent/${studentId}`)}
            >
              Update Consent
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Error Message */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Active Alerts */}
      {activeAlerts.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">Active Alerts</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeAlerts.map(alert => (
              <Card key={alert.id} className="border-l-4 border-l-orange-500">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-sm font-medium text-orange-800">
                        {alert.alertType.replace('_', ' ')}
                      </CardTitle>
                      <Badge variant="outline" className="mt-1">
                        {alert.severity}
                      </Badge>
                    </div>
                    {!alert.acknowledged && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleAcknowledgeAlert(alert.id)}
                      >
                        Acknowledge
                      </Button>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <p className="text-sm text-gray-600 mb-3">{alert.message}</p>
                  <div className="flex gap-2">
                    {alert.acknowledged && (
                      <Button
                        size="sm"
                        onClick={() => handleResolveAlert(alert.id)}
                        className="flex items-center gap-1"
                      >
                        <CheckCircle className="w-3 h-3" />
                        Resolve
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Recommended strategies for alerts */}
          {recommendedForAlerts.length > 0 && (
            <div className="bg-blue-50 rounded-lg p-4">
              <h3 className="font-medium text-blue-900 mb-3">
                Recommended strategies based on your alerts:
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {recommendedForAlerts.map(strategy => (
                  <StrategyCard
                    key={strategy.id}
                    strategy={strategy}
                    studentId={studentId!}
                    onUse={handleStrategyUse}
                    className="bg-white"
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search strategies..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Category Filter */}
            <select
              value={selectedCategory}
              onChange={e =>
                setSelectedCategory(e.target.value as StrategyCategory | 'ALL')
              }
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="ALL">All Categories</option>
              {Object.values(StrategyCategory).map(category => (
                <option key={category} value={category}>
                  {category.replace('_', ' ')}
                </option>
              ))}
            </select>

            {/* Sort */}
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="recommended">Recommended</option>
              <option value="effectiveness">Most Effective</option>
              <option value="recent">Recently Used</option>
              <option value="duration">Shortest Duration</option>
            </select>

            {/* Refresh */}
            <Button
              variant="outline"
              onClick={loadData}
              className="flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Strategies Tabs */}
      <Tabs defaultValue="all" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="all">
            All Strategies ({filteredStrategies.length})
          </TabsTrigger>
          <TabsTrigger value="recommended">
            Recommended (
            {filteredStrategies.filter(s => s.isRecommended).length})
          </TabsTrigger>
          <TabsTrigger value="recent">
            Recently Used ({filteredStrategies.filter(s => s.lastUsed).length})
          </TabsTrigger>
          <TabsTrigger value="favorites">
            Highly Rated (
            {filteredStrategies.filter(s => s.effectiveness >= 4).length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          {filteredStrategies.length === 0 ? (
            <Card>
              <CardContent className="text-center py-8">
                <p className="text-gray-500">
                  No strategies found matching your criteria.
                </p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setSearchTerm('')
                    setSelectedCategory('ALL')
                  }}
                  className="mt-2"
                >
                  Clear Filters
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredStrategies.map(strategy => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  studentId={studentId!}
                  onUse={handleStrategyUse}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="recommended" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredStrategies
              .filter(strategy => strategy.isRecommended)
              .map(strategy => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  studentId={studentId!}
                  onUse={handleStrategyUse}
                />
              ))}
          </div>
        </TabsContent>

        <TabsContent value="recent" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredStrategies
              .filter(strategy => strategy.lastUsed)
              .map(strategy => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  studentId={studentId!}
                  onUse={handleStrategyUse}
                />
              ))}
          </div>
        </TabsContent>

        <TabsContent value="favorites" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredStrategies
              .filter(strategy => strategy.effectiveness >= 4)
              .map(strategy => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  studentId={studentId!}
                  onUse={handleStrategyUse}
                />
              ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Stats Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Your Strategy Stats</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {strategies.filter(s => s.timesUsed > 0).length}
              </div>
              <div className="text-sm text-gray-500">Strategies Tried</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {strategies.reduce((sum, s) => sum + s.timesUsed, 0)}
              </div>
              <div className="text-sm text-gray-500">Total Uses</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {strategies.filter(s => s.effectiveness >= 4).length}
              </div>
              <div className="text-sm text-gray-500">Highly Rated</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {strategies.filter(s => s.isRecommended).length}
              </div>
              <div className="text-sm text-gray-500">Recommended</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
