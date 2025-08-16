import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import {
  tenantClient,
  RosterImportResult,
  School,
} from '../../api/tenantClient'
import { RosterTable } from '../../components/tables'

interface UploadProgress {
  file: File | null
  progress: number
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error'
  error?: string
}

export const RosterImport: React.FC = () => {
  const [schools, setSchools] = useState<School[]>([])
  const [importHistory, setImportHistory] = useState<RosterImportResult[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedSchool, setSelectedSchool] = useState<string>('')
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({
    file: null,
    progress: 0,
    status: 'idle',
  })
  const [dragActive, setDragActive] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [schoolList, history] = await Promise.all([
        tenantClient.getSchools(),
        tenantClient.getRosterImportHistory(),
      ])
      setSchools(schoolList)
      setImportHistory(history)
    } catch (err) {
      setError('Failed to load data')
      console.error('Error loading data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0])
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0])
    }
  }

  const handleFile = (file: File) => {
    if (!file.name.endsWith('.csv')) {
      setError('Please upload a CSV file')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      // 10MB limit
      setError('File size must be less than 10MB')
      return
    }

    setUploadProgress({
      file,
      progress: 0,
      status: 'idle',
    })
    setError(null)
  }

  const handleUpload = async () => {
    if (!uploadProgress.file || !selectedSchool) {
      setError('Please select a school and file to upload')
      return
    }

    setUploadProgress(prev => ({ ...prev, status: 'uploading', progress: 0 }))

    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => ({
          ...prev,
          progress: Math.min(prev.progress + Math.random() * 20, 90),
        }))
      }, 200)

      const result = await tenantClient.uploadRosterFile(
        uploadProgress.file,
        selectedSchool
      )

      clearInterval(progressInterval)
      setUploadProgress(prev => ({
        ...prev,
        status: 'processing',
        progress: 100,
      }))

      // Simulate processing time
      setTimeout(() => {
        setUploadProgress(prev => ({ ...prev, status: 'completed' }))
        setImportHistory([result, ...importHistory])

        // Reset form
        setTimeout(() => {
          setUploadProgress({
            file: null,
            progress: 0,
            status: 'idle',
          })
          setSelectedSchool('')
        }, 2000)
      }, 1500)
    } catch (err) {
      setUploadProgress(prev => ({
        ...prev,
        status: 'error',
        error: 'Upload failed. Please try again.',
      }))
      console.error('Upload error:', err)
    }
  }

  const downloadTemplate = () => {
    const headers = [
      'firstName',
      'lastName',
      'email',
      'role',
      'gradeLevel',
      'classroomId',
      'parentEmail',
      'dateOfBirth',
    ]

    const csvContent =
      headers.join(',') +
      '\n' +
      'John,Doe,john.doe@example.com,student,5,5A,parent@example.com,2015-08-15\n' +
      'Jane,Smith,jane.smith@school.edu,teacher,,5A,,\n' +
      'Bob,Johnson,bob.johnson@parent.com,parent,,,,'

    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'roster_template.csv'
    link.click()
    window.URL.revokeObjectURL(url)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'uploading':
        return (
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
        )
      case 'processing':
        return (
          <svg
            className="w-5 h-5 text-yellow-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        )
      case 'completed':
        return (
          <svg
            className="w-5 h-5 text-green-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        )
      case 'error':
        return (
          <svg
            className="w-5 h-5 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        )
      default:
        return null
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link
                to="/district"
                className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M15 19l-7-7 7-7"
                  />
                </svg>
              </Link>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  Roster Import
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  Upload and manage student and staff rosters
                </p>
              </div>
            </div>
            <button
              onClick={downloadTemplate}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Download Template
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-red-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-red-800 dark:text-red-200">
                  {error}
                </p>
              </div>
              <div className="ml-auto pl-3">
                <div className="-mx-1.5 -my-1.5">
                  <button
                    onClick={() => setError(null)}
                    className="inline-flex bg-red-50 dark:bg-red-900/20 rounded-md p-1.5 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/40"
                  >
                    <span className="sr-only">Dismiss</span>
                    <svg
                      className="h-4 w-4"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Upload Section */}
        <FadeInWhenVisible>
          <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 mb-8">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Upload Roster File
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Upload a CSV file with student and staff information. Use our
                template for proper formatting.
              </p>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label
                    htmlFor="school"
                    className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
                  >
                    Select School *
                  </label>
                  <select
                    id="school"
                    value={selectedSchool}
                    onChange={e => setSelectedSchool(e.target.value)}
                    className="block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">Choose a school</option>
                    {schools.map(school => (
                      <option key={school.id} value={school.id}>
                        {school.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* File Upload Area */}
              <div
                className={`relative border-2 border-dashed rounded-lg p-6 transition-colors ${
                  dragActive
                    ? 'border-blue-400 bg-blue-50 dark:bg-blue-900/20'
                    : uploadProgress.file
                      ? 'border-green-400 bg-green-50 dark:bg-green-900/20'
                      : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <div className="text-center">
                  {uploadProgress.file ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-center">
                        {getStatusIcon(uploadProgress.status)}
                        <span className="ml-2 text-sm font-medium text-gray-900 dark:text-white">
                          {uploadProgress.file.name}
                        </span>
                      </div>

                      {uploadProgress.status !== 'idle' && (
                        <div className="space-y-2">
                          <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                            <div
                              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${uploadProgress.progress}%` }}
                            />
                          </div>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            {uploadProgress.status === 'uploading' &&
                              'Uploading file...'}
                            {uploadProgress.status === 'processing' &&
                              'Processing roster data...'}
                            {uploadProgress.status === 'completed' &&
                              'Import completed successfully!'}
                            {uploadProgress.status === 'error' &&
                              (uploadProgress.error || 'Upload failed')}
                          </p>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div>
                      <svg
                        className="mx-auto h-12 w-12 text-gray-400"
                        stroke="currentColor"
                        fill="none"
                        viewBox="0 0 48 48"
                      >
                        <path
                          d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                          strokeWidth={2}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      <div className="mt-4">
                        <label htmlFor="file-upload" className="cursor-pointer">
                          <span className="mt-2 block text-sm font-medium text-gray-900 dark:text-white">
                            Drop your CSV file here, or{' '}
                            <span className="text-blue-600 hover:text-blue-500">
                              browse
                            </span>
                          </span>
                          <input
                            id="file-upload"
                            name="file-upload"
                            type="file"
                            className="sr-only"
                            accept=".csv"
                            onChange={handleFileInput}
                          />
                        </label>
                        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                          CSV files up to 10MB
                        </p>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {uploadProgress.file && uploadProgress.status === 'idle' && (
                <div className="mt-6 flex justify-end">
                  <button
                    onClick={handleUpload}
                    disabled={!selectedSchool}
                    className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Upload Roster
                  </button>
                </div>
              )}
            </div>
          </div>
        </FadeInWhenVisible>

        {/* Import History */}
        <FadeInWhenVisible delay={0.2}>
          <RosterTable importHistory={importHistory} />
        </FadeInWhenVisible>
      </div>
    </div>
  )
}
