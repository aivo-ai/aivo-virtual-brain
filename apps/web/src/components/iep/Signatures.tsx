/**
 * S3-11 IEP Signatures Component
 * Electronic signature management and workflow
 */

import React, { useState, useRef, useCallback } from 'react'

interface IEPSignature {
  id: string
  userId: string
  userName: string
  userRole: 'parent' | 'teacher' | 'specialist' | 'administrator'
  signatureData: string // base64 encoded signature image
  signatureType: 'draw' | 'type' | 'upload'
  signedAt: string
}

type IEPSignatureStatus = 'pending' | 'partial' | 'complete' | 'rejected'

interface SignaturesProps {
  iepId: string
  signatures: IEPSignature[]
  currentUserRole: 'parent' | 'teacher' | 'specialist' | 'administrator'
  status: IEPSignatureStatus
  onSignatureAdded: () => void
  onSignatureRemoved: () => void
}

export function Signatures({
  iepId,
  signatures,
  currentUserRole,
  status,
  onSignatureAdded,
  onSignatureRemoved,
}: SignaturesProps) {
  const [loading, setLoading] = useState(false)

  const [isSigningModalOpen, setIsSigningModalOpen] = useState(false)
  const [signatureType, setSignatureType] = useState<
    'draw' | 'type' | 'upload'
  >('draw')
  const [typedSignature, setTypedSignature] = useState('')
  const [signatureError, setSignatureError] = useState<string | null>(null)

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const currentUserId = 'current-user' // In real app, get from auth context

  // Required signature roles for complete IEP
  const requiredRoles: Array<
    'parent' | 'teacher' | 'specialist' | 'administrator'
  > = ['parent', 'teacher', 'specialist', 'administrator']

  // Check if current user has already signed
  const currentUserSignature = signatures.find(
    sig => sig.userId === currentUserId
  )
  const hasCurrentUserSigned = !!currentUserSignature

  // Check signature completion status
  const signedRoles = new Set(signatures.map(sig => sig.userRole))
  const missingRoles = requiredRoles.filter(role => !signedRoles.has(role))
  const isComplete = missingRoles.length === 0

  // Canvas drawing functionality
  const [isDrawing, setIsDrawing] = useState(false)
  const [lastX, setLastX] = useState(0)
  const [lastY, setLastY] = useState(0)

  const startDrawing = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    setIsDrawing(true)
    setLastX(x)
    setLastY(y)
  }, [])

  const draw = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      if (!isDrawing) return

      const canvas = canvasRef.current
      const ctx = canvas?.getContext('2d')
      if (!canvas || !ctx) return

      const rect = canvas.getBoundingClientRect()
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top

      ctx.beginPath()
      ctx.moveTo(lastX, lastY)
      ctx.lineTo(x, y)
      ctx.strokeStyle = '#1f2937'
      ctx.lineWidth = 2
      ctx.lineCap = 'round'
      ctx.stroke()

      setLastX(x)
      setLastY(y)
    },
    [isDrawing, lastX, lastY]
  )

  const stopDrawing = useCallback(() => {
    setIsDrawing(false)
  }, [])

  // Clear canvas
  const clearCanvas = () => {
    const canvas = canvasRef.current
    const ctx = canvas?.getContext('2d')
    if (canvas && ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
    }
  }

  // Convert canvas to base64
  const getCanvasSignature = (): string | null => {
    const canvas = canvasRef.current
    if (!canvas) return null
    return canvas.toDataURL('image/png')
  }

  // Handle signature submission
  const handleSignature = async () => {
    try {
      setSignatureError(null)
      setLoading(true)

      let signatureData: string

      switch (signatureType) {
        case 'draw':
          const canvasData = getCanvasSignature()
          if (!canvasData) {
            setSignatureError('Please draw your signature')
            return
          }
          signatureData = canvasData
          break

        case 'type':
          if (!typedSignature.trim()) {
            setSignatureError('Please enter your name')
            return
          }
          // Generate typed signature as image
          signatureData = generateTypedSignature(typedSignature)
          break

        case 'upload':
          const file = fileInputRef.current?.files?.[0]
          if (!file) {
            setSignatureError('Please select a signature file')
            return
          }
          signatureData = await fileToBase64(file)
          break

        default:
          setSignatureError('Invalid signature type')
          return
      }

      // Mock API call
      console.log('Adding signature:', {
        iepId,
        signatureData,
        signatureType,
        userRole: currentUserRole,
      })

      setIsSigningModalOpen(false)
      resetSignatureForm()
      onSignatureAdded()
    } catch (error) {
      setSignatureError(
        error instanceof Error ? error.message : 'Failed to add signature'
      )
    } finally {
      setLoading(false)
    }
  }

  // Handle signature removal
  const handleRemoveSignature = async (signatureId: string) => {
    try {
      console.log('Removing signature:', { iepId, signatureId })
      onSignatureRemoved()
    } catch (error) {
      console.error('Failed to remove signature:', error)
    }
  }

  // Reset signature form
  const resetSignatureForm = () => {
    setSignatureType('draw')
    setTypedSignature('')
    setSignatureError(null)
    clearCanvas()
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // Generate typed signature as canvas image
  const generateTypedSignature = (text: string): string => {
    const canvas = document.createElement('canvas')
    canvas.width = 400
    canvas.height = 100
    const ctx = canvas.getContext('2d')!

    ctx.font = '32px cursive'
    ctx.fillStyle = '#1f2937'
    ctx.textAlign = 'center'
    ctx.fillText(text, 200, 60)

    return canvas.toDataURL('image/png')
  }

  // Convert file to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result as string)
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
  }

  // Get status badge style
  const getStatusBadgeStyle = (status: IEPSignatureStatus) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'partial':
        return 'bg-blue-100 text-blue-800'
      case 'complete':
        return 'bg-green-100 text-green-800'
      case 'rejected':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <h3 className="text-lg font-medium text-gray-900">
            Electronic Signatures
          </h3>
          <span
            className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusBadgeStyle(status)}`}
          >
            {status === 'pending' && 'Pending Signatures'}
            {status === 'partial' &&
              `${signatures.length}/${requiredRoles.length} Complete`}
            {status === 'complete' && 'All Signatures Complete'}
            {status === 'rejected' && 'Signature Rejected'}
          </span>
        </div>

        {!hasCurrentUserSigned && status !== 'complete' && (
          <button
            onClick={() => setIsSigningModalOpen(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
          >
            Add My Signature
          </button>
        )}
      </div>

      {/* Progress indicator */}
      <div className="mb-6">
        <div className="flex justify-between text-sm text-gray-600 mb-2">
          <span>Signature Progress</span>
          <span>
            {signatures.length} of {requiredRoles.length} complete
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{
              width: `${(signatures.length / requiredRoles.length) * 100}%`,
            }}
          ></div>
        </div>
      </div>

      {/* Required signatures list */}
      <div className="space-y-4">
        {requiredRoles.map(role => {
          const signature = signatures.find(sig => sig.userRole === role)
          return (
            <div
              key={role}
              className={`flex items-center justify-between p-4 border rounded-lg ${
                signature
                  ? 'border-green-200 bg-green-50'
                  : 'border-gray-200 bg-gray-50'
              }`}
            >
              <div className="flex items-center space-x-3">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center ${
                    signature
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-300 text-gray-600'
                  }`}
                >
                  {signature ? '✓' : role.charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-gray-900 capitalize">{role}</p>
                  {signature ? (
                    <p className="text-sm text-gray-600">
                      Signed by {signature.userName} on{' '}
                      {new Date(signature.signedAt).toLocaleDateString()}
                    </p>
                  ) : (
                    <p className="text-sm text-gray-500">Signature required</p>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {signature && (
                  <>
                    <button
                      onClick={() => {
                        // Show signature in modal
                        const img = new Image()
                        img.src = signature.signatureData
                        const win = window.open('', '_blank')
                        win?.document.write(
                          `<img src="${signature.signatureData}" alt="Signature" style="max-width: 100%; height: auto;">`
                        )
                      }}
                      className="text-blue-600 hover:text-blue-700 text-sm"
                    >
                      View
                    </button>
                    {signature.userId === currentUserId && (
                      <button
                        onClick={() => handleRemoveSignature(signature.id)}
                        className="text-red-600 hover:text-red-700 text-sm"
                      >
                        Remove
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Missing signatures warning */}
      {missingRoles.length > 0 && (
        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
          <div className="flex">
            <div className="ml-3">
              <h4 className="text-sm font-medium text-yellow-800">
                Signatures Required
              </h4>
              <p className="text-sm text-yellow-700 mt-1">
                The following signatures are still required:{' '}
                {missingRoles.join(', ')}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Signature completion */}
      {isComplete && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-md">
          <div className="flex">
            <div className="ml-3">
              <h4 className="text-sm font-medium text-green-800">
                All Signatures Complete
              </h4>
              <p className="text-sm text-green-700 mt-1">
                This IEP has been signed by all required parties and is ready
                for implementation.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Signature Modal */}
      {isSigningModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  Add Your Signature
                </h3>
                <button
                  onClick={() => {
                    setIsSigningModalOpen(false)
                    resetSignatureForm()
                  }}
                  className="text-gray-400 hover:text-gray-600"
                >
                  ✕
                </button>
              </div>

              {/* Signature type selector */}
              <div className="mb-4">
                <div className="flex space-x-4 border-b">
                  {(['draw', 'type', 'upload'] as const).map(type => (
                    <button
                      key={type}
                      onClick={() => setSignatureType(type)}
                      className={`pb-2 px-1 text-sm font-medium border-b-2 ${
                        signatureType === type
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {type === 'draw' && 'Draw'}
                      {type === 'type' && 'Type'}
                      {type === 'upload' && 'Upload'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Signature input area */}
              <div className="mb-6">
                {signatureType === 'draw' && (
                  <div>
                    <div className="border-2 border-gray-300 rounded-lg">
                      <canvas
                        ref={canvasRef}
                        width={600}
                        height={200}
                        className="w-full cursor-crosshair"
                        onMouseDown={startDrawing}
                        onMouseMove={draw}
                        onMouseUp={stopDrawing}
                        onMouseLeave={stopDrawing}
                      />
                    </div>
                    <div className="flex justify-between mt-2">
                      <p className="text-sm text-gray-600">
                        Draw your signature above
                      </p>
                      <button
                        onClick={clearCanvas}
                        className="text-sm text-blue-600 hover:text-blue-700"
                      >
                        Clear
                      </button>
                    </div>
                  </div>
                )}

                {signatureType === 'type' && (
                  <div>
                    <input
                      type="text"
                      value={typedSignature}
                      onChange={e => setTypedSignature(e.target.value)}
                      placeholder="Enter your full name"
                      className="w-full p-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    />
                    {typedSignature && (
                      <div className="mt-2 p-3 border border-gray-200 rounded-md bg-gray-50">
                        <p className="text-sm text-gray-600 mb-2">Preview:</p>
                        <div className="text-2xl font-cursive text-gray-800">
                          {typedSignature}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {signatureType === 'upload' && (
                  <div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      className="w-full p-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
                    />
                    <p className="text-sm text-gray-600 mt-2">
                      Upload an image of your signature (PNG, JPG, or GIF)
                    </p>
                  </div>
                )}
              </div>

              {/* Error message */}
              {signatureError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                  <p className="text-sm text-red-600">{signatureError}</p>
                </div>
              )}

              {/* Legal notice */}
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
                <p className="text-sm text-blue-800">
                  <strong>Legal Notice:</strong> By signing this document
                  electronically, you agree that your electronic signature has
                  the same legal effect as a handwritten signature and that you
                  are the person authorized to sign this document.
                </p>
              </div>

              {/* Action buttons */}
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => {
                    setIsSigningModalOpen(false)
                    resetSignatureForm()
                  }}
                  className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSignature}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? 'Adding Signature...' : 'Add Signature'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
