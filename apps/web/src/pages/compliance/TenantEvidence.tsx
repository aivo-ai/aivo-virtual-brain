/**
 * TenantEvidence Component (S5-09)
 *
 * Displays compliance evidence for a specific tenant including isolation test
 * results, chaos engineering checks, and retention job status.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Alert } from '@/components/ui/Alert'
import { Shield, RefreshCw, Download, Eye, TrendingUp } from 'lucide-react'
import { EvidenceCard } from '../../components/compliance/EvidenceCard'

// Types
interface IsolationTestSummary {
  test_type: string
  total_tests: number
  passed_tests: number
  failed_tests: number
  pass_rate: number
  last_test_date: string
  average_duration: number
}

interface ChaosCheckResult {
  total: number
  passed: number
  failed: number
  last_run: string
}

interface RetentionJobStatus {
  last_retention_run: string
  next_scheduled_run: string
  items_processed: number
  items_deleted: number
  items_archived: number
  status: string
  compliance_policies: Record<string, string>
}

interface TenantEvidence {
  tenant_id: string
  isolation_tests: IsolationTestSummary[]
  chaos_checks: Record<string, ChaosCheckResult>
  retention_job_status: RetentionJobStatus
  last_updated: string
  overall_isolation_pass_rate: number
  total_isolation_tests: number
  failed_isolation_tests: number
  retention_compliance_score: number
}

export const TenantEvidence: React.FC = () => {
  const { tenantId } = useParams<{ tenantId: string }>()

  // State
  const [evidence, setEvidence] = useState<TenantEvidence | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedTest, setSelectedTest] = useState<IsolationTestSummary | null>(
    null
  )
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [dateRange] = useState(30) // days

  // Load tenant evidence
  const loadEvidence = useCallback(
    async (showRefreshing = false) => {
      if (!tenantId) return

      try {
        if (showRefreshing) {
          setRefreshing(true)
        } else {
          setLoading(true)
        }
        setError(null)

        const response = await fetch(
          `/api/compliance-svc/evidence/tenant/${tenantId}?days=${dateRange}`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
            },
          }
        )

        if (!response.ok) {
          throw new Error(`Failed to load evidence: ${response.statusText}`)
        }

        const data = await response.json()
        setEvidence(data)
      } catch (err: any) {
        console.error('Failed to load tenant evidence:', err)
        setError(err.message || 'Failed to load compliance evidence')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [tenantId, dateRange]
  )

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadEvidence(true)
  }, [loadEvidence])

  // Handle test details
  const handleViewTestDetails = useCallback((test: IsolationTestSummary) => {
    setSelectedTest(test)
    setDetailsOpen(true)
  }, [])

  // Get status color and icon
  const getStatusInfo = (passRate: number) => {
    if (passRate >= 0.95) {
      return { color: 'success', label: 'Excellent' }
    } else if (passRate >= 0.85) {
      return { color: 'warning', label: 'Good' }
    } else {
      return { color: 'error', label: 'Needs Attention' }
    }
  }

  // Format duration
  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`
    return `${Math.round((seconds / 3600) * 10) / 10}h`
  }

  // Load data on mount
  useEffect(() => {
    loadEvidence()
  }, [loadEvidence])

  if (loading) {
    return (
      <div className="p-6 flex flex-col items-center">
        <RefreshCw className="h-8 w-8 animate-spin mb-4" />
        <p className="text-gray-600">Loading compliance evidence...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <Alert className="mb-4 text-red-600 bg-red-50 border-red-200">
          {error}
        </Alert>
        <Button onClick={() => loadEvidence()}>Try Again</Button>
      </div>
    )
  }

  if (!evidence) {
    return (
      <div className="p-6">
        <Alert className="text-blue-600 bg-blue-50 border-blue-200">
          No compliance evidence found for this tenant.
        </Alert>
      </div>
    )
  }

  return (
    <div className="p-6" data-testid="tenant-evidence-page">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Shield className="h-8 w-8 text-blue-600" />
            <h1 className="text-3xl font-bold">Tenant Compliance Evidence</h1>
          </div>
          <p className="text-gray-600">
            Isolation tests, chaos checks, and retention compliance for tenant{' '}
            {tenantId}
          </p>
        </div>

        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => {
              // Export evidence report
              window.open(
                `/api/compliance-svc/evidence/tenant/${tenantId}/export`,
                '_blank'
              )
            }}
          >
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
          <Button onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw
              className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`}
            />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <EvidenceCard
          title="Isolation Pass Rate"
          value={`${Math.round(evidence.overall_isolation_pass_rate * 100)}%`}
          subtitle={`${evidence.total_isolation_tests} total tests`}
          icon={<Shield className="h-5 w-5" />}
          color={
            getStatusInfo(evidence.overall_isolation_pass_rate).color as any
          }
          progress={evidence.overall_isolation_pass_rate * 100}
        />

        <EvidenceCard
          title="Failed Tests"
          value={evidence.failed_isolation_tests.toString()}
          subtitle="Require attention"
          icon={<TrendingUp className="h-5 w-5" />}
          color={evidence.failed_isolation_tests > 0 ? 'error' : 'success'}
        />

        <EvidenceCard
          title="Retention Compliance"
          value={`${Math.round(evidence.retention_compliance_score * 100)}%`}
          subtitle="Policy adherence"
          icon={<Shield className="h-5 w-5" />}
          color={
            evidence.retention_compliance_score >= 0.95 ? 'success' : 'warning'
          }
          progress={evidence.retention_compliance_score * 100}
        />

        <EvidenceCard
          title="Last Updated"
          value={new Date(evidence.last_updated).toLocaleDateString()}
          subtitle={new Date(evidence.last_updated).toLocaleTimeString()}
          icon={<RefreshCw className="h-5 w-5" />}
          color="info"
        />
      </div>

      {/* Isolation Tests */}
      <Card className="mb-8">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Isolation Test Results
          </CardTitle>
        </CardHeader>
        <CardContent>
          {evidence.isolation_tests.length === 0 ? (
            <Alert className="text-blue-600 bg-blue-50 border-blue-200">
              No isolation tests found for the selected time period.
            </Alert>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-3 px-4">Test Type</th>
                    <th className="text-right py-3 px-4">Pass Rate</th>
                    <th className="text-right py-3 px-4">Passed/Total</th>
                    <th className="text-right py-3 px-4">Avg Duration</th>
                    <th className="text-right py-3 px-4">Last Run</th>
                    <th className="text-right py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {evidence.isolation_tests.map((test, index) => {
                    const statusInfo = getStatusInfo(test.pass_rate)
                    return (
                      <tr key={index} className="border-b hover:bg-gray-50">
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <Shield className="h-4 w-4" />
                            {test.test_type
                              .replace(/_/g, ' ')
                              .replace(/\b\w/g, l => l.toUpperCase())}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Progress
                              value={test.pass_rate * 100}
                              className="w-16 h-2"
                            />
                            <Badge
                              className={
                                statusInfo.color === 'success'
                                  ? 'bg-green-100 text-green-800'
                                  : statusInfo.color === 'warning'
                                    ? 'bg-yellow-100 text-yellow-800'
                                    : 'bg-red-100 text-red-800'
                              }
                            >
                              {Math.round(test.pass_rate * 100)}%
                            </Badge>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          {test.passed_tests}/{test.total_tests}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {formatDuration(test.average_duration)}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {new Date(test.last_test_date).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <div title="View Details">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleViewTestDetails(test)}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Chaos Engineering Checks */}
      <Card className="mb-8" data-testid="chaos-checks-section">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Chaos Engineering Checks
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Object.entries(evidence.chaos_checks).map(
              ([checkType, result]) => (
                <Card key={checkType} className="border">
                  <CardContent className="p-4">
                    <h4 className="font-medium mb-3">
                      {checkType
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, l => l.toUpperCase())}
                    </h4>

                    <div className="flex items-center gap-3 mb-3">
                      <Progress
                        value={(result.passed / result.total) * 100}
                        className="flex-1 h-2"
                      />
                      <span className="text-sm text-gray-600">
                        {result.passed}/{result.total}
                      </span>
                    </div>

                    <p className="text-sm text-gray-500">
                      Last run: {new Date(result.last_run).toLocaleDateString()}
                    </p>
                  </CardContent>
                </Card>
              )
            )}
          </div>
        </CardContent>
      </Card>

      {/* Retention Job Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            Retention Job Status
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-3">Job Status</h4>
              <Badge
                className={
                  evidence.retention_job_status.status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-yellow-100 text-yellow-800'
                }
              >
                {evidence.retention_job_status.status.toUpperCase()}
              </Badge>

              <div className="mt-4 space-y-2">
                <p className="text-sm text-gray-600">
                  Last run:{' '}
                  {new Date(
                    evidence.retention_job_status.last_retention_run
                  ).toLocaleString()}
                </p>
                <p className="text-sm text-gray-600">
                  Next run:{' '}
                  {new Date(
                    evidence.retention_job_status.next_scheduled_run
                  ).toLocaleString()}
                </p>
              </div>
            </div>

            <div>
              <h4 className="font-medium mb-3">Processing Summary</h4>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-sm">Items Processed:</span>
                  <span className="text-sm font-medium">
                    {evidence.retention_job_status.items_processed.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Items Deleted:</span>
                  <span className="text-sm font-medium">
                    {evidence.retention_job_status.items_deleted.toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm">Items Archived:</span>
                  <span className="text-sm font-medium">
                    {evidence.retention_job_status.items_archived.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6">
            <h4 className="font-medium mb-3">Compliance Policies</h4>
            <div className="flex flex-wrap gap-2">
              {Object.entries(
                evidence.retention_job_status.compliance_policies
              ).map(([policy, duration]) => (
                <Badge key={policy} variant="outline" className="text-sm">
                  {policy.replace(/_/g, ' ')}: {duration}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Test Details Modal */}
      {detailsOpen && selectedTest && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">
                  Isolation Test Details: {selectedTest.test_type}
                </h3>
                <Button
                  variant="ghost"
                  onClick={() => setDetailsOpen(false)}
                  className="p-2"
                >
                  ×
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium mb-3">Test Summary</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Total Tests:</span>
                      <span className="text-sm font-medium">
                        {selectedTest.total_tests}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Passed:</span>
                      <span className="text-sm font-medium text-green-600">
                        {selectedTest.passed_tests}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Failed:</span>
                      <span className="text-sm font-medium text-red-600">
                        {selectedTest.failed_tests}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Pass Rate:</span>
                      <span className="text-sm font-medium">
                        {Math.round(selectedTest.pass_rate * 100)}%
                      </span>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium mb-3">Performance</h4>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm">Average Duration:</span>
                      <span className="text-sm font-medium">
                        {formatDuration(selectedTest.average_duration)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm">Last Test:</span>
                      <span className="text-sm font-medium">
                        {new Date(selectedTest.last_test_date).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <Button onClick={() => setDetailsOpen(false)}>Close</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
