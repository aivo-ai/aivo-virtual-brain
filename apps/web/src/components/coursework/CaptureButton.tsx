import React, { useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/Button'
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Camera, Smartphone, AlertTriangle, CheckCircle } from 'lucide-react'

interface CaptureButtonProps {
  onCapture: (file: File) => void
  disabled?: boolean
  className?: string
}

export default function CaptureButton({
  onCapture,
  disabled = false,
  className = '',
}: CaptureButtonProps) {
  const { t } = useTranslation('coursework')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [isCapturing, setIsCapturing] = useState(false)

  const isMobile = () => {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    )
  }

  const supportsCamera = () => {
    return (
      'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices
    )
  }

  const handleCameraClick = () => {
    setError(null)

    if (!supportsCamera()) {
      setError(t('capture.errors.noCamera'))
      return
    }

    if (fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsCapturing(true)
    setError(null)

    try {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        setError(t('capture.errors.invalidType'))
        return
      }

      // Validate file size (5MB max for camera captures)
      const maxSize = 5 * 1024 * 1024
      if (file.size > maxSize) {
        setError(t('capture.errors.fileTooLarge'))
        return
      }

      // Check image dimensions and quality
      await validateImageQuality(file)

      onCapture(file)
    } catch (err) {
      console.error('Capture error:', err)
      setError(
        err instanceof Error ? err.message : t('capture.errors.captureFailed')
      )
    } finally {
      setIsCapturing(false)
      // Reset input to allow capturing the same file again
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const validateImageQuality = (file: File): Promise<void> => {
    return new Promise((resolve, reject) => {
      const img = new Image()
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')

      img.onload = () => {
        // Check minimum dimensions
        const minWidth = 400
        const minHeight = 300

        if (img.width < minWidth || img.height < minHeight) {
          reject(new Error(t('capture.errors.lowResolution')))
          return
        }

        // Check aspect ratio (should be reasonable for documents)
        const aspectRatio = img.width / img.height
        if (aspectRatio < 0.1 || aspectRatio > 10) {
          reject(new Error(t('capture.errors.badAspectRatio')))
          return
        }

        // Check if image appears to be mostly blank
        canvas.width = Math.min(img.width, 200)
        canvas.height = Math.min(img.height, 200)

        if (ctx) {
          ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
          const data = imageData.data

          let totalBrightness = 0
          for (let i = 0; i < data.length; i += 4) {
            const brightness = (data[i] + data[i + 1] + data[i + 2]) / 3
            totalBrightness += brightness
          }

          const avgBrightness = totalBrightness / (data.length / 4)

          // Reject if image is too dark or too bright (likely a bad capture)
          if (avgBrightness < 30) {
            reject(new Error(t('capture.errors.tooDark')))
            return
          }

          if (avgBrightness > 240) {
            reject(new Error(t('capture.errors.tooBright')))
            return
          }
        }

        resolve()
      }

      img.onerror = () => {
        reject(new Error(t('capture.errors.invalidImage')))
      }

      img.src = URL.createObjectURL(file)
    })
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {error && (
        <Alert className="border-orange-200 bg-orange-50">
          <AlertTriangle className="h-4 w-4 text-orange-600" />
          <AlertDescription className="text-orange-800">
            {error}
          </AlertDescription>
        </Alert>
      )}

      <Button
        onClick={handleCameraClick}
        disabled={disabled || isCapturing}
        className="w-full"
        size="lg"
      >
        {isCapturing ? (
          <>
            <Camera className="h-4 w-4 mr-2 animate-pulse" />
            {t('capture.processing')}
          </>
        ) : (
          <>
            <Camera className="h-4 w-4 mr-2" />
            {isMobile() ? t('capture.mobile') : t('capture.desktop')}
          </>
        )}
      </Button>

      {/* Camera capabilities info */}
      <div className="text-xs text-muted-foreground space-y-1">
        <div className="flex items-center space-x-2">
          {supportsCamera() ? (
            <CheckCircle className="h-3 w-3 text-green-600" />
          ) : (
            <AlertTriangle className="h-3 w-3 text-orange-600" />
          )}
          <span>
            {supportsCamera()
              ? t('capture.capabilities.supported')
              : t('capture.capabilities.notSupported')}
          </span>
        </div>

        {isMobile() && (
          <div className="flex items-center space-x-2">
            <Smartphone className="h-3 w-3 text-blue-600" />
            <span>{t('capture.capabilities.mobile')}</span>
          </div>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  )
}
