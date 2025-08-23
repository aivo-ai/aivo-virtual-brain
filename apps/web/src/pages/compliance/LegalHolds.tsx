import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AlertCircle,
  Download,
  Eye,
  FileText,
  Gavel,
  Lock,
  Plus,
  Search,
  Shield,
  Users,
  Archive,
  Clock,
  CheckCircle,
  XCircle,
} from 'lucide-react'

interface LegalHold {
  id: string
  hold_number: string
  title: string
  description?: string
  case_number?: string
  legal_basis: string
  status: 'active' | 'released' | 'expired' | 'suspended'
  scope_type: string
  scope_parameters: Record<string, any>
  effective_date: string
  expiration_date?: string
  created_at: string
  affected_entities_count: number
  custodians_count: number
}

interface eDiscoveryExport {
  id: string
  export_number: string
  title: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'expired'
  progress_percentage: number
  total_records: number
  exported_records: number
  file_count: number
  total_size_bytes: number
  requested_date: string
  completed_date?: string
  archive_location?: string
}

interface AuditLog {
  id: string
  hold_id: string
  event_type: string
  event_description: string
  user_name?: string
  event_timestamp: string
  risk_level: string
  affected_entity_type?: string
  affected_entity_id?: string
}

const LegalHoldsPage: React.FC = () => {
  const [holds, setHolds] = useState<LegalHold[]>([])
  const [selectedHold, setSelectedHold] = useState<LegalHold | null>(null)
  const [exports, setExports] = useState<eDiscoveryExport[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showExportDialog, setShowExportDialog] = useState(false)
  const [activeTab, setActiveTab] = useState<'holds' | 'exports' | 'audit'>(
    'holds'
  )

  // New hold form state
  const [newHold, setNewHold] = useState({
    title: '',
    description: '',
    case_number: '',
    legal_basis: 'litigation',
    scope_type: 'tenant',
    scope_parameters: {},
    custodian_user_ids: [],
    notify_custodians: true,
  })

  // New export form state
  const [newExport, setNewExport] = useState({
    title: '',
    description: '',
    export_format: 'structured_json',
    include_metadata: true,
    include_system_logs: true,
    include_deleted_data: false,
    data_types: ['chat', 'audit', 'files'],
    requesting_attorney: '',
  })

  // Load legal holds
  const loadLegalHolds = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/legal-holds', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setHolds(data)
      }
    } catch (error) {
      console.error('Failed to load legal holds:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Load exports for selected hold
  const loadExports = async (holdId: string) => {
    try {
      const response = await fetch(`/api/v1/ediscovery/${holdId}/exports`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setExports(data)
      }
    } catch (error) {
      console.error('Failed to load exports:', error)
    }
  }

  // Load audit logs for selected hold
  const loadAuditLogs = async (holdId: string) => {
    try {
      const response = await fetch(`/api/v1/audit/holds/${holdId}/logs`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
      })

      if (response.ok) {
        const data = await response.json()
        setAuditLogs(data)
      }
    } catch (error) {
      console.error('Failed to load audit logs:', error)
    }
  }

  // Create new legal hold
  const createLegalHold = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/legal-holds', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify(newHold),
      })

      if (response.ok) {
        const createdHold = await response.json()
        setHolds(prev => [createdHold, ...prev])
        setShowCreateDialog(false)
        setNewHold({
          title: '',
          description: '',
          case_number: '',
          legal_basis: 'litigation',
          scope_type: 'tenant',
          scope_parameters: {},
          custodian_user_ids: [],
          notify_custodians: true,
        })
      }
    } catch (error) {
      console.error('Failed to create legal hold:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Create eDiscovery export
  const createExport = async () => {
    if (!selectedHold) return

    setIsLoading(true)
    try {
      const response = await fetch(
        `/api/v1/ediscovery/${selectedHold.id}/exports`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
          },
          body: JSON.stringify(newExport),
        }
      )

      if (response.ok) {
        const createdExport = await response.json()
        setExports(prev => [createdExport, ...prev])
        setShowExportDialog(false)
        setNewExport({
          title: '',
          description: '',
          export_format: 'structured_json',
          include_metadata: true,
          include_system_logs: true,
          include_deleted_data: false,
          data_types: ['chat', 'audit', 'files'],
          requesting_attorney: '',
        })
      }
    } catch (error) {
      console.error('Failed to create export:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Release legal hold
  const releaseHold = async (holdId: string) => {
    try {
      const response = await fetch(`/api/v1/legal-holds/${holdId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify({ status: 'released' }),
      })

      if (response.ok) {
        await loadLegalHolds()
      }
    } catch (error) {
      console.error('Failed to release hold:', error)
    }
  }

  // Filter holds
  const filteredHolds = holds.filter(hold => {
    const matchesSearch =
      hold.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      hold.case_number?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      hold.hold_number.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesStatus = statusFilter === 'all' || hold.status === statusFilter

    return matchesSearch && matchesStatus
  })

  // Get status badge color
  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'active':
        return 'destructive'
      case 'released':
        return 'secondary'
      case 'expired':
        return 'outline'
      case 'suspended':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  // Get export status badge color
  const getExportStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'completed':
        return 'default'
      case 'in_progress':
        return 'secondary'
      case 'pending':
        return 'outline'
      case 'failed':
        return 'destructive'
      default:
        return 'outline'
    }
  }

  // Format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  useEffect(() => {
    loadLegalHolds()
  }, [])

  useEffect(() => {
    if (selectedHold) {
      if (activeTab === 'exports') {
        loadExports(selectedHold.id)
      } else if (activeTab === 'audit') {
        loadAuditLogs(selectedHold.id)
      }
    }
  }, [selectedHold, activeTab])

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Gavel className="h-8 w-8" />
          Legal Holds & eDiscovery
        </h1>
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Create Legal Hold
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create New Legal Hold</DialogTitle>
              <DialogDescription>
                Create a legal preservation hold to suspend data deletion and
                retention policies.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="title">Title *</Label>
                  <Input
                    id="title"
                    value={newHold.title}
                    onChange={e =>
                      setNewHold(prev => ({ ...prev, title: e.target.value }))
                    }
                    placeholder="Enter hold title"
                  />
                </div>
                <div>
                  <Label htmlFor="case_number">Case Number</Label>
                  <Input
                    id="case_number"
                    value={newHold.case_number}
                    onChange={e =>
                      setNewHold(prev => ({
                        ...prev,
                        case_number: e.target.value,
                      }))
                    }
                    placeholder="CASE-2025-001"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={newHold.description}
                  onChange={e =>
                    setNewHold(prev => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  placeholder="Describe the reason for this legal hold"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="legal_basis">Legal Basis</Label>
                  <Select
                    value={newHold.legal_basis}
                    onValueChange={value =>
                      setNewHold(prev => ({ ...prev, legal_basis: value }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="litigation">Litigation</SelectItem>
                      <SelectItem value="investigation">
                        Investigation
                      </SelectItem>
                      <SelectItem value="regulatory">Regulatory</SelectItem>
                      <SelectItem value="compliance">Compliance</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="scope_type">Scope Type</Label>
                  <Select
                    value={newHold.scope_type}
                    onValueChange={value =>
                      setNewHold(prev => ({ ...prev, scope_type: value }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="tenant">Entire Tenant</SelectItem>
                      <SelectItem value="learner">Specific Learner</SelectItem>
                      <SelectItem value="teacher">Specific Teacher</SelectItem>
                      <SelectItem value="classroom">Classroom</SelectItem>
                      <SelectItem value="timerange">Time Range</SelectItem>
                      <SelectItem value="custom">Custom Scope</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setShowCreateDialog(false)}
              >
                Cancel
              </Button>
              <Button
                onClick={createLegalHold}
                disabled={!newHold.title || isLoading}
              >
                Create Hold
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Legal Holds List */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Legal Holds
              </CardTitle>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Search className="h-4 w-4 absolute left-3 top-3 text-gray-400" />
                  <Input
                    placeholder="Search holds..."
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="released">Released</SelectItem>
                    <SelectItem value="expired">Expired</SelectItem>
                    <SelectItem value="suspended">Suspended</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {filteredHolds.map(hold => (
                  <div
                    key={hold.id}
                    className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                      selectedHold?.id === hold.id
                        ? 'border-blue-500 bg-blue-50'
                        : 'hover:bg-gray-50'
                    }`}
                    onClick={() => setSelectedHold(hold)}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="font-medium">{hold.title}</h3>
                          <Badge variant={getStatusBadgeVariant(hold.status)}>
                            {hold.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 mb-2">
                          {hold.hold_number} •{' '}
                          {hold.case_number && `Case: ${hold.case_number}`}
                        </p>
                        <div className="flex items-center gap-4 text-xs text-gray-500">
                          <span className="flex items-center gap-1">
                            <Users className="h-3 w-3" />
                            {hold.custodians_count} custodians
                          </span>
                          <span className="flex items-center gap-1">
                            <Lock className="h-3 w-3" />
                            {hold.affected_entities_count} entities
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {new Date(hold.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={e => {
                            e.stopPropagation()
                            setSelectedHold(hold)
                            setActiveTab('exports')
                          }}
                        >
                          <Download className="h-3 w-3" />
                        </Button>
                        {hold.status === 'active' && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={e => {
                              e.stopPropagation()
                              releaseHold(hold.id)
                            }}
                          >
                            Release
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {filteredHolds.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    No legal holds found matching your criteria.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Hold Details Panel */}
        <div>
          {selectedHold ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">{selectedHold.title}</CardTitle>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant={activeTab === 'holds' ? 'default' : 'outline'}
                    onClick={() => setActiveTab('holds')}
                  >
                    Details
                  </Button>
                  <Button
                    size="sm"
                    variant={activeTab === 'exports' ? 'default' : 'outline'}
                    onClick={() => setActiveTab('exports')}
                  >
                    Exports
                  </Button>
                  <Button
                    size="sm"
                    variant={activeTab === 'audit' ? 'default' : 'outline'}
                    onClick={() => setActiveTab('audit')}
                  >
                    Audit
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {activeTab === 'holds' && (
                  <div className="space-y-4">
                    <div>
                      <Label className="text-sm font-medium">Hold Number</Label>
                      <p className="text-sm">{selectedHold.hold_number}</p>
                    </div>

                    {selectedHold.case_number && (
                      <div>
                        <Label className="text-sm font-medium">
                          Case Number
                        </Label>
                        <p className="text-sm">{selectedHold.case_number}</p>
                      </div>
                    )}

                    <div>
                      <Label className="text-sm font-medium">Legal Basis</Label>
                      <p className="text-sm capitalize">
                        {selectedHold.legal_basis}
                      </p>
                    </div>

                    <div>
                      <Label className="text-sm font-medium">Scope</Label>
                      <p className="text-sm capitalize">
                        {selectedHold.scope_type}
                      </p>
                    </div>

                    <div>
                      <Label className="text-sm font-medium">
                        Effective Date
                      </Label>
                      <p className="text-sm">
                        {new Date(selectedHold.effective_date).toLocaleString()}
                      </p>
                    </div>

                    {selectedHold.description && (
                      <div>
                        <Label className="text-sm font-medium">
                          Description
                        </Label>
                        <p className="text-sm">{selectedHold.description}</p>
                      </div>
                    )}
                  </div>
                )}

                {activeTab === 'exports' && (
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <h4 className="font-medium">eDiscovery Exports</h4>
                      <Dialog
                        open={showExportDialog}
                        onOpenChange={setShowExportDialog}
                      >
                        <DialogTrigger asChild>
                          <Button size="sm">
                            <Plus className="h-3 w-3 mr-1" />
                            New Export
                          </Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Create eDiscovery Export</DialogTitle>
                            <DialogDescription>
                              Export data for legal discovery and compliance
                              review.
                            </DialogDescription>
                          </DialogHeader>
                          <div className="space-y-4">
                            <div>
                              <Label htmlFor="export_title">Title *</Label>
                              <Input
                                id="export_title"
                                value={newExport.title}
                                onChange={e =>
                                  setNewExport(prev => ({
                                    ...prev,
                                    title: e.target.value,
                                  }))
                                }
                                placeholder="Export title"
                              />
                            </div>

                            <div>
                              <Label htmlFor="export_format">Format</Label>
                              <Select
                                value={newExport.export_format}
                                onValueChange={value =>
                                  setNewExport(prev => ({
                                    ...prev,
                                    export_format: value,
                                  }))
                                }
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  <SelectItem value="structured_json">
                                    Structured JSON
                                  </SelectItem>
                                  <SelectItem value="pst">
                                    PST Archive
                                  </SelectItem>
                                  <SelectItem value="pdf">
                                    PDF Report
                                  </SelectItem>
                                  <SelectItem value="native">
                                    Native Format
                                  </SelectItem>
                                </SelectContent>
                              </Select>
                            </div>

                            <div>
                              <Label htmlFor="requesting_attorney">
                                Requesting Attorney
                              </Label>
                              <Input
                                id="requesting_attorney"
                                value={newExport.requesting_attorney}
                                onChange={e =>
                                  setNewExport(prev => ({
                                    ...prev,
                                    requesting_attorney: e.target.value,
                                  }))
                                }
                                placeholder="Attorney name"
                              />
                            </div>
                          </div>
                          <DialogFooter>
                            <Button
                              variant="outline"
                              onClick={() => setShowExportDialog(false)}
                            >
                              Cancel
                            </Button>
                            <Button
                              onClick={createExport}
                              disabled={!newExport.title || isLoading}
                            >
                              Create Export
                            </Button>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>
                    </div>

                    <div className="space-y-3">
                      {exports.map(exportItem => (
                        <div key={exportItem.id} className="p-3 border rounded">
                          <div className="flex items-center justify-between mb-2">
                            <h5 className="font-medium">{exportItem.title}</h5>
                            <Badge
                              variant={getExportStatusBadgeVariant(
                                exportItem.status
                              )}
                            >
                              {exportItem.status}
                            </Badge>
                          </div>
                          <div className="text-xs text-gray-500 space-y-1">
                            <p>Export: {exportItem.export_number}</p>
                            <p>
                              Records: {exportItem.exported_records}/
                              {exportItem.total_records}
                            </p>
                            <p>
                              Size:{' '}
                              {formatFileSize(exportItem.total_size_bytes)}
                            </p>
                            {exportItem.status === 'in_progress' && (
                              <div className="w-full bg-gray-200 rounded-full h-2">
                                <div
                                  className="bg-blue-600 h-2 rounded-full"
                                  style={{
                                    width: `${exportItem.progress_percentage}%`,
                                  }}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      ))}

                      {exports.length === 0 && (
                        <p className="text-sm text-gray-500 text-center py-4">
                          No exports created yet.
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {activeTab === 'audit' && (
                  <div className="space-y-4">
                    <h4 className="font-medium">Audit Trail</h4>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {auditLogs.map(log => (
                        <div
                          key={log.id}
                          className="p-2 border rounded text-xs"
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium">
                              {log.event_type}
                            </span>
                            <Badge
                              variant={
                                log.risk_level === 'high'
                                  ? 'destructive'
                                  : log.risk_level === 'medium'
                                    ? 'secondary'
                                    : 'outline'
                              }
                              className="text-xs"
                            >
                              {log.risk_level}
                            </Badge>
                          </div>
                          <p className="text-gray-600 mb-1">
                            {log.event_description}
                          </p>
                          <div className="flex justify-between text-gray-500">
                            <span>{log.user_name}</span>
                            <span>
                              {new Date(log.event_timestamp).toLocaleString()}
                            </span>
                          </div>
                        </div>
                      ))}

                      {auditLogs.length === 0 && (
                        <p className="text-sm text-gray-500 text-center py-4">
                          No audit logs available.
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="text-center py-12">
                <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">
                  Select a legal hold to view details, exports, and audit logs.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

export default LegalHoldsPage
