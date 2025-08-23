/**
 * LearnerEvidence Component (S5-09)
 *
 * Displays compliance evidence for a specific learner including consent history,
 * data protection requests, audit logs, and export/erase status.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Alert } from '@/components/ui/Alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import {
  User,
  Shield,
  Clock,
  Download,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock3,
  AlertCircle,
  FileText,
  History,
  Eye,
} from 'lucide-react'
import { EvidenceCard } from '../../components/compliance/EvidenceCard'
import { AuditTable } from '../../components/compliance/AuditTable'

// Types
interface ConsentRecord {
  id: string
  purpose: string
  granted_at: string
  revoked_at?: string
  status: string
  consent_type: string
  legal_basis: string
  expiry_date?: string
  version: string
}

interface DataProtectionRequest {
  id: string
  request_type: string
  status: string
  created_at: string
  completed_at?: string
  data_categories: string[]
  retention_policy: string
  processing_notes?: string
  compliance_status: string
}

interface AuditEvent {
  id: string
  timestamp: string
  event_type: string
  action: string
  resource: string
  actor: string
  outcome: string
  details: Record<string, any>
  risk_level: string
}

interface LearnerEvidence {
  learner_id: string
  consent_records: ConsentRecord[]
  data_protection_requests: DataProtectionRequest[]
  audit_events: AuditEvent[]
  last_updated: string
  active_consents: number
  revoked_consents: number
  pending_requests: number
  completed_requests: number
  compliance_score: number
  data_categories_processed: string[]
  retention_status: Record<string, string>
}

export const LearnerEvidence: React.FC = () => {
  const { learnerId } = useParams<{ learnerId: string }>()

  // State
  const [evidence, setEvidence] = useState<LearnerEvidence | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [dateRange] = useState(90) // days

  // Load learner evidence
  const loadEvidence = useCallback(
    async (showRefreshing = false) => {
      if (!learnerId) return

      try {
        if (showRefreshing) {
          setRefreshing(true)
        } else {
          setLoading(true)
        }
        setError(null)

        const response = await fetch(
          `/api/compliance-svc/evidence/learner/${learnerId}?days=${dateRange}`,
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
        console.error('Failed to load learner evidence:', err)
        setError(err.message || 'Failed to load compliance evidence')
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [learnerId, dateRange]
  )

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadEvidence(true)
  }, [loadEvidence])

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'granted':
      case 'completed':
      case 'active':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'revoked':
      case 'failed':
      case 'expired':
        return <XCircle className="h-4 w-4 text-red-600" />
      case 'pending':
      case 'processing':
        return <Clock3 className="h-4 w-4 text-yellow-600" />
      default:
        return <AlertCircle className="h-4 w-4 text-gray-600" />
    }
  }

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'granted':
      case 'completed':
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'revoked':
      case 'failed':
      case 'expired':
        return 'bg-red-100 text-red-800'
      case 'pending':
      case 'processing':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
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
          No compliance evidence found for this learner.
        </Alert>
      </div>
    )
  }

  return (
    <div className="p-6" data-testid="learner-evidence-page">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <User className="h-8 w-8 text-blue-600" />
            <h1 className="text-3xl font-bold">Learner Compliance Evidence</h1>
          </div>
          <p className="text-gray-600">
            Consent history, data protection requests, and audit trail for
            learner {learnerId}
          </p>
        </div>

        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={() => {
              // Export evidence report
              window.open(
                `/api/compliance-svc/evidence/learner/${learnerId}/export`,
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
          title="Compliance Score"
          value={`${Math.round(evidence.compliance_score * 100)}%`}
          subtitle="Overall compliance"
          icon={<Shield className="h-5 w-5" />}
          color={
            evidence.compliance_score >= 0.95
              ? 'success'
              : evidence.compliance_score >= 0.85
                ? 'warning'
                : 'error'
          }
          progress={evidence.compliance_score * 100}
        />

        <EvidenceCard
          title="Active Consents"
          value={evidence.active_consents.toString()}
          subtitle={`${evidence.revoked_consents} revoked`}
          icon={<CheckCircle className="h-5 w-5" />}
          color="success"
        />

        <EvidenceCard
          title="DP Requests"
          value={evidence.completed_requests.toString()}
          subtitle={`${evidence.pending_requests} pending`}
          icon={<FileText className="h-5 w-5" />}
          color={evidence.pending_requests > 0 ? 'warning' : 'success'}
        />

        <EvidenceCard
          title="Data Categories"
          value={evidence.data_categories_processed.length.toString()}
          subtitle="Categories processed"
          icon={<Eye className="h-5 w-5" />}
          color="info"
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="consent" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="consent" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            Consent Timeline
          </TabsTrigger>
          <TabsTrigger value="requests" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Data Protection
          </TabsTrigger>
          <TabsTrigger value="audit" className="flex items-center gap-2">
            <Eye className="h-4 w-4" />
            Audit Events
          </TabsTrigger>
          <TabsTrigger value="retention" className="flex items-center gap-2">
            <Clock className="h-4 w-4" />
            Retention Status
          </TabsTrigger>
        </TabsList>

        {/* Consent Timeline Tab */}
        <TabsContent value="consent" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5" />
                Consent History Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              {evidence.consent_records.length === 0 ? (
                <Alert className="text-blue-600 bg-blue-50 border-blue-200">
                  No consent records found.
                </Alert>
              ) : (
                <div className="space-y-6" data-testid="consent-timeline">
                  {evidence.consent_records
                    .sort(
                      (a, b) =>
                        new Date(b.granted_at).getTime() -
                        new Date(a.granted_at).getTime()
                    )
                    .map(consent => (
                      <div
                        key={consent.id}
                        className="flex gap-4 p-4 border rounded-lg hover:bg-gray-50"
                        data-testid="consent-timeline-item"
                      >
                        <div className="flex-shrink-0 mt-1">
                          {getStatusIcon(consent.status)}
                        </div>
                        <div className="flex-grow">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="font-medium">{consent.purpose}</h4>
                            <Badge className={getStatusColor(consent.status)}>
                              {consent.status.toUpperCase()}
                            </Badge>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                            <div>
                              <p className="text-sm text-gray-500">
                                Consent Type
                              </p>
                              <p className="text-sm">
                                {consent.consent_type
                                  .replace(/_/g, ' ')
                                  .replace(/\b\w/g, l => l.toUpperCase())}
                              </p>
                            </div>
                            <div>
                              <p className="text-sm text-gray-500">
                                Legal Basis
                              </p>
                              <p className="text-sm">
                                {consent.legal_basis
                                  .replace(/_/g, ' ')
                                  .replace(/\b\w/g, l => l.toUpperCase())}
                              </p>
                            </div>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                            <div>
                              <p className="text-gray-500">Granted</p>
                              <p>
                                {new Date(consent.granted_at).toLocaleString()}
                              </p>
                            </div>
                            {consent.revoked_at && (
                              <div>
                                <p className="text-gray-500">Revoked</p>
                                <p>
                                  {new Date(
                                    consent.revoked_at
                                  ).toLocaleString()}
                                </p>
                              </div>
                            )}
                            {consent.expiry_date && (
                              <div>
                                <p className="text-gray-500">Expires</p>
                                <p>
                                  {new Date(
                                    consent.expiry_date
                                  ).toLocaleDateString()}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Data Protection Requests Tab */}
        <TabsContent value="requests" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Data Protection Requests
              </CardTitle>
            </CardHeader>
            <CardContent>
              {evidence.data_protection_requests.length === 0 ? (
                <Alert className="text-blue-600 bg-blue-50 border-blue-200">
                  No data protection requests found.
                </Alert>
              ) : (
                <div className="space-y-4" data-testid="dp-requests-section">
                  {evidence.data_protection_requests
                    .sort(
                      (a, b) =>
                        new Date(b.created_at).getTime() -
                        new Date(a.created_at).getTime()
                    )
                    .map(request => (
                      <div key={request.id} className="border rounded-lg p-4">
                        <div className="flex justify-between items-start mb-4">
                          <div className="flex items-center gap-3">
                            {getStatusIcon(request.status)}
                            <h4 className="font-medium">
                              {request.request_type
                                .replace(/_/g, ' ')
                                .replace(/\b\w/g, l => l.toUpperCase())}
                            </h4>
                          </div>
                          <div className="flex items-center gap-3">
                            <Badge className={getStatusColor(request.status)}>
                              {request.status.toUpperCase()}
                            </Badge>
                            <span className="text-sm text-gray-500">
                              {new Date(
                                request.created_at
                              ).toLocaleDateString()}
                            </span>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          <div>
                            <h5 className="font-medium mb-2">
                              Request Details
                            </h5>
                            <div className="space-y-2 text-sm">
                              <div className="flex justify-between">
                                <span>Created:</span>
                                <span>
                                  {new Date(
                                    request.created_at
                                  ).toLocaleString()}
                                </span>
                              </div>
                              {request.completed_at && (
                                <div className="flex justify-between">
                                  <span>Completed:</span>
                                  <span>
                                    {new Date(
                                      request.completed_at
                                    ).toLocaleString()}
                                  </span>
                                </div>
                              )}
                              <div className="flex justify-between">
                                <span>Compliance Status:</span>
                                <Badge
                                  className={getStatusColor(
                                    request.compliance_status
                                  )}
                                >
                                  {request.compliance_status.toUpperCase()}
                                </Badge>
                              </div>
                            </div>
                          </div>

                          <div>
                            <h5 className="font-medium mb-2">
                              Data Categories
                            </h5>
                            <div className="flex flex-wrap gap-2 mb-4">
                              {request.data_categories.map(category => (
                                <Badge
                                  key={category}
                                  variant="outline"
                                  className="text-sm"
                                >
                                  {category.replace(/_/g, ' ')}
                                </Badge>
                              ))}
                            </div>

                            <p className="text-sm text-gray-600">
                              <span className="font-medium">
                                Retention Policy:
                              </span>{' '}
                              {request.retention_policy}
                            </p>

                            {request.processing_notes && (
                              <p className="text-sm text-gray-600 mt-2">
                                <span className="font-medium">Notes:</span>{' '}
                                {request.processing_notes}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Audit Events Tab */}
        <TabsContent value="audit" className="mt-6">
          <AuditTable
            events={evidence.audit_events}
            title="Learner Audit Events"
            showLearnerColumn={false}
          />
        </TabsContent>

        {/* Retention Status Tab */}
        <TabsContent value="retention" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Data Retention Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6"
                data-testid="retention-status"
              >
                {Object.entries(evidence.retention_status).map(
                  ([category, status]) => (
                    <Card key={category} className="border">
                      <CardContent className="p-4">
                        <h4 className="font-medium mb-2">
                          {category
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, l => l.toUpperCase())}
                        </h4>
                        <Badge className={getStatusColor(status)}>
                          {status.toUpperCase()}
                        </Badge>
                        <p className="text-sm text-gray-500 mt-2">
                          Current retention status for this data category
                        </p>
                      </CardContent>
                    </Card>
                  )
                )}
              </div>

              <div>
                <h4 className="font-medium mb-3">Processed Data Categories</h4>
                <div className="flex flex-wrap gap-2">
                  {evidence.data_categories_processed.map(category => (
                    <Badge key={category} variant="outline" className="text-sm">
                      {category
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, l => l.toUpperCase())}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
