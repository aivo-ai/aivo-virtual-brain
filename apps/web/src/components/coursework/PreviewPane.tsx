import { useTranslation } from 'react-i18next'
import { FileText, Image, AlertCircle } from 'lucide-react'

interface PreviewPaneProps {
  fileData: string
  fileName: string
  fileType: string
}

export default function PreviewPane({
  fileData,
  fileName,
  fileType,
}: PreviewPaneProps) {
  const { t } = useTranslation('coursework')

  const renderPreview = () => {
    if (fileType.startsWith('image/')) {
      return (
        <div className="relative">
          <img
            src={fileData}
            alt={fileName}
            className="w-full h-auto max-h-96 object-contain rounded-lg border"
          />
          <div className="absolute top-2 right-2 bg-black bg-opacity-50 text-white px-2 py-1 rounded text-xs">
            <Image className="h-3 w-3 inline mr-1" />
            {t('preview.image')}
          </div>
        </div>
      )
    }

    if (fileType === 'application/pdf') {
      return (
        <div className="border-2 border-dashed border-muted rounded-lg p-8 text-center">
          <FileText className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
          <h3 className="font-medium mb-2">{t('preview.pdf.title')}</h3>
          <p className="text-sm text-muted-foreground mb-4">
            {t('preview.pdf.description')}
          </p>
          <p className="text-xs text-muted-foreground">{fileName}</p>
        </div>
      )
    }

    return (
      <div className="border-2 border-dashed border-red-200 rounded-lg p-8 text-center">
        <AlertCircle className="h-16 w-16 mx-auto text-red-400 mb-4" />
        <h3 className="font-medium mb-2 text-red-700">
          {t('preview.unsupported.title')}
        </h3>
        <p className="text-sm text-red-600">
          {t('preview.unsupported.description', { fileType })}
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {renderPreview()}
      <div className="text-xs text-muted-foreground">
        <span className="font-medium">{fileName}</span>
        <span className="mx-2">•</span>
        <span>{fileType}</span>
      </div>
    </div>
  )
}
