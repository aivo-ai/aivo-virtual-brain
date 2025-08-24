import React, { useState, useEffect } from 'react'
import {
  courseworkClient,
  CourseworkUploadRequest,
  OCRPreviewResponse,
} from '../../api/courseworkClient'
import { consentClient, ConsentRecord } from '../../api/consentClient'
import { UploadDropzone } from '../../components/library/UploadDropzone'

interface UploadForm {
  title: string
  description: string
  type: string
  subject: string
  topic: string
  gradeBand: string
  tags: string[]
  isPublic: boolean
  attachToLearner: boolean
}

const Upload: React.FC = () => {
  const [consent, setConsent] = useState<ConsentResponse | null>(null)
  const [form, setForm] = useState<UploadForm>({
    title: '',
    description: '',
    type: 'document',
    subject: '',
    topic: '',
    gradeBand: '',
    tags: [],
    isPublic: false,
    attachToLearner: false,
  })
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [ocrPreview, setOcrPreview] = useState<OCRPreviewResponse | null>(null)
  const [uploading, setUploading] = useState(false)
  const [loadingConsent, setLoadingConsent] = useState(true)
  const [loadingOcr, setLoadingOcr] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [tagInput, setTagInput] = useState('')

  const subjects = [
    'Mathematics',
    'Science',
    'English Language Arts',
    'Social Studies',
    'History',
    'Geography',
    'Art',
    'Music',
    'Physical Education',
    'Computer Science',
    'Foreign Languages',
    'Life Skills',
  ]

  const gradeBands = ['K-2', '3-5', '6-8', '9-12', 'Adult']

  const fileTypes = [
    { value: 'document', label: 'Document' },
    { value: 'image', label: 'Image' },
    { value: 'video', label: 'Video' },
    { value: 'audio', label: 'Audio' },
    { value: 'interactive', label: 'Interactive Content' },
    { value: 'assessment', label: 'Assessment' },
    { value: 'worksheet', label: 'Worksheet' },
    { value: 'presentation', label: 'Presentation' },
  ]

  useEffect(() => {
    loadConsent()
  }, [])

  const loadConsent = async () => {
    try {
      setLoadingConsent(true)
      const consentData = await consentClient.getConsent()
      setConsent(consentData)
    } catch (err) {
      setError('Failed to load consent information')
    } finally {
      setLoadingConsent(false)
    }
  }

  const handleFileSelect = async (file: File) => {
    setSelectedFile(file)
    setOcrPreview(null)
    setError(null)

    // Auto-detect file type based on MIME type
    if (file.type.startsWith('image/')) {
      setForm(prev => ({ ...prev, type: 'image' }))
    } else if (file.type.startsWith('video/')) {
      setForm(prev => ({ ...prev, type: 'video' }))
    } else if (file.type.startsWith('audio/')) {
      setForm(prev => ({ ...prev, type: 'audio' }))
    } else if (file.type.includes('pdf') || file.type.includes('document')) {
      setForm(prev => ({ ...prev, type: 'document' }))
    }

    // Auto-populate title from filename if empty
    if (!form.title) {
      const nameWithoutExt = file.name.replace(/\.[^/.]+$/, '')
      setForm(prev => ({ ...prev, title: nameWithoutExt }))
    }

    // Try OCR preview for supported file types
    if (file.type.includes('pdf') || file.type.startsWith('image/')) {
      try {
        setLoadingOcr(true)
        const preview = await courseworkClient.getOcrPreview(file)
        setOcrPreview(preview)

        // Auto-populate form fields from OCR if empty
        if (preview.suggestedMetadata) {
          const { title, subject, topic, description, tags } =
            preview.suggestedMetadata
          setForm(prev => ({
            ...prev,
            title: title || prev.title,
            subject: subject || prev.subject,
            topic: topic || prev.topic,
            description: description || prev.description,
            tags: tags?.length ? tags : prev.tags,
          }))
        }
      } catch (err) {
        console.warn('OCR preview failed:', err)
        // Don't show error for OCR failures - it's optional
      } finally {
        setLoadingOcr(false)
      }
    }
  }

  const handleFormChange = (field: keyof UploadForm, value: any) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const handleAddTag = () => {
    if (tagInput.trim() && !form.tags.includes(tagInput.trim())) {
      setForm(prev => ({
        ...prev,
        tags: [...prev.tags, tagInput.trim()],
      }))
      setTagInput('')
    }
  }

  const handleRemoveTag = (tagToRemove: string) => {
    setForm(prev => ({
      ...prev,
      tags: prev.tags.filter(tag => tag !== tagToRemove),
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!selectedFile) {
      setError('Please select a file to upload')
      return
    }

    if (!form.title.trim()) {
      setError('Please provide a title for the asset')
      return
    }

    // Check media consent for non-public uploads
    if (!form.isPublic && !consent?.mediaConsent) {
      setError(
        'Media consent is required to upload private content. Please update your consent preferences.'
      )
      return
    }

    setUploading(true)
    setError(null)
    setSuccess(null)

    try {
      const uploadRequest: CourseworkUploadRequest = {
        title: form.title.trim(),
        description: form.description.trim() || undefined,
        type: form.type,
        metadata: {
          subject: form.subject || undefined,
          topic: form.topic || undefined,
          gradeBand: form.gradeBand || undefined,
        },
        tags: form.tags.length > 0 ? form.tags : undefined,
        isPublic: form.isPublic,
      }

      const result = await courseworkClient.uploadAsset(
        selectedFile,
        uploadRequest
      )

      // Attach to learner if requested
      if (form.attachToLearner) {
        await courseworkClient.attachToLearner(
          result.assetId,
          'current-learner'
        ) // Would need actual learner ID
      }

      setSuccess(`Successfully uploaded "${form.title}"`)

      // Reset form
      setForm({
        title: '',
        description: '',
        type: 'document',
        subject: '',
        topic: '',
        gradeBand: '',
        tags: [],
        isPublic: false,
        attachToLearner: false,
      })
      setSelectedFile(null)
      setOcrPreview(null)

      // Redirect to library after a delay
      setTimeout(() => {
        window.location.href = '/library'
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload asset')
    } finally {
      setUploading(false)
    }
  }

  if (loadingConsent) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading consent information...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="mx-auto max-w-4xl px-4">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <a
              href="/library"
              className="inline-flex items-center text-sm text-gray-500 hover:text-gray-700"
            >
              <svg
                className="mr-1 h-4 w-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 19l-7-7m0 0l7-7m0 7h18"
                />
              </svg>
              Back to Library
            </a>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Upload Asset</h1>
          <p className="mt-2 text-lg text-gray-600">
            Add new learning materials to your library
          </p>
        </div>

        {/* Consent Warning */}
        {!consent?.mediaConsent && (
          <div className="mb-6 rounded-lg bg-yellow-50 p-4">
            <div className="flex">
              <svg
                className="h-5 w-5 text-yellow-400 mt-0.5 mr-3"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              <div>
                <h3 className="text-sm font-medium text-yellow-800">
                  Media Consent Required
                </h3>
                <p className="mt-1 text-sm text-yellow-700">
                  You can only upload public content without media consent. To
                  upload private content,{' '}
                  <a
                    href="/settings/consent"
                    className="underline hover:text-yellow-900"
                  >
                    update your consent preferences
                  </a>
                  .
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error/Success Messages */}
        {error && (
          <div className="mb-6 rounded-lg bg-red-50 p-4">
            <div className="flex">
              <svg
                className="h-5 w-5 text-red-400 mt-0.5 mr-3"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div className="mb-6 rounded-lg bg-green-50 p-4">
            <div className="flex">
              <svg
                className="h-5 w-5 text-green-400 mt-0.5 mr-3"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                  clipRule="evenodd"
                />
              </svg>
              <p className="text-sm text-green-700">{success}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* File Upload */}
          <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Select File
            </h2>
            <UploadDropzone
              onFileSelect={handleFileSelect}
              selectedFile={selectedFile}
              loading={loadingOcr}
            />
          </div>

          {/* OCR Preview */}
          {ocrPreview && (
            <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">
                Content Preview
              </h2>
              <div className="space-y-4">
                {ocrPreview.extractedText && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">
                      Extracted Text:
                    </h3>
                    <div className="bg-gray-50 rounded-md p-3 text-sm text-gray-900 max-h-40 overflow-y-auto">
                      {ocrPreview.extractedText}
                    </div>
                  </div>
                )}
                {ocrPreview.confidence !== undefined && (
                  <div>
                    <span className="text-sm text-gray-600">
                      Confidence: {Math.round(ocrPreview.confidence * 100)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Asset Details */}
          <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">
              Asset Details
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Title */}
              <div className="md:col-span-2">
                <label
                  htmlFor="title"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Title *
                </label>
                <input
                  type="text"
                  id="title"
                  value={form.title}
                  onChange={e => handleFormChange('title', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="Enter a descriptive title"
                  required
                />
              </div>

              {/* Description */}
              <div className="md:col-span-2">
                <label
                  htmlFor="description"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Description
                </label>
                <textarea
                  id="description"
                  value={form.description}
                  onChange={e =>
                    handleFormChange('description', e.target.value)
                  }
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="Describe the content and purpose of this asset"
                />
              </div>

              {/* Type */}
              <div>
                <label
                  htmlFor="type"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Type
                </label>
                <select
                  id="type"
                  value={form.type}
                  onChange={e => handleFormChange('type', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  {fileTypes.map(type => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Subject */}
              <div>
                <label
                  htmlFor="subject"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Subject
                </label>
                <select
                  id="subject"
                  value={form.subject}
                  onChange={e => handleFormChange('subject', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">Select subject</option>
                  {subjects.map(subject => (
                    <option key={subject} value={subject}>
                      {subject}
                    </option>
                  ))}
                </select>
              </div>

              {/* Topic */}
              <div>
                <label
                  htmlFor="topic"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Topic
                </label>
                <input
                  type="text"
                  id="topic"
                  value={form.topic}
                  onChange={e => handleFormChange('topic', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="Enter specific topic"
                />
              </div>

              {/* Grade Band */}
              <div>
                <label
                  htmlFor="gradeBand"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Grade Band
                </label>
                <select
                  id="gradeBand"
                  value={form.gradeBand}
                  onChange={e => handleFormChange('gradeBand', e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">Select grade band</option>
                  {gradeBands.map(gradeBand => (
                    <option key={gradeBand} value={gradeBand}>
                      Grade {gradeBand}
                    </option>
                  ))}
                </select>
              </div>

              {/* Tags */}
              <div className="md:col-span-2">
                <label
                  htmlFor="tags"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Tags
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={tagInput}
                    onChange={e => setTagInput(e.target.value)}
                    onKeyPress={e =>
                      e.key === 'Enter' && (e.preventDefault(), handleAddTag())
                    }
                    className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    placeholder="Add tags to help categorize this asset"
                  />
                  <button
                    type="button"
                    onClick={handleAddTag}
                    className="rounded-md bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500"
                  >
                    Add
                  </button>
                </div>
                {form.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {form.tags.map(tag => (
                      <span
                        key={tag}
                        className="inline-flex items-center rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-800"
                      >
                        {tag}
                        <button
                          type="button"
                          onClick={() => handleRemoveTag(tag)}
                          className="ml-1 h-3 w-3 text-blue-600 hover:text-blue-800"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Privacy & Attachment Options */}
          <div className="bg-white rounded-lg shadow-sm ring-1 ring-gray-900/5 p-6">
            <h2 className="text-lg font-medium text-gray-900 mb-4">Options</h2>
            <div className="space-y-4">
              {/* Public/Private */}
              <div className="flex items-start">
                <div className="flex items-center h-5">
                  <input
                    id="isPublic"
                    type="checkbox"
                    checked={form.isPublic}
                    onChange={e =>
                      handleFormChange('isPublic', e.target.checked)
                    }
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                </div>
                <div className="ml-3 text-sm">
                  <label
                    htmlFor="isPublic"
                    className="font-medium text-gray-700"
                  >
                    Make this asset public
                  </label>
                  <p className="text-gray-500">
                    Public assets can be discovered and used by other educators
                  </p>
                </div>
              </div>

              {/* Attach to Learner */}
              <div className="flex items-start">
                <div className="flex items-center h-5">
                  <input
                    id="attachToLearner"
                    type="checkbox"
                    checked={form.attachToLearner}
                    onChange={e =>
                      handleFormChange('attachToLearner', e.target.checked)
                    }
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                </div>
                <div className="ml-3 text-sm">
                  <label
                    htmlFor="attachToLearner"
                    className="font-medium text-gray-700"
                  >
                    Attach to current learner progress
                  </label>
                  <p className="text-gray-500">
                    This asset will be linked to the learner's current learning
                    path
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Submit */}
          <div className="flex justify-end space-x-3">
            <a
              href="/library"
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              Cancel
            </a>
            <button
              type="submit"
              disabled={uploading || !selectedFile || !form.title.trim()}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {uploading ? 'Uploading...' : 'Upload Asset'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Upload
