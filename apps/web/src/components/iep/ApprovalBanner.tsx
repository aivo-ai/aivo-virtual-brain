import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import {
  CheckCircle,
  XCircle,
  Clock,
  MessageSquare,
  AlertTriangle,
  Send,
  Eye,
} from 'lucide-react'
import { toast } from 'sonner'

import { iepClient, type IEPDraft } from '@/api/iepClient'
import { Alert } from '@/components/ui/Alert'
import { Button } from '@/components/ui/Button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card'
import { Textarea } from '@/components/ui/Textarea'
import { Badge } from '@/components/ui/Badge'
import { Separator } from '@/components/ui/separator'

interface ApprovalBannerProps {
  iep: IEPDraft
  onStatusUpdate: () => void
  className?: string
}

export function ApprovalBanner({
  iep,
  onStatusUpdate,
  className = '',
}: ApprovalBannerProps) {
  const { t } = useTranslation()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showSubmitForm, setShowSubmitForm] = useState(false)
  const [submitComments, setSubmitComments] = useState('')

  // Submit for approval mutation
  const submitForApprovalMutation = useMutation({
    mutationFn: (input: { iepId: string; comments?: string }) =>
      iepClient.submitIepForApproval({
        iepId: input.iepId,
        approvers: [
          { userId: 'parent-1', role: 'parent', required: true },
          { userId: 'teacher-1', role: 'teacher', required: true },
          { userId: 'admin-1', role: 'admin', required: false },
        ],
        comments: input.comments,
      }),
    onSuccess: () => {
      toast.success(t('iep.approval.submitted_for_approval'))
      setShowSubmitForm(false)
      setSubmitComments('')
      onStatusUpdate()
    },
    onError: error => {
      toast.error(t('iep.approval.submit_error'))
      console.error('Failed to submit for approval:', error)
    },
  })

  // Update approval status mutation (TODO: Implement approval update functionality)
  // const updateApprovalMutation = useMutation({
  //   mutationFn: (input: {
  //     approvalId: string
  //     status: string
  //     comments?: string
  //     requiredChanges?: string[]
  //   }) => iepClient.updateApprovalStatus(input.approvalId, input.status, input.comments, input.requiredChanges),
  //   onSuccess: () => {
  //     toast.success(t('iep.approval.status_updated'))
  //     onStatusUpdate()
  //   },
  //   onError: (error) => {
  //     toast.error(t('iep.approval.update_error'))
  //     console.error('Failed to update approval status:', error)
  //   },
  // })

  const handleSubmitForApproval = async () => {
    setIsSubmitting(true)
    try {
      await submitForApprovalMutation.mutateAsync({
        iepId: iep.id,
        comments: submitComments.trim() || undefined,
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'bg-green-50 border-green-200 text-green-800'
      case 'rejected':
        return 'bg-red-50 border-red-200 text-red-800'
      case 'pending':
        return 'bg-amber-50 border-amber-200 text-amber-800'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'rejected':
        return <XCircle className="h-4 w-4 text-red-600" />
      case 'pending':
        return <Clock className="h-4 w-4 text-amber-600" />
      default:
        return <Clock className="h-4 w-4 text-gray-600" />
    }
  }

  const renderStatusBanner = () => {
    switch (iep.status) {
      case 'proposed':
        return (
          <Alert className="bg-blue-50 border-blue-200 text-blue-800">
            <Eye className="h-4 w-4" />
            <div className="flex-1">
              <p className="font-medium">{t('iep.approval.proposal_ready')}</p>
              <p className="text-sm mt-1">
                {t('iep.approval.proposal_ready_description')}
              </p>
            </div>
            <div className="flex space-x-2 ml-4">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowSubmitForm(!showSubmitForm)}
                className="border-blue-300 text-blue-700 hover:bg-blue-100"
              >
                <Send className="h-4 w-4 mr-1" />
                {t('iep.approval.submit_for_approval')}
              </Button>
            </div>
          </Alert>
        )

      case 'pending_approval':
        return (
          <Alert className="bg-amber-50 border-amber-200 text-amber-800">
            <Clock className="h-4 w-4" />
            <div>
              <p className="font-medium">
                {t('iep.approval.pending_approval')}
              </p>
              <p className="text-sm mt-1">
                {t('iep.approval.pending_approval_description')}
              </p>
              {iep.metadata.submittedAt && (
                <p className="text-xs mt-1">
                  {t('iep.approval.submitted_on', {
                    date: new Date(
                      iep.metadata.submittedAt
                    ).toLocaleDateString(),
                  })}
                </p>
              )}
            </div>
          </Alert>
        )

      case 'approved':
        return (
          <Alert className="bg-green-50 border-green-200 text-green-800">
            <CheckCircle className="h-4 w-4" />
            <div>
              <p className="font-medium">{t('iep.approval.approved')}</p>
              <p className="text-sm mt-1">
                {t('iep.approval.approved_description')}
              </p>
              {iep.metadata.reviewedAt && (
                <p className="text-xs mt-1">
                  {t('iep.approval.approved_on', {
                    date: new Date(
                      iep.metadata.reviewedAt
                    ).toLocaleDateString(),
                  })}
                </p>
              )}
            </div>
          </Alert>
        )

      case 'rejected':
        return (
          <Alert className="bg-red-50 border-red-200 text-red-800">
            <XCircle className="h-4 w-4" />
            <div>
              <p className="font-medium">{t('iep.approval.rejected')}</p>
              <p className="text-sm mt-1">
                {t('iep.approval.rejected_description')}
              </p>
              {iep.metadata.reviewedAt && (
                <p className="text-xs mt-1">
                  {t('iep.approval.rejected_on', {
                    date: new Date(
                      iep.metadata.reviewedAt
                    ).toLocaleDateString(),
                  })}
                </p>
              )}
            </div>
          </Alert>
        )

      case 'active':
        return (
          <Alert className="bg-emerald-50 border-emerald-200 text-emerald-800">
            <CheckCircle className="h-4 w-4" />
            <div>
              <p className="font-medium">{t('iep.approval.active')}</p>
              <p className="text-sm mt-1">
                {t('iep.approval.active_description')}
              </p>
            </div>
          </Alert>
        )

      default:
        return null
    }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Main Status Banner */}
      {renderStatusBanner()}

      {/* Submit for Approval Form */}
      {showSubmitForm && iep.status === 'proposed' && (
        <Card className="border-blue-200">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg">
              {t('iep.approval.submit_form_title')}
            </CardTitle>
            <CardDescription>
              {t('iep.approval.submit_form_description')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label
                htmlFor="submit-comments"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                {t('iep.approval.optional_comments')}
              </label>
              <Textarea
                id="submit-comments"
                placeholder={t('iep.approval.comments_placeholder')}
                value={submitComments}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setSubmitComments(e.target.value)
                }
                rows={3}
                className="resize-none"
              />
            </div>

            <div className="flex justify-end space-x-3">
              <Button
                variant="outline"
                onClick={() => {
                  setShowSubmitForm(false)
                  setSubmitComments('')
                }}
              >
                {t('common.cancel')}
              </Button>
              <Button
                onClick={handleSubmitForApproval}
                disabled={isSubmitting || submitForApprovalMutation.isPending}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isSubmitting || submitForApprovalMutation.isPending ? (
                  <>
                    <Clock className="h-4 w-4 mr-2 animate-spin" />
                    {t('iep.approval.submitting')}
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    {t('iep.approval.submit_for_approval')}
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Approval Details */}
      {iep.approvals && iep.approvals.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <MessageSquare className="h-5 w-5" />
              <span>{t('iep.approval.approval_details')}</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {iep.approvals.map((approval, index) => (
                <div key={approval.id}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        {getStatusIcon(approval.status)}
                        <div>
                          <p className="font-medium text-gray-900 dark:text-white">
                            {approval.actor}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {t(`iep.approval.role.${approval.actorRole}`)}
                          </p>
                        </div>
                        <Badge className={getStatusColor(approval.status)}>
                          {t(`iep.approval.status.${approval.status}`)}
                        </Badge>
                      </div>

                      {approval.comments && (
                        <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-md">
                          <p className="text-sm text-gray-700 dark:text-gray-300">
                            {approval.comments}
                          </p>
                        </div>
                      )}

                      {approval.requiredChanges &&
                        approval.requiredChanges.length > 0 && (
                          <div className="mt-2 p-3 bg-amber-50 border border-amber-200 rounded-md">
                            <p className="text-sm font-medium text-amber-800 mb-2 flex items-center">
                              <AlertTriangle className="h-4 w-4 mr-1" />
                              {t('iep.approval.required_changes')}
                            </p>
                            <ul className="text-sm text-amber-700 space-y-1">
                              {approval.requiredChanges.map((change, idx) => (
                                <li key={idx} className="flex items-start">
                                  <span className="mr-2">•</span>
                                  <span>{change}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                    </div>

                    <div className="text-sm text-gray-500 ml-4">
                      {new Date(approval.timestamp).toLocaleString()}
                    </div>
                  </div>

                  {index < iep.approvals.length - 1 && (
                    <Separator className="mt-4" />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
