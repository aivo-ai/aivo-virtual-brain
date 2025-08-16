import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import { tenantClient, SeatAllocation, School } from '../../api/tenantClient'
import { SeatTable } from '../../components/tables'

interface PurchaseFormData {
  schoolId: string
  seatCount: number
  duration: number // months
}

const initialPurchaseForm: PurchaseFormData = {
  schoolId: '',
  seatCount: 50,
  duration: 12,
}

export const Seats: React.FC = () => {
  const [seatAllocations, setSeatAllocations] = useState<SeatAllocation[]>([])
  const [schools, setSchools] = useState<School[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showPurchaseForm, setShowPurchaseForm] = useState(false)
  const [purchaseForm, setPurchaseForm] =
    useState<PurchaseFormData>(initialPurchaseForm)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [allocations, schoolList] = await Promise.all([
        tenantClient.getSeatAllocations(),
        tenantClient.getSchools(),
      ])
      setSeatAllocations(allocations)
      setSchools(schoolList)
    } catch (err) {
      setError('Failed to load seat allocations')
      console.error('Error loading data:', err)
    } finally {
      setLoading(false)
    }
  }

  const handlePurchaseSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)

    try {
      const newAllocation = await tenantClient.purchaseSeats({
        schoolId: purchaseForm.schoolId,
        seatCount: purchaseForm.seatCount,
        duration: purchaseForm.duration,
      })
      setSeatAllocations([...seatAllocations, newAllocation])
      setPurchaseForm(initialPurchaseForm)
      setShowPurchaseForm(false)
    } catch (err) {
      setError('Failed to purchase seats')
      console.error('Error purchasing seats:', err)
    } finally {
      setSubmitting(false)
    }
  }

  const handleReassignSeats = async (
    allocationId: string,
    fromSchoolId: string,
    toSchoolId: string,
    seatCount: number
  ) => {
    try {
      const updatedAllocation = await tenantClient.reassignSeats(allocationId, {
        fromSchoolId,
        toSchoolId,
        seatCount,
      })
      setSeatAllocations(
        seatAllocations.map(a =>
          a.id === allocationId ? updatedAllocation : a
        )
      )
    } catch (err) {
      setError('Failed to reassign seats')
      console.error('Error reassigning seats:', err)
    }
  }

  const calculateSeatCost = () => {
    const basePrice = 15 // $15 per seat per month
    const totalCost = purchaseForm.seatCount * basePrice * purchaseForm.duration

    // Volume discounts
    let discount = 0
    if (purchaseForm.seatCount >= 500)
      discount = 0.2 // 20% for 500+
    else if (purchaseForm.seatCount >= 200)
      discount = 0.15 // 15% for 200+
    else if (purchaseForm.seatCount >= 100) discount = 0.1 // 10% for 100+

    // Duration discounts
    if (purchaseForm.duration >= 24)
      discount += 0.1 // Additional 10% for 2+ years
    else if (purchaseForm.duration >= 12) discount += 0.05 // Additional 5% for 1+ year

    const finalCost = totalCost * (1 - Math.min(discount, 0.3)) // Max 30% discount

    return {
      subtotal: totalCost,
      discount: totalCost - finalCost,
      total: finalCost,
      perSeat: finalCost / purchaseForm.seatCount,
    }
  }

  const totalSeats = seatAllocations.reduce(
    (sum, allocation) => sum + allocation.totalSeats,
    0
  )
  const usedSeats = seatAllocations.reduce(
    (sum, allocation) => sum + allocation.usedSeats,
    0
  )
  const availableSeats = totalSeats - usedSeats
  const utilizationRate = totalSeats > 0 ? (usedSeats / totalSeats) * 100 : 0

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
                  Seat Management
                </h1>
                <p className="text-gray-600 dark:text-gray-400 mt-1">
                  Purchase and manage seat licenses
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowPurchaseForm(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Purchase Seats
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

        {/* Overview Stats */}
        <FadeInWhenVisible>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center text-blue-600 dark:text-blue-400">
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
                          d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                        />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Total Seats
                    </h3>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {totalSeats.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center text-green-600 dark:text-green-400">
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
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Used Seats
                    </h3>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {usedSeats.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900 rounded-lg flex items-center justify-center text-yellow-600 dark:text-yellow-400">
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
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Available
                    </h3>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {availableSeats.toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white dark:bg-gray-800 overflow-hidden shadow-lg rounded-lg border border-gray-200 dark:border-gray-700">
              <div className="p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div
                      className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        utilizationRate > 90
                          ? 'bg-red-100 dark:bg-red-900 text-red-600 dark:text-red-400'
                          : utilizationRate > 75
                            ? 'bg-yellow-100 dark:bg-yellow-900 text-yellow-600 dark:text-yellow-400'
                            : 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400'
                      }`}
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
                          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                        />
                      </svg>
                    </div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      Utilization
                    </h3>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {utilizationRate.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </FadeInWhenVisible>

        {/* Purchase Form */}
        {showPurchaseForm && (
          <FadeInWhenVisible>
            <div className="bg-white dark:bg-gray-800 shadow-lg rounded-lg border border-gray-200 dark:border-gray-700 mb-8">
              <div className="p-6 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                  Purchase Additional Seats
                </h2>
              </div>
              <form onSubmit={handlePurchaseSubmit} className="p-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
                  <div>
                    <label
                      htmlFor="schoolId"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                    >
                      School *
                    </label>
                    <select
                      id="schoolId"
                      required
                      value={purchaseForm.schoolId}
                      onChange={e =>
                        setPurchaseForm({
                          ...purchaseForm,
                          schoolId: e.target.value,
                        })
                      }
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    >
                      <option value="">Select a school</option>
                      {schools.map(school => (
                        <option key={school.id} value={school.id}>
                          {school.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="seatCount"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                    >
                      Number of Seats *
                    </label>
                    <input
                      type="number"
                      id="seatCount"
                      min="1"
                      required
                      value={purchaseForm.seatCount}
                      onChange={e =>
                        setPurchaseForm({
                          ...purchaseForm,
                          seatCount: parseInt(e.target.value),
                        })
                      }
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="duration"
                      className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                    >
                      Duration (months) *
                    </label>
                    <select
                      id="duration"
                      required
                      value={purchaseForm.duration}
                      onChange={e =>
                        setPurchaseForm({
                          ...purchaseForm,
                          duration: parseInt(e.target.value),
                        })
                      }
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                    >
                      <option value={1}>1 month</option>
                      <option value={3}>3 months</option>
                      <option value={6}>6 months</option>
                      <option value={12}>12 months</option>
                      <option value={24}>24 months</option>
                      <option value={36}>36 months</option>
                    </select>
                  </div>
                </div>

                {/* Pricing Breakdown */}
                {purchaseForm.seatCount > 0 && (
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 mb-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-3">
                      Pricing Breakdown
                    </h3>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400">
                          {purchaseForm.seatCount} seats × ${15}/month ×{' '}
                          {purchaseForm.duration} months
                        </span>
                        <span className="text-gray-900 dark:text-white">
                          ${calculateSeatCost().subtotal.toLocaleString()}
                        </span>
                      </div>
                      {calculateSeatCost().discount > 0 && (
                        <div className="flex justify-between text-sm">
                          <span className="text-green-600 dark:text-green-400">
                            Volume & Duration Discount
                          </span>
                          <span className="text-green-600 dark:text-green-400">
                            -${calculateSeatCost().discount.toLocaleString()}
                          </span>
                        </div>
                      )}
                      <div className="border-t border-gray-200 dark:border-gray-600 pt-2">
                        <div className="flex justify-between font-medium">
                          <span className="text-gray-900 dark:text-white">
                            Total
                          </span>
                          <span className="text-gray-900 dark:text-white">
                            ${calculateSeatCost().total.toLocaleString()}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
                          <span>Cost per seat</span>
                          <span>${calculateSeatCost().perSeat.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div className="flex justify-end space-x-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowPurchaseForm(false)
                      setPurchaseForm(initialPurchaseForm)
                    }}
                    className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {submitting
                      ? 'Processing...'
                      : `Purchase Seats - $${calculateSeatCost().total.toLocaleString()}`}
                  </button>
                </div>
              </form>
            </div>
          </FadeInWhenVisible>
        )}

        {/* Seat Allocations Table */}
        <FadeInWhenVisible>
          <SeatTable
            seatAllocations={seatAllocations}
            schools={schools}
            onReassign={handleReassignSeats}
          />
        </FadeInWhenVisible>
      </div>
    </div>
  )
}
