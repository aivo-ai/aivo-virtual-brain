import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { SeatAllocation, School } from '../../api/tenantClient'

interface SeatTableProps {
  seatAllocations: SeatAllocation[]
  schools: School[]
  onReassign: (
    allocationId: string,
    fromSchoolId: string,
    toSchoolId: string,
    seatCount: number
  ) => Promise<void>
}

interface ReassignForm {
  allocationId: string
  fromSchoolId: string
  toSchoolId: string
  seatCount: number
}

export const SeatTable: React.FC<SeatTableProps> = ({
  seatAllocations,
  schools,
  onReassign,
}) => {
  const [showReassignForm, setShowReassignForm] = useState(false)
  const [reassignForm, setReassignForm] = useState<ReassignForm>({
    allocationId: '',
    fromSchoolId: '',
    toSchoolId: '',
    seatCount: 0,
  })
  const [submitting, setSubmitting] = useState(false)

  const handleReassignClick = (allocation: SeatAllocation) => {
    setReassignForm({
      allocationId: allocation.id,
      fromSchoolId: allocation.schoolId,
      toSchoolId: '',
      seatCount: Math.min(10, allocation.availableSeats),
    })
    setShowReassignForm(true)
  }

  const handleReassignSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      await onReassign(
        reassignForm.allocationId,
        reassignForm.fromSchoolId,
        reassignForm.toSchoolId,
        reassignForm.seatCount
      )
      setShowReassignForm(false)
      setReassignForm({
        allocationId: '',
        fromSchoolId: '',
        toSchoolId: '',
        seatCount: 0,
      })
    } catch (error) {
      console.error('Error reassigning seats:', error)
    } finally {
      setSubmitting(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
      case 'expired':
        return 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'
      case 'suspended':
        return 'bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200'
      default:
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
    }
  }

  const getUtilizationColor = (utilization: number) => {
    if (utilization >= 90) return 'text-red-600 dark:text-red-400'
    if (utilization >= 75) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-green-600 dark:text-green-400'
  }

  return (
    <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Seat Allocations ({seatAllocations.length})
        </h2>
      </div>

      {/* Reassign Form Modal */}
      {showReassignForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4">
            <div className="p-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Reassign Seats
              </h3>
              <form onSubmit={handleReassignSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    From School
                  </label>
                  <select
                    disabled
                    value={reassignForm.fromSchoolId}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white"
                  >
                    {schools.map(school => (
                      <option key={school.id} value={school.id}>
                        {school.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    To School *
                  </label>
                  <select
                    required
                    value={reassignForm.toSchoolId}
                    onChange={e =>
                      setReassignForm({
                        ...reassignForm,
                        toSchoolId: e.target.value,
                      })
                    }
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  >
                    <option value="">Select target school</option>
                    {schools
                      .filter(school => school.id !== reassignForm.fromSchoolId)
                      .map(school => (
                        <option key={school.id} value={school.id}>
                          {school.name}
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Number of Seats *
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={reassignForm.seatCount}
                    onChange={e =>
                      setReassignForm({
                        ...reassignForm,
                        seatCount: parseInt(e.target.value),
                      })
                    }
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                  />
                </div>

                <div className="flex justify-end space-x-4 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowReassignForm(false)}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {submitting ? 'Reassigning...' : 'Reassign Seats'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {seatAllocations.length === 0 ? (
        <div className="p-12 text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
            No seat allocations
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Purchase seats to get started with license management.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    School
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Total Seats
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Used / Available
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Utilization
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Expiry Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {seatAllocations.map(allocation => {
                  const utilization =
                    (allocation.usedSeats / allocation.totalSeats) * 100

                  return (
                    <motion.tr
                      key={allocation.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="hover:bg-gray-50 dark:hover:bg-gray-700"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {allocation.schoolName}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          Purchased:{' '}
                          {new Date(
                            allocation.purchaseDate
                          ).toLocaleDateString()}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900 dark:text-white">
                          {allocation.totalSeats.toLocaleString()}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 dark:text-white">
                          <span className="font-medium">
                            {allocation.usedSeats.toLocaleString()}
                          </span>
                          <span className="text-gray-500 dark:text-gray-400">
                            {' '}
                            /{' '}
                          </span>
                          <span className="text-green-600 dark:text-green-400">
                            {allocation.availableSeats.toLocaleString()}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div
                          className={`text-sm font-medium ${getUtilizationColor(utilization)}`}
                        >
                          {utilization.toFixed(1)}%
                        </div>
                        <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 mt-1">
                          <div
                            className={`h-2 rounded-full ${
                              utilization >= 90
                                ? 'bg-red-500'
                                : utilization >= 75
                                  ? 'bg-yellow-500'
                                  : 'bg-green-500'
                            }`}
                            style={{ width: `${Math.min(utilization, 100)}%` }}
                          />
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900 dark:text-white">
                          {new Date(allocation.expiryDate).toLocaleDateString()}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {new Date(allocation.expiryDate) > new Date()
                            ? `${Math.ceil((new Date(allocation.expiryDate).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))} days left`
                            : 'Expired'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(allocation.status)}`}
                        >
                          {allocation.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex justify-end space-x-2">
                          {allocation.availableSeats > 0 && (
                            <button
                              onClick={() => handleReassignClick(allocation)}
                              className="text-blue-600 dark:text-blue-400 hover:text-blue-900 dark:hover:text-blue-300"
                            >
                              Reassign
                            </button>
                          )}
                          <button className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-300">
                            Details
                          </button>
                        </div>
                      </td>
                    </motion.tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
