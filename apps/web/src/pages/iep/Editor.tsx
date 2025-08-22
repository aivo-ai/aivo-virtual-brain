import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Save,
  Eye,
  FileText,
  AlertCircle,
  CheckCircle,
  Edit3,
  Bot,
  Diff,
} from 'lucide-react'

import { iepClient } from '@/api/iepClient'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs'
import { Badge } from '@/components/ui/Badge'
// import { Separator } from '@/components/ui/separator'

import { StatusChips } from '@/components/iep/StatusChips'
import { ApprovalBanner } from '@/components/iep/ApprovalBanner'
// import { SectionEditor } from '@/components/iep/SectionEditor'

interface EditorProps {
  className?: string
}

export default function Editor({ className = '' }: EditorProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { learnerId } = useParams<{ learnerId: string }>()
  const queryClient = useQueryClient()

  const [hasUnsavedChanges] = useState(false) // TODO: Implement editing functionality with SectionEditor
  const [showDifferences, setShowDifferences] = useState(false)

  // Fetch IEP data
  const {
    data: iep,
    isLoading: isLoadingIEP,
    error,
  } = useQuery({
    queryKey: ['iep', learnerId],
    queryFn: () => (learnerId ? iepClient.getIEP(learnerId) : null),
    enabled: !!learnerId,
  })

  const handleBackToAssistant = () => {
    if (hasUnsavedChanges) {
      const confirmed = window.confirm(t('iep.editor.unsaved_changes_warning'))
      if (!confirmed) return
    }
    navigate(ROUTES.IEP_ASSISTANT.replace(':learnerId', learnerId!))
  }

  const handleBackToLearner = () => {
    if (hasUnsavedChanges) {
      const confirmed = window.confirm(t('iep.editor.unsaved_changes_warning'))
      if (!confirmed) return
    }
    navigate(ROUTES.LEARNER_DETAIL.replace(':id', learnerId!))
  }

  // Warn about unsaved changes on page unload
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [hasUnsavedChanges])

  if (isLoadingIEP) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
        <div className="max-w-6xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
            <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !iep) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-4">
        <div className="max-w-6xl mx-auto">
          <Alert className="bg-red-50 border-red-200 text-red-800">
            <AlertCircle className="h-4 w-4" />
            <div>
              <p className="font-medium">{t('iep.editor.not_found')}</p>
              <p className="text-sm mt-1">
                {t('iep.editor.not_found_description')}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() =>
                  navigate(
                    ROUTES.IEP_ASSISTANT.replace(':learnerId', learnerId!)
                  )
                }
              >
                <Bot className="h-4 w-4 mr-2" />
                {t('iep.editor.create_new')}
              </Button>
            </div>
          </Alert>
        </div>
      </div>
    )
  }

  const getStatusMessage = () => {
    switch (iep.status) {
      case 'draft':
        return {
          icon: Edit3,
          title: t('iep.editor.status.draft_title'),
          description: t('iep.editor.status.draft_description'),
        }
      case 'proposed':
        return {
          icon: FileText,
          title: t('iep.editor.status.proposed_title'),
          description: t('iep.editor.status.proposed_description'),
        }
      case 'pending_approval':
        return {
          icon: Eye,
          title: t('iep.editor.status.pending_title'),
          description: t('iep.editor.status.pending_description'),
        }
      case 'approved':
        return {
          icon: CheckCircle,
          title: t('iep.editor.status.approved_title'),
          description: t('iep.editor.status.approved_description'),
        }
      case 'rejected':
        return {
          icon: AlertCircle,
          title: t('iep.editor.status.rejected_title'),
          description: t('iep.editor.status.rejected_description'),
        }
      case 'active':
        return {
          icon: CheckCircle,
          title: t('iep.editor.status.active_title'),
          description: t('iep.editor.status.active_description'),
        }
      default:
        return {
          icon: AlertCircle,
          title: t('iep.editor.status.unknown_title'),
          description: t('iep.editor.status.unknown_description'),
        }
    }
  }

  const statusMessage = getStatusMessage()
  const StatusIcon = statusMessage.icon
  const isReadOnly = ['pending_approval', 'approved', 'active'].includes(
    iep.status
  )

  return (
    <div
      className={`min-h-screen bg-gray-50 dark:bg-gray-900 p-4 ${className}`}
    >
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleBackToAssistant}
              className="text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              {t('iep.editor.back_to_assistant')}
            </Button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {t('iep.editor.title')}
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                {t('iep.editor.subtitle')}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {hasUnsavedChanges && (
              <Badge
                variant="warning"
                className="bg-amber-50 text-amber-700 border-amber-300"
              >
                {t('iep.editor.unsaved_changes')}
              </Badge>
            )}
            <StatusChips status={iep.status} metadata={iep.metadata} />
          </div>
        </div>

        {/* Status Message */}
        <Alert className="border-l-4">
          <StatusIcon className="h-4 w-4" />
          <div>
            <p className="font-medium">{statusMessage.title}</p>
            <p className="text-sm mt-1">{statusMessage.description}</p>
          </div>
        </Alert>

        {/* Approval Banner */}
        {iep.status !== 'draft' && (
          <ApprovalBanner
            iep={iep}
            onStatusUpdate={() =>
              queryClient.invalidateQueries({ queryKey: ['iep', learnerId] })
            }
          />
        )}

        {/* Differences View */}
        {iep.differences && iep.differences.length > 0 && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Diff className="h-5 w-5" />
                  <CardTitle>{t('iep.editor.changes_preview')}</CardTitle>
                </div>
                <Button onClick={() => setShowDifferences(!showDifferences)}>
                  {showDifferences ? t('common.hide') : t('common.show')}
                </Button>
              </div>
              <CardDescription>
                {t('iep.editor.changes_description', {
                  count: iep.differences.length,
                })}
              </CardDescription>
            </CardHeader>
            {showDifferences && (
              <CardContent>
                <div className="space-y-4">
                  {iep.differences.map((diff, index) => (
                    <div key={index} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <Badge variant="secondary">
                          {diff.section} - {diff.field}
                        </Badge>
                        <Badge
                          variant={
                            diff.changeType === 'added'
                              ? 'default'
                              : diff.changeType === 'removed'
                                ? 'danger'
                                : 'secondary'
                          }
                        >
                          {t(`iep.editor.change_type.${diff.changeType}`)}
                        </Badge>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        {diff.changeType !== 'added' && (
                          <div>
                            <p className="font-medium text-red-700 mb-1">
                              {t('iep.editor.old_value')}
                            </p>
                            <div className="bg-red-50 border border-red-200 rounded p-2">
                              <pre className="whitespace-pre-wrap text-red-800">
                                {typeof diff.oldValue === 'string'
                                  ? diff.oldValue
                                  : JSON.stringify(diff.oldValue, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}

                        {diff.changeType !== 'removed' && (
                          <div>
                            <p className="font-medium text-green-700 mb-1">
                              {t('iep.editor.new_value')}
                            </p>
                            <div className="bg-green-50 border border-green-200 rounded p-2">
                              <pre className="whitespace-pre-wrap text-green-800">
                                {typeof diff.newValue === 'string'
                                  ? diff.newValue
                                  : JSON.stringify(diff.newValue, null, 2)}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            )}
          </Card>
        )}

        {/* Main Editor */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>{t('iep.editor.iep_content')}</span>
              </CardTitle>

              {!isReadOnly && (
                <div className="flex space-x-2">
                  <Button variant="outline" size="sm">
                    <Eye className="h-4 w-4 mr-2" />
                    {t('iep.editor.preview')}
                  </Button>
                  <Button size="sm" disabled={!hasUnsavedChanges}>
                    <Save className="h-4 w-4 mr-2" />
                    {t('common.save')}
                  </Button>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="goals" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="goals">
                  {t('iep.editor.tabs.goals')}
                </TabsTrigger>
                <TabsTrigger value="accommodations">
                  {t('iep.editor.tabs.accommodations')}
                </TabsTrigger>
                <TabsTrigger value="services">
                  {t('iep.editor.tabs.services')}
                </TabsTrigger>
                <TabsTrigger value="assessments">
                  {t('iep.editor.tabs.assessments')}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="goals" className="mt-6">
                {/* TODO: Implement SectionEditor component */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p>
                    Goals section - SectionEditor component to be implemented
                  </p>
                </div>
                {/* 
                <SectionEditor
                  section="goals"
                  data={iep.content.goals}
                  readOnly={isReadOnly}
                  onChange={(_data) => {
                    // Handle goals changes
                    setHasUnsavedChanges(true)
                  }}
                />
                */}
              </TabsContent>

              <TabsContent value="accommodations" className="mt-6">
                {/* TODO: Implement SectionEditor component */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p>
                    Accommodations section - SectionEditor component to be
                    implemented
                  </p>
                </div>
                {/* 
                <SectionEditor
                  section="accommodations"
                  data={iep.content.accommodations}
                  readOnly={isReadOnly}
                  onChange={(_data) => {
                    // Handle accommodations changes
                    setHasUnsavedChanges(true)
                  }}
                />
                */}
              </TabsContent>

              <TabsContent value="services" className="mt-6">
                {/* TODO: Implement SectionEditor component */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p>
                    Services section - SectionEditor component to be implemented
                  </p>
                </div>
                {/* 
                <SectionEditor
                  section="services"
                  data={iep.content.services}
                  readOnly={isReadOnly}
                  onChange={(_data) => {
                    // Handle services changes
                    setHasUnsavedChanges(true)
                  }}
                />
                */}
              </TabsContent>

              <TabsContent value="assessments" className="mt-6">
                {/* TODO: Implement SectionEditor component */}
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p>
                    Assessments section - SectionEditor component to be
                    implemented
                  </p>
                </div>
                {/* 
                <SectionEditor
                  section="assessments"
                  data={iep.content.assessments}
                  readOnly={isReadOnly}
                  onChange={(_data) => {
                    // Handle assessments changes
                    setHasUnsavedChanges(true)
                  }}
                />
                */}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex justify-between items-center">
          <Button variant="outline" onClick={handleBackToLearner}>
            {t('iep.editor.back_to_learner')}
          </Button>

          <div className="flex space-x-3">
            <Button
              variant="outline"
              onClick={() =>
                navigate(ROUTES.IEP_REVIEW.replace(':learnerId', learnerId!))
              }
            >
              <Eye className="h-4 w-4 mr-2" />
              {t('iep.editor.review_mode')}
            </Button>

            {iep.status === 'draft' && (
              <Button
                onClick={() =>
                  navigate(
                    ROUTES.IEP_ASSISTANT.replace(':learnerId', learnerId!)
                  )
                }
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Bot className="h-4 w-4 mr-2" />
                {t('iep.editor.back_to_assistant')}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
