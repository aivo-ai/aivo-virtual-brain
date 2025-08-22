import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Bot,
  FileText,
  Users,
  CheckCircle,
  AlertCircle,
} from 'lucide-react'
import { toast } from 'sonner'

import { iepClient, type ProposeIEPInput } from '@/api/iepClient'
import { ROUTES } from '@/types/routes'
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
import { Label } from '@/components/ui/Label'
import { Separator } from '@/components/ui/separator'

import { ProposeButton } from '@/components/iep/ProposeButton'
import { StatusChips } from '@/components/iep/StatusChips'
import { ApprovalBanner } from '@/components/iep/ApprovalBanner'

interface AssistantEntryProps {
  className?: string
}

export default function AssistantEntry({
  className = '',
}: AssistantEntryProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { learnerId } = useParams<{ learnerId: string }>()
  const queryClient = useQueryClient()

  const [assistantPrompt, setAssistantPrompt] = useState('')
  const [generateFromData, setGenerateFromData] = useState(true)
  const [isProposing, setIsProposing] = useState(false)

  // Fetch existing IEP if any
  const { data: existingIEP, isLoading: isLoadingIEP } = useQuery({
    queryKey: ['iep', learnerId],
    queryFn: () => (learnerId ? iepClient.getIEP(learnerId) : null),
    enabled: !!learnerId,
  })

  // Propose IEP mutation
  const proposeMutation = useMutation({
    mutationFn: (input: ProposeIEPInput) => iepClient.proposeIep(input),
    onSuccess: _data => {
      toast.success(t('iep.assistant.proposal_generated'))
      queryClient.invalidateQueries({ queryKey: ['iep', learnerId] })
      // Navigate to editor to review the proposal
      navigate(ROUTES.IEP_EDITOR.replace(':learnerId', learnerId!))
    },
    onError: error => {
      toast.error(t('iep.assistant.proposal_error'))
      console.error('Failed to propose IEP:', error)
    },
  })

  const handleProposeIEP = async () => {
    if (!learnerId) return

    setIsProposing(true)
    try {
      await proposeMutation.mutateAsync({
        learnerId,
        assistantPrompt: assistantPrompt.trim() || undefined,
        generateFromData,
      })
    } finally {
      setIsProposing(false)
    }
  }

  const handleBackToLearner = () => {
    navigate(ROUTES.LEARNER_DETAIL.replace(':id', learnerId!))
  }

  if (isLoadingIEP) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
            <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`min-h-screen bg-gray-50 dark:bg-gray-900 p-4 ${className}`}
    >
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBackToLearner}
              className="text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              {t('common.back')}
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {t('iep.assistant.title')}
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                {t('iep.assistant.subtitle')}
              </p>
            </div>
          </div>

          {existingIEP && (
            <StatusChips
              status={existingIEP.status}
              metadata={existingIEP.metadata}
            />
          )}
        </div>

        {/* Approval Banner */}
        {existingIEP && existingIEP.status !== 'draft' && (
          <ApprovalBanner
            iep={existingIEP}
            onStatusUpdate={() =>
              queryClient.invalidateQueries({ queryKey: ['iep', learnerId] })
            }
          />
        )}

        {/* Existing IEP Status */}
        {existingIEP && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>{t('iep.assistant.current_status')}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <Label className="text-gray-600">
                    {t('iep.assistant.status')}
                  </Label>
                  <p className="font-medium">{existingIEP.status}</p>
                </div>
                <div>
                  <Label className="text-gray-600">
                    {t('iep.assistant.last_updated')}
                  </Label>
                  <p className="font-medium">
                    {new Date(
                      existingIEP.metadata.updatedAt
                    ).toLocaleDateString()}
                  </p>
                </div>
                <div>
                  <Label className="text-gray-600">
                    {t('iep.assistant.created_by')}
                  </Label>
                  <p className="font-medium">
                    {existingIEP.metadata.createdBy}
                  </p>
                </div>
              </div>

              {existingIEP.status === 'approved' && (
                <Alert className="bg-green-50 border-green-200 text-green-800">
                  <CheckCircle className="h-4 w-4" />
                  <span>{t('iep.assistant.iep_approved')}</span>
                </Alert>
              )}

              {existingIEP.status === 'rejected' && (
                <Alert className="bg-red-50 border-red-200 text-red-800">
                  <AlertCircle className="h-4 w-4" />
                  <span>{t('iep.assistant.iep_rejected')}</span>
                </Alert>
              )}

              <div className="flex space-x-3">
                <Button
                  variant="outline"
                  onClick={() =>
                    navigate(
                      ROUTES.IEP_EDITOR.replace(':learnerId', learnerId!)
                    )
                  }
                >
                  {t('iep.assistant.view_editor')}
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    navigate(
                      ROUTES.IEP_REVIEW.replace(':learnerId', learnerId!)
                    )
                  }
                >
                  {t('iep.assistant.view_review')}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Assistant Proposal Interface */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Bot className="h-5 w-5 text-blue-600" />
              <span>{t('iep.assistant.propose_new')}</span>
            </CardTitle>
            <CardDescription>
              {t('iep.assistant.propose_description')}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Assistant Prompt */}
            <div className="space-y-2">
              <Label htmlFor="assistant-prompt">
                {t('iep.assistant.custom_prompt')}
              </Label>
              <Textarea
                id="assistant-prompt"
                placeholder={t('iep.assistant.prompt_placeholder')}
                value={assistantPrompt}
                onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
                  setAssistantPrompt(e.target.value)
                }
                rows={4}
                className="resize-none"
              />
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {t('iep.assistant.prompt_hint')}
              </p>
            </div>

            <Separator />

            {/* Data Source Options */}
            <div className="space-y-4">
              <Label className="text-base font-medium">
                {t('iep.assistant.data_sources')}
              </Label>
              <div className="space-y-3">
                <label className="flex items-center space-x-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={generateFromData}
                    onChange={e => setGenerateFromData(e.target.checked)}
                    className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {t('iep.assistant.use_learner_data')}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      {t('iep.assistant.use_learner_data_description')}
                    </p>
                  </div>
                </label>
              </div>
            </div>

            <Separator />

            {/* Action Buttons */}
            <div className="flex justify-between items-center">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {t('iep.assistant.review_before_submit')}
              </div>

              <ProposeButton
                onPropose={handleProposeIEP}
                isLoading={isProposing || proposeMutation.isPending}
                disabled={!learnerId}
                hasExistingIEP={!!existingIEP}
              />
            </div>

            {/* Warning for existing IEP */}
            {existingIEP && existingIEP.status !== 'draft' && (
              <Alert className="bg-amber-50 border-amber-200 text-amber-800">
                <AlertCircle className="h-4 w-4" />
                <div>
                  <p className="font-medium">
                    {t('iep.assistant.existing_iep_warning')}
                  </p>
                  <p className="text-sm mt-1">
                    {t('iep.assistant.existing_iep_warning_description')}
                  </p>
                </div>
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Users className="h-5 w-5" />
              <span>{t('iep.assistant.quick_actions')}</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Button
                variant="outline"
                className="justify-start h-auto p-4"
                onClick={() =>
                  navigate(
                    ROUTES.LEARNER_ASSESSMENTS.replace(':id', learnerId!)
                  )
                }
              >
                <div className="text-left">
                  <p className="font-medium">
                    {t('iep.assistant.view_assessments')}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    {t('iep.assistant.view_assessments_description')}
                  </p>
                </div>
              </Button>

              <Button
                variant="outline"
                className="justify-start h-auto p-4"
                onClick={() =>
                  navigate(ROUTES.LEARNER_PROGRESS.replace(':id', learnerId!))
                }
              >
                <div className="text-left">
                  <p className="font-medium">
                    {t('iep.assistant.view_progress')}
                  </p>
                  <p className="text-sm text-gray-600 mt-1">
                    {t('iep.assistant.view_progress_description')}
                  </p>
                </div>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
