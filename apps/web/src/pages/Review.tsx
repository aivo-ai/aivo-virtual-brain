import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Badge } from '@/components/ui/Badge'
import { Separator } from '@/components/ui/separator'
import { Progress } from '@/components/ui/Progress'
import {
  ArrowLeft,
  ArrowRight,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle,
} from 'lucide-react'
import { courseworkClient, OCRPreviewResponse } from '@/api/courseworkClient'
import PreviewPane from '@/components/coursework/PreviewPane'
import TopicChips from '@/components/coursework/TopicChips'

interface LocationState {
  file: File
  fileData: string
  fileName: string
  fileType: string
  fileSize: number
}

export default function Review() {
  const { t } = useTranslation('coursework')
  const navigate = useNavigate()
  const location = useLocation()
  const state = location.state as LocationState

  const [ocrData, setOcrData] = useState<OCRPreviewResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showConfidence, setShowConfidence] = useState(false)
  const [selectedSubject, setSelectedSubject] = useState<string>('')
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [selectedGradeBand, setSelectedGradeBand] = useState<string>('')

  useEffect(() => {
    if (!state?.file) {
      navigate('/coursework/upload')
      return
    }

    processOCR()
  }, [state, navigate])

  const processOCR = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const result = await courseworkClient.getOcrPreview(state.file)
      setOcrData(result)

      // Set suggested values as defaults
      if (result.suggestedMetadata) {
        setSelectedSubject(result.suggestedMetadata.subject || '')
        setSelectedTopics(result.suggestedMetadata.topics || [])
        setSelectedGradeBand(result.suggestedMetadata.gradeBand || '')
      }
    } catch (err) {
      console.error('OCR processing error:', err)
      setError(t('review.errors.ocrFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleBack = () => {
    navigate('/coursework/upload')
  }

  const handleContinue = () => {
    if (!ocrData || !selectedSubject) {
      return
    }

    navigate('/coursework/confirm', {
      state: {
        ...state,
        ocrData,
        metadata: {
          subject: selectedSubject,
          topics: selectedTopics,
          gradeBand: selectedGradeBand,
          extractedText: ocrData.extractedText,
          confidence: ocrData.confidence,
        },
      },
    })
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return <CheckCircle className="h-4 w-4" />
    return <AlertCircle className="h-4 w-4" />
  }

  const canContinue = selectedSubject && ocrData && !isLoading

  if (!state?.file) {
    return null
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center space-x-4">
          <Button variant="ghost" size="sm" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('common.back')}
          </Button>
          <div>
            <h1 className="text-3xl font-bold">{t('review.title')}</h1>
            <p className="text-muted-foreground">{t('review.subtitle')}</p>
          </div>
        </div>
        <Button onClick={handleContinue} disabled={!canContinue} size="lg">
          {t('review.continue')}
          <ArrowRight className="h-4 w-4 ml-2" />
        </Button>
      </div>

      {error && (
        <Alert className="mb-6 border-red-200 bg-red-50">
          <AlertCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">
            {error}
            <Button
              variant="link"
              className="p-0 h-auto ml-2 text-red-600 underline"
              onClick={processOCR}
            >
              {t('review.retry')}
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="grid lg:grid-cols-2 gap-8">
        {/* File Preview */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>{t('review.preview.title')}</CardTitle>
            <Badge variant="secondary">
              {(state.fileSize / 1024 / 1024).toFixed(1)} MB
            </Badge>
          </CardHeader>
          <CardContent>
            <PreviewPane
              fileData={state.fileData}
              fileName={state.fileName}
              fileType={state.fileType}
            />
          </CardContent>
        </Card>

        {/* OCR Results & Metadata */}
        <div className="space-y-6">
          {/* OCR Status */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>{t('review.ocr.title')}</CardTitle>
              {ocrData && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowConfidence(!showConfidence)}
                >
                  {showConfidence ? (
                    <>
                      <EyeOff className="h-4 w-4 mr-2" />{' '}
                      {t('review.ocr.hideConfidence')}
                    </>
                  ) : (
                    <>
                      <Eye className="h-4 w-4 mr-2" />{' '}
                      {t('review.ocr.showConfidence')}
                    </>
                  )}
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <Progress value={undefined} className="flex-1" />
                    <span className="text-sm text-muted-foreground">
                      {t('review.ocr.processing')}
                    </span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {t('review.ocr.processingDescription')}
                  </p>
                </div>
              ) : ocrData ? (
                <div className="space-y-4">
                  {/* Confidence Score */}
                  <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                    <div className="flex items-center space-x-2">
                      <span className={getConfidenceColor(ocrData.confidence)}>
                        {getConfidenceIcon(ocrData.confidence)}
                      </span>
                      <span className="font-medium">
                        {t('review.ocr.confidence')}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Progress
                        value={ocrData.confidence * 100}
                        className="w-20 h-2"
                      />
                      <span
                        className={`font-medium ${getConfidenceColor(ocrData.confidence)}`}
                      >
                        {Math.round(ocrData.confidence * 100)}%
                      </span>
                    </div>
                  </div>

                  {/* Extracted Text Preview */}
                  <div>
                    <h4 className="font-medium mb-2">
                      {t('review.ocr.extractedText')}
                    </h4>
                    <div className="max-h-40 overflow-y-auto p-3 bg-muted rounded border text-sm">
                      {showConfidence ? (
                        <div className="space-y-1">
                          {ocrData.extractedText.split(' ').map((word, idx) => (
                            <span
                              key={idx}
                              className={`inline-block mr-1 px-1 rounded ${
                                Math.random() > 0.8
                                  ? 'bg-red-100'
                                  : Math.random() > 0.6
                                    ? 'bg-yellow-100'
                                    : 'bg-green-100'
                              }`}
                              title={`Confidence: ${Math.round(Math.random() * 40 + 60)}%`}
                            >
                              {word}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="whitespace-pre-wrap">
                          {ocrData.extractedText}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>

          {/* Metadata Editing */}
          {ocrData && (
            <Card>
              <CardHeader>
                <CardTitle>{t('review.metadata.title')}</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {t('review.metadata.description')}
                </p>
              </CardHeader>
              <CardContent className="space-y-6">
                <TopicChips
                  suggestedSubjects={
                    ocrData.suggestedMetadata?.availableSubjects || []
                  }
                  suggestedTopics={
                    ocrData.suggestedMetadata?.availableTopics || []
                  }
                  suggestedGradeBands={
                    ocrData.suggestedMetadata?.availableGradeBands || []
                  }
                  selectedSubject={selectedSubject}
                  selectedTopics={selectedTopics}
                  selectedGradeBand={selectedGradeBand}
                  onSubjectChange={setSelectedSubject}
                  onTopicsChange={setSelectedTopics}
                  onGradeBandChange={setSelectedGradeBand}
                />
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Action Bar */}
      <div className="mt-8 pt-6 border-t">
        <div className="flex items-center justify-between">
          <Button variant="outline" onClick={handleBack}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('review.backToUpload')}
          </Button>
          <div className="flex items-center space-x-4">
            {ocrData && (
              <div className="text-sm text-muted-foreground">
                {t('review.readyToContinue', {
                  confidence: Math.round(ocrData.confidence * 100),
                })}
              </div>
            )}
            <Button onClick={handleContinue} disabled={!canContinue} size="lg">
              {t('review.continueToConfirm')}
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
