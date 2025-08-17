/**
 * S3-12 SLP System Route
 * Integration point for SLP system in main application
 */

import { useParams, useNavigate } from 'react-router-dom'
import { SimpleSLPFlow } from '../components/slp/SimpleSLPFlow'

export function SLPPage() {
  const { studentId } = useParams<{ studentId: string }>()
  const navigate = useNavigate()

  const handleExit = () => {
    navigate('/dashboard') // Or appropriate parent route
  }

  if (!studentId) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">
            Missing Student ID
          </h1>
          <p className="text-gray-600 mb-4">
            A valid student ID is required to access the SLP system.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return <SimpleSLPFlow studentId={studentId} onExit={handleExit} />
}
