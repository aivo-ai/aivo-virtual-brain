/**
 * AuditTable Component (S5-09)
 *
 * Displays audit events in a paginated, filterable table with risk level
 * indicators, event type filtering, and detailed event information.
 */

import React, { useState, useMemo } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Alert } from '@/components/ui/Alert'
import {
  Search,
  Filter,
  Eye,
  ChevronDown,
  ChevronUp,
  Shield,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'

// Types
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
  learner_id?: string
  tenant_id?: string
}

interface AuditTableProps {
  events: AuditEvent[]
  title?: string
  showLearnerColumn?: boolean
  showTenantColumn?: boolean
  maxHeight?: number
  dense?: boolean
}

export const AuditTable: React.FC<AuditTableProps> = ({
  events,
  title = 'Audit Events',
  showLearnerColumn = true,
  showTenantColumn = true,
  maxHeight = 600,
}) => {
  // State
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [searchTerm, setSearchTerm] = useState('')
  const [eventTypeFilter, setEventTypeFilter] = useState('')
  const [riskLevelFilter, setRiskLevelFilter] = useState('')
  const [outcomeFilter, setOutcomeFilter] = useState('')
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null)
  const [detailsOpen, setDetailsOpen] = useState(false)
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set())
  const [showFilters, setShowFilters] = useState(false)

  // Get unique filter values
  const filterOptions = useMemo(() => {
    const eventTypes = [...new Set(events.map(e => e.event_type))].sort()
    const riskLevels = [...new Set(events.map(e => e.risk_level))].sort()
    const outcomes = [...new Set(events.map(e => e.outcome))].sort()

    return { eventTypes, riskLevels, outcomes }
  }, [events])

  // Filter and search events
  const filteredEvents = useMemo(() => {
    return events.filter(event => {
      const matchesSearch =
        !searchTerm ||
        event.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
        event.resource.toLowerCase().includes(searchTerm.toLowerCase()) ||
        event.actor.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesEventType =
        !eventTypeFilter || event.event_type === eventTypeFilter
      const matchesRiskLevel =
        !riskLevelFilter || event.risk_level === riskLevelFilter
      const matchesOutcome = !outcomeFilter || event.outcome === outcomeFilter

      return (
        matchesSearch && matchesEventType && matchesRiskLevel && matchesOutcome
      )
    })
  }, [events, searchTerm, eventTypeFilter, riskLevelFilter, outcomeFilter])

  // Paginated events
  const paginatedEvents = useMemo(() => {
    const startIndex = page * rowsPerPage
    return filteredEvents.slice(startIndex, startIndex + rowsPerPage)
  }, [filteredEvents, page, rowsPerPage])

  // Risk level styling
  const getRiskLevelConfig = (riskLevel: string) => {
    switch (riskLevel.toLowerCase()) {
      case 'critical':
        return {
          color: 'text-red-600',
          bg: 'bg-red-100',
          icon: AlertCircle,
        }
      case 'high':
        return {
          color: 'text-orange-600',
          bg: 'bg-orange-100',
          icon: AlertTriangle,
        }
      case 'medium':
        return {
          color: 'text-blue-600',
          bg: 'bg-blue-100',
          icon: Info,
        }
      case 'low':
        return {
          color: 'text-green-600',
          bg: 'bg-green-100',
          icon: CheckCircle,
        }
      default:
        return {
          color: 'text-gray-600',
          bg: 'bg-gray-100',
          icon: Info,
        }
    }
  }

  // Outcome styling
  const getOutcomeColor = (outcome: string) => {
    switch (outcome.toLowerCase()) {
      case 'success':
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'failure':
      case 'failed':
      case 'error':
        return 'bg-red-100 text-red-800'
      case 'pending':
      case 'in_progress':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  // Handle row expansion
  const handleRowToggle = (eventId: string) => {
    const newExpanded = new Set(expandedRows)
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId)
    } else {
      newExpanded.add(eventId)
    }
    setExpandedRows(newExpanded)
  }

  // Handle event details
  const handleViewDetails = (event: AuditEvent) => {
    setSelectedEvent(event)
    setDetailsOpen(true)
  }

  // Clear filters
  const clearFilters = () => {
    setSearchTerm('')
    setEventTypeFilter('')
    setRiskLevelFilter('')
    setOutcomeFilter('')
    setPage(0)
  }

  const totalPages = Math.ceil(filteredEvents.length / rowsPerPage)

  return (
    <Card className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Shield className="h-5 w-5" />
          {title}
        </h3>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className={showFilters ? 'bg-blue-50' : ''}
          >
            <Filter className="h-4 w-4" />
          </Button>
          {(searchTerm ||
            eventTypeFilter ||
            riskLevelFilter ||
            outcomeFilter) && (
            <Button size="sm" variant="outline" onClick={clearFilters}>
              Clear Filters
            </Button>
          )}
        </div>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-gray-50 p-4 rounded-lg mb-6 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search..."
              value={searchTerm}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setSearchTerm(e.target.value)
              }
              className="pl-10"
            />
          </div>

          <select
            value={eventTypeFilter}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
              setEventTypeFilter(e.target.value)
            }
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Event Types</option>
            {filterOptions.eventTypes.map(type => (
              <option key={type} value={type}>
                {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </option>
            ))}
          </select>

          <select
            value={riskLevelFilter}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
              setRiskLevelFilter(e.target.value)
            }
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Risk Levels</option>
            {filterOptions.riskLevels.map(level => (
              <option key={level} value={level}>
                {level.charAt(0).toUpperCase() + level.slice(1)}
              </option>
            ))}
          </select>

          <select
            value={outcomeFilter}
            onChange={(e: React.ChangeEvent<HTMLSelectElement>) =>
              setOutcomeFilter(e.target.value)
            }
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Outcomes</option>
            {filterOptions.outcomes.map(outcome => (
              <option key={outcome} value={outcome}>
                {outcome
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, l => l.toUpperCase())}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Results summary */}
      {filteredEvents.length !== events.length && (
        <Alert className="mb-4">
          Showing {filteredEvents.length} of {events.length} events
        </Alert>
      )}

      {/* Table */}
      <div
        className={cn(
          'overflow-x-auto',
          maxHeight && `max-h-[${maxHeight}px] overflow-y-auto`
        )}
      >
        <table className="w-full border-collapse">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <span className="sr-only">Expand</span>
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Timestamp
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Event Type
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Action
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Resource
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actor
              </th>
              {showLearnerColumn && (
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Learner
                </th>
              )}
              {showTenantColumn && (
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tenant
                </th>
              )}
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Risk Level
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Outcome
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedEvents.length === 0 ? (
              <tr>
                <td
                  colSpan={
                    10 +
                    (showLearnerColumn ? 1 : 0) +
                    (showTenantColumn ? 1 : 0)
                  }
                  className="px-4 py-8 text-center text-gray-500"
                >
                  No audit events found
                </td>
              </tr>
            ) : (
              paginatedEvents.map(event => {
                const riskConfig = getRiskLevelConfig(event.risk_level)
                const isExpanded = expandedRows.has(event.id)
                const RiskIcon = riskConfig.icon

                return (
                  <React.Fragment key={event.id}>
                    <tr className="hover:bg-gray-50">
                      <td className="px-4 py-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRowToggle(event.id)}
                        >
                          {isExpanded ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </Button>
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-900">
                        {new Date(event.timestamp).toLocaleString()}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-900">
                        {event.event_type
                          .replace(/_/g, ' ')
                          .replace(/\b\w/g, l => l.toUpperCase())}
                      </td>
                      <td className="px-4 py-4 text-sm font-medium text-gray-900">
                        {event.action}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-900">
                        {event.resource}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-900">
                        {event.actor}
                      </td>
                      {showLearnerColumn && (
                        <td className="px-4 py-4 text-sm text-gray-900">
                          {event.learner_id || '-'}
                        </td>
                      )}
                      {showTenantColumn && (
                        <td className="px-4 py-4 text-sm text-gray-900">
                          {event.tenant_id || '-'}
                        </td>
                      )}
                      <td className="px-4 py-4">
                        <Badge
                          className={cn(
                            riskConfig.bg,
                            riskConfig.color,
                            'flex items-center gap-1'
                          )}
                        >
                          <RiskIcon className="h-3 w-3" />
                          {event.risk_level.charAt(0).toUpperCase() +
                            event.risk_level.slice(1)}
                        </Badge>
                      </td>
                      <td className="px-4 py-4">
                        <Badge className={getOutcomeColor(event.outcome)}>
                          {event.outcome
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, l => l.toUpperCase())}
                        </Badge>
                      </td>
                      <td className="px-4 py-4 text-right">
                        <div title="View Details">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleViewDetails(event)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>

                    {/* Expanded row details */}
                    {isExpanded && (
                      <tr>
                        <td
                          colSpan={
                            10 +
                            (showLearnerColumn ? 1 : 0) +
                            (showTenantColumn ? 1 : 0)
                          }
                          className="px-4 py-4 bg-gray-50"
                        >
                          <div className="p-4 bg-white rounded border">
                            <h4 className="font-medium mb-3">Event Details</h4>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                              {Object.entries(event.details).map(
                                ([key, value]) => (
                                  <div key={key}>
                                    <dt className="text-sm font-medium text-gray-500">
                                      {key
                                        .replace(/_/g, ' ')
                                        .replace(/\b\w/g, l => l.toUpperCase())}
                                    </dt>
                                    <dd className="text-sm text-gray-900 mt-1">
                                      {typeof value === 'object'
                                        ? JSON.stringify(value, null, 2)
                                        : String(value)}
                                    </dd>
                                  </div>
                                )
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {filteredEvents.length > 0 && (
        <div className="flex items-center justify-between mt-6 pt-4 border-t">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-700">Rows per page:</span>
            <select
              value={rowsPerPage}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => {
                setRowsPerPage(parseInt(e.target.value))
                setPage(0)
              }}
              className="px-2 py-1 border border-gray-300 rounded text-sm"
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-700">
              {page * rowsPerPage + 1}-
              {Math.min((page + 1) * rowsPerPage, filteredEvents.length)} of{' '}
              {filteredEvents.length}
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page - 1)}
                disabled={page === 0}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(page + 1)}
                disabled={page >= totalPages - 1}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Event Details Modal */}
      {detailsOpen && selectedEvent && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Audit Event Details</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setDetailsOpen(false)}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium mb-3">Basic Information</h4>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-500">Event ID:</dt>
                      <dd className="text-sm font-mono">{selectedEvent.id}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-500">Timestamp:</dt>
                      <dd className="text-sm">
                        {new Date(selectedEvent.timestamp).toLocaleString()}
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-500">Event Type:</dt>
                      <dd className="text-sm">
                        {selectedEvent.event_type
                          .replace(/_/g, ' ')
                          .replace(/\b\w/g, l => l.toUpperCase())}
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-500">Action:</dt>
                      <dd className="text-sm font-medium">
                        {selectedEvent.action}
                      </dd>
                    </div>
                  </dl>
                </div>

                <div>
                  <h4 className="font-medium mb-3">Context</h4>
                  <dl className="space-y-2">
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-500">Resource:</dt>
                      <dd className="text-sm">{selectedEvent.resource}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-500">Actor:</dt>
                      <dd className="text-sm">{selectedEvent.actor}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-500">Risk Level:</dt>
                      <dd className="text-sm">
                        <Badge
                          className={cn(
                            getRiskLevelConfig(selectedEvent.risk_level).bg,
                            getRiskLevelConfig(selectedEvent.risk_level).color
                          )}
                        >
                          {selectedEvent.risk_level.charAt(0).toUpperCase() +
                            selectedEvent.risk_level.slice(1)}
                        </Badge>
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-sm text-gray-500">Outcome:</dt>
                      <dd className="text-sm">
                        <Badge
                          className={getOutcomeColor(selectedEvent.outcome)}
                        >
                          {selectedEvent.outcome
                            .replace(/_/g, ' ')
                            .replace(/\b\w/g, l => l.toUpperCase())}
                        </Badge>
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>

              <div className="mt-6">
                <h4 className="font-medium mb-3">Additional Details</h4>
                <pre className="bg-gray-50 p-4 rounded text-sm overflow-auto">
                  {JSON.stringify(selectedEvent.details, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
