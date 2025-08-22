import React, { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import {
  Camera,
  Upload as UploadIcon,
  FileText,
  AlertTriangle,
} from 'lucide-react'
import { courseworkClient } from '@/api/courseworkClient'

interface UploadProps {
  onFileSelected?: (file: File) => void
}

export default function Upload({ onFileSelected }: UploadProps) {
  const { t } = useTranslation('coursework')
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [consentError, setConsentError] = useState(false)

  const handleFileUpload = async (file: File) => {
    if (!file) return

    setIsUploading(true)
    setError(null)
    setConsentError(false)

    try {
      // Check media consent first
      const consentCheck = await courseworkClient.checkMediaConsent()
      if (!consentCheck.hasConsent) {
        setConsentError(true)
        setError(t('upload.errors.consentRequired'))
        return
      }

      // Validate file type
      const allowedTypes = [
        'image/jpeg',
        'image/png',
        'image/webp',
        'application/pdf',
      ]
      if (!allowedTypes.includes(file.type)) {
        setError(t('upload.errors.invalidFileType'))
        return
      }

      // Validate file size (10MB max)
      const maxSize = 10 * 1024 * 1024
      if (file.size > maxSize) {
        setError(t('upload.errors.fileTooLarge'))
        return
      }

      // Call parent callback if provided
      if (onFileSelected) {
        onFileSelected(file)
      } else {
        // Navigate to review page with file data
        const fileData = await fileToBase64(file)
        navigate('/coursework/review', {
          state: {
            file,
            fileData,
            fileName: file.name,
            fileType: file.type,
            fileSize: file.size,
          },
        })
      }
    } catch (err) {
      console.error('Upload error:', err)
      setError(t('upload.errors.uploadFailed'))
    } finally {
      setIsUploading(false)
    }
  }

  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = error => reject(error)
    })
  }

  const handleCameraCapture = () => {
    if (cameraInputRef.current) {
      cameraInputRef.current.click()
    }
  }

  const handleFileSelect = () => {
    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      handleFileUpload(file)
    }
  }

  const handleConsentRedirect = () => {
    navigate('/settings/consent', {
      state: { returnTo: '/coursework/upload' },
    })
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-2xl">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">{t('upload.title')}</h1>
        <p className="text-muted-foreground">{t('upload.subtitle')}</p>
      </div>

      {error && (
        <Alert
          className={`mb-6 ${consentError ? 'border-orange-200 bg-orange-50' : 'border-red-200 bg-red-50'}`}
        >
          <AlertTriangle
            className={`h-4 w-4 ${consentError ? 'text-orange-600' : 'text-red-600'}`}
          />
          <AlertDescription
            className={consentError ? 'text-orange-800' : 'text-red-800'}
          >
            {error}
            {consentError && (
              <Button
                variant="link"
                className="p-0 h-auto ml-2 text-orange-600 underline"
                onClick={handleConsentRedirect}
              >
                {t('upload.grantConsent')}
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Camera Capture Card */}
        <Card className="hover:shadow-lg transition-shadow cursor-pointer group">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 p-4 bg-blue-100 rounded-full w-16 h-16 flex items-center justify-center group-hover:bg-blue-200 transition-colors">
              <Camera className="h-8 w-8 text-blue-600" />
            </div>
            <CardTitle className="text-xl">
              {t('upload.camera.title')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4 text-center">
              {t('upload.camera.description')}
            </p>
            <Button
              onClick={handleCameraCapture}
              disabled={isUploading}
              className="w-full"
              size="lg"
            >
              {isUploading ? t('upload.processing') : t('upload.camera.button')}
            </Button>
          </CardContent>
        </Card>

        {/* File Upload Card */}
        <Card className="hover:shadow-lg transition-shadow cursor-pointer group">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 p-4 bg-green-100 rounded-full w-16 h-16 flex items-center justify-center group-hover:bg-green-200 transition-colors">
              <FileText className="h-8 w-8 text-green-600" />
            </div>
            <CardTitle className="text-xl">{t('upload.file.title')}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground mb-4 text-center">
              {t('upload.file.description')}
            </p>
            <Button
              onClick={handleFileSelect}
              disabled={isUploading}
              variant="outline"
              className="w-full"
              size="lg"
            >
              <UploadIcon className="mr-2 h-4 w-4" />
              {isUploading ? t('upload.processing') : t('upload.file.button')}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Hidden file inputs */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
        className="hidden"
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*,application/pdf"
        onChange={handleFileChange}
        className="hidden"
      />

      {/* Upload Instructions */}
      <div className="mt-8 p-6 bg-muted rounded-lg">
        <h3 className="font-semibold mb-3">{t('upload.instructions.title')}</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>• {t('upload.instructions.fileTypes')}</li>
          <li>• {t('upload.instructions.fileSize')}</li>
          <li>• {t('upload.instructions.quality')}</li>
          <li>• {t('upload.instructions.consent')}</li>
        </ul>
      </div>
    </div>
  )
}
