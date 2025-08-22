import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/Avatar'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ArrowLeft,
  Upload,
  User,
  CheckCircle,
  AlertCircle,
  FileText,
} from 'lucide-react'
import { courseworkClient, OCRPreviewResponse } from '@/api/courseworkClient'

interface LocationState {
  file: File
  fileData: string
  fileName: string
  fileType: string
  fileSize: number
  ocrData: OCRPreviewResponse
  metadata: {
    subject: string
    topics: string[]
    gradeBand: string
    extractedText: string
    confidence: number
  }
}

interface Learner {
  id: string
  name: string
  email: string
  gradeBand: string
  avatar?: string
}

export default function Confirm() {
  const { t } = useTranslation('coursework')
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as LocationState

  const [learners, setLearners] = useState<Learner[]>([])
  const [selectedLearner, setSelectedLearner] = useState<string>('')
  const [isUploading, setIsUploading] = useState(false)
  const [isLoadingLearners, setIsLoadingLearners] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploadProgress, setUploadProgress] = useState(0)

  useEffect(() => {
    if (!state?.file || !state?.metadata) {
      navigate('/coursework/upload')
      return
    }

    loadLearners()
  }, [state, navigate])

  const loadLearners = async () => {
    try {
      setIsLoadingLearners(true)
      // Mock learner data - in real app, this would come from learner service
      const mockLearners: Learner[] = [
        {
          id: '1',
          name: 'Emma Johnson',
          email: 'emma.j@example.com',
          gradeBand: 'Grade 5',
          avatar: '/avatars/emma.jpg',
        },
        {
          id: '2',
          name: 'Michael Chen',
          email: 'michael.c@example.com',
          gradeBand: 'Grade 6',
        },
        {
          id: '3',
          name: 'Sofia Rodriguez',
          email: 'sofia.r@example.com',
          gradeBand: 'Grade 5',
          avatar: '/avatars/sofia.jpg',
        },
      ]

      setLearners(mockLearners)

      // Auto-select learner if grade band matches
      const matchingLearner = mockLearners.find(
        learner => learner.gradeBand === state.metadata.gradeBand
      )
      if (matchingLearner) {
        setSelectedLearner(matchingLearner.id)
      }
    } catch (err) {
      console.error('Failed to load learners:', err)
      setError(t('confirm.errors.loadLearnersFailed'))
    } finally {
      setIsLoadingLearners(false)
    }
  }

  const handleBack = () => {
    navigate('/coursework/review', { state })
  }

  const handleConfirm = async () => {
    if (!selectedLearner || !state.metadata) {
      return
    }

    setIsUploading(true)
    setError(null)
    setUploadProgress(0)

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 200)

      // Upload coursework
      const uploadRequest = {
        fileName: state.fileName,
        fileType: state.fileType,
        fileSize: state.fileSize,
        subject: state.metadata.subject,
        topics: state.metadata.topics,
        gradeBand: state.metadata.gradeBand,
        extractedText: state.metadata.extractedText,
        ocrConfidence: state.metadata.confidence,
        metadata: {
          uploadSource: 'web-ui',
          processingDate: new Date().toISOString(),
          learnerAttached: true,
        },
      }

      const uploadedAsset = await courseworkClient.uploadCoursework(
        uploadRequest,
        state.file
      )

      setUploadProgress(95)

      // Attach to learner
      await courseworkClient.attachToLearner(uploadedAsset.id, selectedLearner)

      setUploadProgress(100)

      // Clear interval
      clearInterval(progressInterval)

      // Navigate to success page or coursework list
      setTimeout(() => {
        navigate('/coursework', {
          state: {
            uploadSuccess: true,
            assetId: uploadedAsset.id,
            learnerName: learners.find(l => l.id === selectedLearner)?.name,
          },
        })
      }, 1000)
    } catch (err) {
      console.error('Upload error:', err)
      setError(t('confirm.errors.uploadFailed'))
      setUploadProgress(0)
    } finally {
      setIsUploading(false)
    }
  }

  const selectedLearnerData = learners.find(l => l.id === selectedLearner)
  const canConfirm = selectedLearner && !isUploading && !isLoadingLearners

  if (!state?.file || !state?.metadata) {
    return null
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleBack}
            disabled={isUploading}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('common.back')}
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{t('confirm.title')}</h1>
            <p className="text-muted-foreground">{t('confirm.subtitle')}</p>
          </div>
        </div>
      </div>

      {error && (
        <Alert className="mb-6 border-red-200 bg-red-50">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Upload Summary */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <FileText className="h-5 w-5" />
                <span>{t('confirm.summary.title')}</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* File Info */}
              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div>
                  <p className="font-medium">{state.fileName}</p>
                  <p className="text-sm text-muted-foreground">
                    {(state.fileSize / 1024 / 1024).toFixed(1)} MB •{' '}
                    {state.fileType}
                  </p>
                </div>
                <Badge variant="secondary">
                  {Math.round(state.metadata.confidence * 100)}%{' '}
                  {t('confirm.summary.confidence')}
                </Badge>
              </div>

              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">
                    {t('confirm.summary.subject')}
                  </p>
                  <p className="font-medium">{state.metadata.subject}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-1">
                    {t('confirm.summary.gradeBand')}
                  </p>
                  <p className="font-medium">{state.metadata.gradeBand}</p>
                </div>
              </div>

              {/* Topics */}
              {state.metadata.topics.length > 0 && (
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">
                    {t('confirm.summary.topics')}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {state.metadata.topics.map((topic, idx) => (
                      <Badge key={idx} variant="outline">
                        {topic}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Text Preview */}
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  {t('confirm.summary.extractedText')}
                </p>
                <div className="max-h-32 overflow-y-auto p-3 bg-muted rounded border text-sm">
                  <p className="whitespace-pre-wrap">
                    {state.metadata.extractedText.length > 200
                      ? `${state.metadata.extractedText.substring(0, 200)}...`
                      : state.metadata.extractedText}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Learner Assignment */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <User className="h-5 w-5" />
                <span>{t('confirm.learner.title')}</span>
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                {t('confirm.learner.description')}
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              {isLoadingLearners ? (
                <div className="text-center py-4">
                  <p className="text-muted-foreground">
                    {t('confirm.learner.loading')}
                  </p>
                </div>
              ) : (
                <>
                  <Select
                    value={selectedLearner}
                    onValueChange={setSelectedLearner}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder={t('confirm.learner.select')} />
                    </SelectTrigger>
                    <SelectContent>
                      {learners.map(learner => (
                        <SelectItem key={learner.id} value={learner.id}>
                          <div className="flex items-center space-x-2">
                            <Avatar className="h-6 w-6">
                              <AvatarImage src={learner.avatar} />
                              <AvatarFallback>
                                {learner.name
                                  .split(' ')
                                  .map(n => n[0])
                                  .join('')}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="font-medium">{learner.name}</p>
                              <p className="text-xs text-muted-foreground">
                                {learner.gradeBand}
                              </p>
                            </div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  {selectedLearnerData && (
                    <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                      <div className="flex items-center space-x-3">
                        <Avatar>
                          <AvatarImage src={selectedLearnerData.avatar} />
                          <AvatarFallback>
                            {selectedLearnerData.name
                              .split(' ')
                              .map(n => n[0])
                              .join('')}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <p className="font-medium">
                            {selectedLearnerData.name}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {selectedLearnerData.email}
                          </p>
                          <p className="text-sm text-green-700">
                            {selectedLearnerData.gradeBand}
                          </p>
                        </div>
                        <CheckCircle className="h-5 w-5 text-green-600" />
                      </div>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          {/* Upload Progress */}
          {isUploading && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Upload className="h-5 w-5" />
                  <span>{t('confirm.upload.title')}</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">
                      {t('confirm.upload.progress')}
                    </span>
                    <span className="text-sm font-medium">
                      {uploadProgress}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {uploadProgress < 30
                      ? t('confirm.upload.uploading')
                      : uploadProgress < 60
                        ? t('confirm.upload.processing')
                        : uploadProgress < 90
                          ? t('confirm.upload.analyzing')
                          : t('confirm.upload.completing')}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Confirm Button */}
          <Button
            onClick={handleConfirm}
            disabled={!canConfirm}
            size="lg"
            className="w-full"
          >
            {isUploading ? (
              <>
                <Upload className="h-4 w-4 mr-2 animate-spin" />
                {t('confirm.uploading')}
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                {t('confirm.confirmUpload')}
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}
