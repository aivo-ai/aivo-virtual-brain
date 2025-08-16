/**
 * S3-11 IEP Evidence Uploader Component
 * S3-based file upload for evidence attachments
 */

import React, { useState, useRef, useCallback } from 'react'
import { useIEPMutations, type IEPEvidence } from '../../api/iepClient'

interface EvidenceUploaderProps {
  iepId: string
  evidence: IEPEvidence[]
  onEvidenceAdded: (evidence: IEPEvidence) => void
  onEvidenceRemoved: (evidenceId: string) => void
  maxFiles?: number
  maxFileSize?: number // in MB
  allowedTypes?: string[]
}

export function EvidenceUploader({
  iepId,
  evidence,
  onEvidenceAdded,
  onEvidenceRemoved,
  maxFiles = 10,
  maxFileSize = 50, // 50MB default
  allowedTypes = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
  ],
}: EvidenceUploaderProps) {
  const { getUploadUrl, uploadToS3, addEvidence, removeEvidence } =
    useIEPMutations()

  const [dragActive, setDragActive] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>(
    {}
  )
  const [uploadErrors, setUploadErrors] = useState<Record<string, string>>({})
  const [isUploading, setIsUploading] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)

  // Check if we can add more files
  const canAddMore = evidence.length < maxFiles

  // Handle file selection
  const handleFiles = useCallback(
    async (files: FileList) => {
      const fileArray = Array.from(files)

      // Validate files
      const validFiles = fileArray.filter(file => {
        const isValidType = allowedTypes.includes(file.type)
        const isValidSize = file.size <= maxFileSize * 1024 * 1024

        if (!isValidType) {
          setUploadErrors(prev => ({
            ...prev,
            [file.name]: `File type ${file.type} is not allowed`,
          }))
          return false
        }

        if (!isValidSize) {
          setUploadErrors(prev => ({
            ...prev,
            [file.name]: `File size exceeds ${maxFileSize}MB limit`,
          }))
          return false
        }

        return true
      })

      // Check total file limit
      if (evidence.length + validFiles.length > maxFiles) {
        setUploadErrors(prev => ({
          ...prev,
          limit: `Cannot upload more than ${maxFiles} files total`,
        }))
        return
      }

      // Upload valid files
      setIsUploading(true)

      for (const file of validFiles) {
        await uploadFile(file)
      }

      setIsUploading(false)
    },
    [evidence.length, maxFiles, maxFileSize, allowedTypes]
  )

  // Upload single file
  const uploadFile = async (file: File) => {
    const fileId = `${Date.now()}-${file.name}`

    try {
      setUploadProgress(prev => ({ ...prev, [fileId]: 0 }))

      // Get signed upload URL from backend
      const uploadResponse = await getUploadUrl(file.name, file.type)

      // Upload to S3
      await uploadToS3(uploadResponse.uploadUrl, uploadResponse.fields, file)

      // Add evidence record to IEP
      const evidenceData = {
        filename: file.name,
        originalFilename: file.name,
        contentType: file.type,
        fileSize: file.size,
        evidenceType: detectFileCategory(file.type),
        description: '',
        tags: [],
        isConfidential: false,
        accessLevel: 'TEAM',
      }

      const newEvidence = await addEvidence(iepId, evidenceData)

      // Clean up progress
      setUploadProgress(prev => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { [fileId]: _, ...rest } = prev
        return rest
      })

      onEvidenceAdded({
        id: newEvidence.id,
        filename: newEvidence.filename,
        contentType: newEvidence.contentType,
        fileSize: newEvidence.fileSize,
        evidenceType: newEvidence.evidenceType,
        description: newEvidence.description || '',
        uploadedAt: newEvidence.uploadedAt,
        uploadedBy: newEvidence.uploadedBy,
        url: newEvidence.signedUrl,
      })
    } catch (error) {
      setUploadErrors(prev => ({
        ...prev,
        [fileId]: error instanceof Error ? error.message : 'Upload failed',
      }))

      // Clean up progress
      setUploadProgress(prev => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { [fileId]: _, ...rest } = prev
        return rest
      })
    }
  }

  // Detect file category based on type
  const detectFileCategory = (fileType: string): string => {
    if (fileType.startsWith('image/')) return 'assessment'
    if (fileType === 'application/pdf') return 'report'
    if (fileType.includes('word') || fileType === 'text/plain')
      return 'documentation'
    return 'other'
  }

  // Handle drag and drop
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      e.stopPropagation()
      setDragActive(false)

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files)
      }
    },
    [handleFiles]
  )

  // Handle file input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files)
    }
  }

  // Handle evidence removal
  const handleRemoveEvidence = async (evidenceId: string) => {
    try {
      await removeEvidence(iepId, evidenceId)
      onEvidenceRemoved(evidenceId)
    } catch (error) {
      console.error('Failed to remove evidence:', error)
    }
  }

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  // Get file icon
  const getFileIcon = (fileType: string): string => {
    if (fileType.startsWith('image/')) return '🖼️'
    if (fileType === 'application/pdf') return '📄'
    if (fileType.includes('word')) return '📝'
    if (fileType === 'text/plain') return '📃'
    return '📎'
  }

  // Get category badge style
  const getCategoryBadgeStyle = (category: string) => {
    switch (category) {
      case 'assessment':
        return 'bg-blue-100 text-blue-800'
      case 'report':
        return 'bg-green-100 text-green-800'
      case 'documentation':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload area */}
      {canAddMore && (
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 ${
            dragActive
              ? 'border-blue-400 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="space-y-4">
            <div className="mx-auto w-12 h-12 text-gray-400">📁</div>
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                Upload Evidence Files
              </h3>
              <p className="text-gray-600 mb-4">
                Drag and drop files here, or click to select files
              </p>
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {isUploading ? 'Uploading...' : 'Select Files'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept={allowedTypes.join(',')}
                onChange={handleInputChange}
                className="hidden"
                disabled={isUploading}
              />
            </div>
            <div className="text-sm text-gray-500">
              <p>Supported formats: PDF, Word, Text, Images</p>
              <p>Maximum file size: {maxFileSize}MB</p>
              <p>
                Maximum files: {maxFiles} ({evidence.length} uploaded)
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Upload progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="space-y-3">
          <h4 className="font-medium text-gray-900">Uploading Files</h4>
          {Object.entries(uploadProgress).map(([fileId, progress]) => (
            <div key={fileId} className="bg-gray-50 rounded-lg p-3">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>{fileId.split('-').slice(1).join('-')}</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Upload errors */}
      {Object.keys(uploadErrors).length > 0 && (
        <div className="space-y-2">
          {Object.entries(uploadErrors).map(([fileId, error]) => (
            <div
              key={fileId}
              className="bg-red-50 border border-red-200 rounded-md p-3"
            >
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-sm font-medium text-red-800">
                    {fileId === 'limit' ? 'Upload Limit' : fileId}
                  </p>
                  <p className="text-sm text-red-600">{error}</p>
                </div>
                <button
                  onClick={() => {
                    setUploadErrors(prev => {
                      // eslint-disable-next-line @typescript-eslint/no-unused-vars
                      const { [fileId]: _, ...rest } = prev
                      return rest
                    })
                  }}
                  className="text-red-400 hover:text-red-600"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Evidence list */}
      {evidence.length > 0 && (
        <div className="space-y-4">
          <h4 className="font-medium text-gray-900">
            Uploaded Evidence ({evidence.length})
          </h4>
          <div className="grid gap-4">
            {evidence.map(item => (
              <div
                key={item.id}
                className="bg-white border border-gray-200 rounded-lg p-4"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    <div className="text-2xl">
                      {getFileIcon(item.contentType)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h5 className="font-medium text-gray-900 truncate">
                          {item.filename}
                        </h5>
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getCategoryBadgeStyle(item.evidenceType)}`}
                        >
                          {item.evidenceType}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600">
                        {formatFileSize(item.fileSize)} • Uploaded{' '}
                        {new Date(item.uploadedAt).toLocaleDateString()}
                      </p>
                      {item.description && (
                        <p className="text-sm text-gray-700 mt-1">
                          {item.description}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 ml-4">
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-700 text-sm"
                    >
                      View
                    </a>
                    <a
                      href={item.url}
                      download={item.filename}
                      className="text-blue-600 hover:text-blue-700 text-sm"
                    >
                      Download
                    </a>
                    <button
                      onClick={() => handleRemoveEvidence(item.id)}
                      className="text-red-600 hover:text-red-700 text-sm"
                    >
                      Remove
                    </button>
                  </div>
                </div>

                {/* Description editor */}
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <textarea
                    placeholder="Add a description for this evidence..."
                    defaultValue={item.description}
                    onBlur={async e => {
                      const newDescription = e.target.value.trim()
                      if (newDescription !== item.description) {
                        try {
                          // For now, just update locally - in real app would call updateEvidence
                          // await updateEvidence(iepId, item.id, { description: newDescription })
                          console.log('Description updated:', newDescription)
                        } catch (error) {
                          console.error('Failed to update description:', error)
                        }
                      }
                    }}
                    className="w-full text-sm border border-gray-300 rounded-md px-3 py-2 focus:ring-blue-500 focus:border-blue-500"
                    rows={2}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {evidence.length === 0 && !canAddMore && (
        <div className="text-center py-8 text-gray-500">
          <div className="text-4xl mb-2">📎</div>
          <p>No evidence files uploaded yet</p>
        </div>
      )}

      {/* File limit reached */}
      {!canAddMore && evidence.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <div className="flex">
            <div className="ml-3">
              <h4 className="text-sm font-medium text-yellow-800">
                File Limit Reached
              </h4>
              <p className="text-sm text-yellow-700 mt-1">
                You have reached the maximum of {maxFiles} files. Remove
                existing files to upload new ones.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
