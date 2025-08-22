import { useTranslation } from 'react-i18next'
import {
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  FileText,
  Users,
  Edit3,
  Eye,
} from 'lucide-react'

import { Badge } from '@/components/ui/Badge'

type IEPStatus =
  | 'draft'
  | 'proposed'
  | 'pending_approval'
  | 'approved'
  | 'rejected'
  | 'active'

interface StatusChipsProps {
  status: IEPStatus
  metadata: {
    createdAt: string
    updatedAt: string
    createdBy: string
    proposedAt?: string
    proposedBy?: string
    submittedAt?: string
    submittedBy?: string
    reviewedAt?: string
    reviewedBy?: string
  }
  className?: string
}

export function StatusChips({
  status,
  metadata,
  className = '',
}: StatusChipsProps) {
  const { t } = useTranslation()

  const getStatusConfig = (status: IEPStatus) => {
    switch (status) {
      case 'draft':
        return {
          icon: Edit3,
          label: t('iep.status.draft'),
          variant: 'secondary' as const,
          className: 'bg-gray-100 text-gray-800 border-gray-300',
          ariaLabel: t('iep.status.draft_aria'),
        }
      case 'proposed':
        return {
          icon: FileText,
          label: t('iep.status.proposed'),
          variant: 'secondary' as const,
          className: 'bg-blue-50 text-blue-700 border-blue-300',
          ariaLabel: t('iep.status.proposed_aria'),
        }
      case 'pending_approval':
        return {
          icon: Clock,
          label: t('iep.status.pending_approval'),
          variant: 'warning' as const,
          className: 'bg-amber-50 text-amber-700 border-amber-300',
          ariaLabel: t('iep.status.pending_approval_aria'),
        }
      case 'approved':
        return {
          icon: CheckCircle,
          label: t('iep.status.approved'),
          variant: 'success' as const,
          className: 'bg-green-50 text-green-700 border-green-300',
          ariaLabel: t('iep.status.approved_aria'),
        }
      case 'rejected':
        return {
          icon: XCircle,
          label: t('iep.status.rejected'),
          variant: 'danger' as const,
          className: 'bg-red-50 text-red-700 border-red-300',
          ariaLabel: t('iep.status.rejected_aria'),
        }
      case 'active':
        return {
          icon: CheckCircle,
          label: t('iep.status.active'),
          variant: 'default' as const,
          className: 'bg-emerald-50 text-emerald-700 border-emerald-300',
          ariaLabel: t('iep.status.active_aria'),
        }
      default:
        return {
          icon: AlertCircle,
          label: t('iep.status.unknown'),
          variant: 'secondary' as const,
          className: 'bg-gray-100 text-gray-800 border-gray-300',
          ariaLabel: t('iep.status.unknown_aria'),
        }
    }
  }

  const config = getStatusConfig(status)
  const Icon = config.icon

  const getTimestamp = () => {
    switch (status) {
      case 'proposed':
        return metadata.proposedAt
          ? new Date(metadata.proposedAt)
          : new Date(metadata.updatedAt)
      case 'pending_approval':
        return metadata.submittedAt
          ? new Date(metadata.submittedAt)
          : new Date(metadata.updatedAt)
      case 'approved':
      case 'rejected':
      case 'active':
        return metadata.reviewedAt
          ? new Date(metadata.reviewedAt)
          : new Date(metadata.updatedAt)
      default:
        return new Date(metadata.updatedAt)
    }
  }

  const getActor = () => {
    switch (status) {
      case 'proposed':
        return metadata.proposedBy || metadata.createdBy
      case 'pending_approval':
        return metadata.submittedBy || metadata.createdBy
      case 'approved':
      case 'rejected':
      case 'active':
        return metadata.reviewedBy || metadata.createdBy
      default:
        return metadata.createdBy
    }
  }

  const timestamp = getTimestamp()
  const actor = getActor()

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      {/* Main Status Badge */}
      <Badge
        variant={config.variant}
        className={`flex items-center space-x-1.5 px-3 py-1.5 text-sm font-medium ${config.className}`}
        aria-label={config.ariaLabel}
      >
        <Icon className="h-4 w-4" aria-hidden="true" />
        <span>{config.label}</span>
      </Badge>

      {/* Timestamp and Actor Info */}
      <div className="flex items-center space-x-2 text-sm text-gray-600 dark:text-gray-400">
        <span className="hidden sm:inline">
          {t('iep.status.last_action_by', { actor })}
        </span>
        <span className="text-gray-400">•</span>
        <time
          dateTime={timestamp.toISOString()}
          title={timestamp.toLocaleString()}
          className="tabular-nums"
        >
          {timestamp.toLocaleDateString()}
        </time>
      </div>

      {/* Additional Status Indicators */}
      {status === 'pending_approval' && (
        <Badge
          variant="warning"
          className="bg-amber-50 text-amber-700 border-amber-300"
        >
          <Users className="h-3 w-3 mr-1" aria-hidden="true" />
          <span className="text-xs">{t('iep.status.awaiting_review')}</span>
        </Badge>
      )}

      {status === 'proposed' && (
        <Badge
          variant="secondary"
          className="bg-blue-50 text-blue-700 border-blue-300"
        >
          <Eye className="h-3 w-3 mr-1" aria-hidden="true" />
          <span className="text-xs">{t('iep.status.needs_review')}</span>
        </Badge>
      )}
    </div>
  )
}
