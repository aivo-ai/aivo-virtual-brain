import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  CreditCard,
  Shield,
  CheckCircle,
  AlertTriangle,
  Clock,
  Lock,
} from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import { UseOnboardingReturn } from '../../hooks/useOnboarding'

interface GuardianVerifyStepProps {
  onboardingData: UseOnboardingReturn
  onNext: () => void
  onBack: () => void
}

interface VerificationStatus {
  verification_id?: string
  status:
    | 'pending'
    | 'in_progress'
    | 'verified'
    | 'failed'
    | 'expired'
    | 'rate_limited'
  method?: 'micro_charge' | 'kba'
  attempts_remaining: number
  next_attempt_at?: string
  failure_reason?: string
  can_retry: boolean
}

interface MicroChargeData {
  client_secret: string
  publishable_key: string
  amount_cents: number
  currency: string
}

interface KBAData {
  session_id: string
  session_url: string
  expires_at: string
  max_questions: number
}

export const GuardianVerifyStep: React.FC<GuardianVerifyStepProps> = ({
  onboardingData,
  onNext,
  onBack,
}) => {
  const { state, updateGuardianVerification } = onboardingData
  const [selectedMethod, setSelectedMethod] = useState<
    'micro_charge' | 'kba' | null
  >(null)
  const [verificationStatus, setVerificationStatus] =
    useState<VerificationStatus>({
      status: 'pending',
      attempts_remaining: 3,
      can_retry: true,
    })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [microChargeData, setMicroChargeData] =
    useState<MicroChargeData | null>(null)
  const [kbaData, setKBAData] = useState<KBAData | null>(null)
  const [stripeElements, setStripeElements] = useState<any>(null)

  // Check existing verification status on component mount
  useEffect(() => {
    checkExistingVerification()
  }, [])

  // Load Stripe if micro-charge method is selected
  useEffect(() => {
    if (selectedMethod === 'micro_charge' && microChargeData) {
      loadStripeElements()
    }
  }, [selectedMethod, microChargeData])

  const checkExistingVerification = async () => {
    if (!state.guardian?.userId) return

    try {
      const response = await fetch(
        `/api/v1/guardian/${state.guardian.userId}/verification`
      )
      if (response.ok) {
        const data = await response.json()

        if (data.is_verified) {
          // Guardian is already verified
          setVerificationStatus({
            status: 'verified',
            attempts_remaining: 3,
            can_retry: false,
          })
          updateGuardianVerification({
            isVerified: true,
            verifiedAt: data.verified_at,
            method: data.verification_method,
          })
        }
      }
    } catch (error) {
      console.error('Failed to check verification status:', error)
    }
  }

  const startVerification = async (method: 'micro_charge' | 'kba') => {
    if (!state.guardian?.userId) {
      setError('Guardian information is required')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const verificationRequest = {
        guardian_user_id: state.guardian.userId,
        method: method,
        country_code: determineCountryCode(),
        metadata: {
          tenant_id: state.tenantId || 'default',
          first_name: state.guardian.firstName,
          last_name: state.guardian.lastName,
          zip_code: state.guardian.zipCode,
          state: state.guardian.state,
          city: state.guardian.city,
        },
        coppa_compliant: true,
      }

      const response = await fetch('/api/v1/verify/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(verificationRequest),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(
          errorData.detail?.error || 'Failed to start verification'
        )
      }

      const data = await response.json()

      setVerificationStatus({
        verification_id: data.verification_id,
        status: data.status,
        method: data.method,
        attempts_remaining: data.attempts_remaining,
        can_retry: true,
      })

      if (method === 'micro_charge' && data.micro_charge) {
        setMicroChargeData(data.micro_charge)
      } else if (method === 'kba' && data.kba) {
        setKBAData(data.kba)
        // Redirect to KBA session
        window.open(data.kba.session_url, '_blank')
        startKBAPolling(data.verification_id)
      }
    } catch (error) {
      console.error('Verification start failed:', error)
      setError(
        error instanceof Error ? error.message : 'Failed to start verification'
      )
    } finally {
      setIsLoading(false)
    }
  }

  const loadStripeElements = async () => {
    if (!microChargeData) return

    try {
      // Load Stripe dynamically
      const stripe = await import('@stripe/stripe-js').then(module =>
        module.loadStripe(microChargeData.publishable_key)
      )

      if (!stripe) {
        throw new Error('Failed to load Stripe')
      }

      const elements = stripe.elements({
        clientSecret: microChargeData.client_secret,
        appearance: {
          theme: 'stripe',
          variables: {
            colorPrimary: '#6366f1',
            colorBackground: '#ffffff',
            colorText: '#374151',
            fontFamily: 'Inter, system-ui, sans-serif',
          },
        },
      })

      setStripeElements({ stripe, elements })
    } catch (error) {
      console.error('Failed to load Stripe:', error)
      setError('Payment processor unavailable. Please try KBA verification.')
    }
  }

  const processPayment = async () => {
    if (!stripeElements || !microChargeData) {
      setError('Payment system not ready')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const { stripe, elements } = stripeElements

      const { error, paymentIntent } = await stripe.confirmPayment({
        elements,
        confirmParams: {
          return_url: `${window.location.origin}/onboarding/guardian-verify-complete`,
        },
        redirect: 'if_required',
      })

      if (error) {
        setError(error.message || 'Payment failed')
        setVerificationStatus(prev => ({
          ...prev,
          status: 'failed',
          failure_reason: error.code,
        }))
      } else if (paymentIntent?.status === 'succeeded') {
        // Payment succeeded - verification complete
        setVerificationStatus(prev => ({
          ...prev,
          status: 'verified',
        }))

        updateGuardianVerification({
          isVerified: true,
          verifiedAt: new Date().toISOString(),
          method: 'micro_charge',
        })

        // Auto-advance to next step after brief delay
        setTimeout(() => {
          onNext()
        }, 2000)
      }
    } catch (error) {
      console.error('Payment processing failed:', error)
      setError('Payment processing failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const startKBAPolling = (verificationId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/v1/verify/${verificationId}/status`)
        if (response.ok) {
          const data = await response.json()

          if (data.status === 'verified') {
            clearInterval(pollInterval)
            setVerificationStatus({
              verification_id: verificationId,
              status: 'verified',
              method: 'kba',
              attempts_remaining: data.attempts_remaining,
              can_retry: false,
            })

            updateGuardianVerification({
              isVerified: true,
              verifiedAt: data.verified_at,
              method: 'kba',
            })

            setTimeout(() => {
              onNext()
            }, 2000)
          } else if (data.status === 'failed') {
            clearInterval(pollInterval)
            setVerificationStatus(prev => ({
              ...prev,
              status: 'failed',
              failure_reason: data.failure_reason,
              can_retry: data.can_retry,
              attempts_remaining: data.attempts_remaining,
            }))
          }
        }
      } catch (error) {
        console.error('Failed to poll verification status:', error)
      }
    }, 3000) // Poll every 3 seconds

    // Stop polling after 10 minutes
    setTimeout(() => {
      clearInterval(pollInterval)
    }, 600000)
  }

  const determineCountryCode = (): string => {
    // In production, this would use geolocation or form data
    return state.guardian?.country || 'US'
  }

  const formatTimeRemaining = (isoString: string): string => {
    const time = new Date(isoString)
    const now = new Date()
    const diff = time.getTime() - now.getTime()

    if (diff <= 0) return 'Now'

    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

    if (hours > 0) return `${hours}h ${minutes}m`
    return `${minutes}m`
  }

  // Skip verification if already verified
  if (verificationStatus.status === 'verified') {
    return (
      <FadeInWhenVisible>
        <div className="max-w-2xl mx-auto">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="text-center py-12"
          >
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="w-10 h-10 text-green-600" />
            </div>

            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Identity Verified!
            </h2>

            <p className="text-gray-600 mb-8">
              Your identity has been successfully verified. You can now proceed
              with the enrollment process.
            </p>

            <Button onClick={onNext} size="lg">
              Continue to Consent
            </Button>
          </motion.div>
        </div>
      </FadeInWhenVisible>
    )
  }

  return (
    <FadeInWhenVisible>
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">
            Guardian Identity Verification
          </h2>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            To comply with COPPA regulations and ensure child safety, we need to
            verify your identity as a parent or guardian before proceeding with
            enrollment.
          </p>
        </div>

        {/* COPPA Compliance Notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-8">
          <div className="flex items-start">
            <Shield className="w-5 h-5 text-blue-600 mt-0.5 mr-3" />
            <div>
              <h3 className="font-semibold text-blue-900 mb-1">
                COPPA Compliance
              </h3>
              <p className="text-blue-800 text-sm">
                The Children's Online Privacy Protection Act (COPPA) requires us
                to verify the identity of parents/guardians before collecting
                information from children under 13. This verification is quick,
                secure, and protects your child's privacy.
              </p>
            </div>
          </div>
        </div>

        {/* Rate Limit Warning */}
        {verificationStatus.attempts_remaining <= 1 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5 mr-3" />
              <div>
                <h3 className="font-semibold text-amber-900 mb-1">
                  Limited Attempts Remaining
                </h3>
                <p className="text-amber-800 text-sm">
                  You have {verificationStatus.attempts_remaining} verification
                  attempt(s) remaining today.
                  {verificationStatus.next_attempt_at && (
                    <>
                      {' '}
                      Next attempt available:{' '}
                      {formatTimeRemaining(verificationStatus.next_attempt_at)}
                    </>
                  )}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 mr-3" />
              <div>
                <h3 className="font-semibold text-red-900 mb-1">
                  Verification Error
                </h3>
                <p className="text-red-800 text-sm">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Verification Method Selection */}
        {!selectedMethod && verificationStatus.status === 'pending' && (
          <div className="grid md:grid-cols-2 gap-6 mb-8">
            {/* Micro-Charge Option */}
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="border-2 border-gray-200 rounded-lg p-6 hover:border-indigo-300 cursor-pointer transition-colors"
              onClick={() => setSelectedMethod('micro_charge')}
            >
              <div className="flex items-start mb-4">
                <CreditCard className="w-8 h-8 text-indigo-600 mr-4" />
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    Credit Card Verification
                  </h3>
                  <p className="text-gray-600 text-sm mb-4">
                    We'll charge $0.10 to your credit card and immediately
                    refund it. This verifies you have access to a valid payment
                    method.
                  </p>
                </div>
              </div>

              <div className="space-y-2 text-sm text-gray-500">
                <div className="flex items-center">
                  <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                  <span>Quick verification (2-3 minutes)</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                  <span>$0.10 charge automatically refunded</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                  <span>Secure payment processing by Stripe</span>
                </div>
              </div>
            </motion.div>

            {/* KBA Option */}
            <motion.div
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="border-2 border-gray-200 rounded-lg p-6 hover:border-indigo-300 cursor-pointer transition-colors"
              onClick={() => setSelectedMethod('kba')}
            >
              <div className="flex items-start mb-4">
                <Lock className="w-8 h-8 text-indigo-600 mr-4" />
                <div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    Knowledge-Based Verification
                  </h3>
                  <p className="text-gray-600 text-sm mb-4">
                    Answer a few questions about your personal history that only
                    you would know. No payment required.
                  </p>
                </div>
              </div>

              <div className="space-y-2 text-sm text-gray-500">
                <div className="flex items-center">
                  <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                  <span>No payment required</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                  <span>4-5 multiple choice questions</span>
                </div>
                <div className="flex items-center">
                  <CheckCircle className="w-4 h-4 text-green-500 mr-2" />
                  <span>Based on public records</span>
                </div>
              </div>
            </motion.div>
          </div>
        )}

        {/* Micro-Charge Flow */}
        {selectedMethod === 'micro_charge' &&
          verificationStatus.status === 'pending' && (
            <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Credit Card Verification
              </h3>

              <div className="bg-blue-50 rounded-lg p-4 mb-6">
                <p className="text-blue-800 text-sm">
                  <strong>Important:</strong> We will charge $0.10 to verify
                  your identity and automatically refund it within 5 minutes.
                  You will not be charged for this verification.
                </p>
              </div>

              <Button
                onClick={() => startVerification('micro_charge')}
                disabled={
                  isLoading || verificationStatus.attempts_remaining <= 0
                }
                size="lg"
                className="w-full"
              >
                {isLoading
                  ? 'Setting up verification...'
                  : 'Start Credit Card Verification'}
              </Button>
            </div>
          )}

        {/* Stripe Payment Element */}
        {microChargeData &&
          stripeElements &&
          verificationStatus.status === 'in_progress' && (
            <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Complete Verification
              </h3>

              <div className="mb-4">
                <p className="text-gray-600 text-sm mb-4">
                  Enter your payment information below. A $0.10 charge will be
                  made and immediately refunded.
                </p>

                {/* Stripe Elements would be rendered here */}
                <div className="border border-gray-300 rounded-lg p-4 bg-gray-50">
                  <p className="text-gray-500 text-center">
                    Stripe Payment Element would render here
                  </p>
                </div>
              </div>

              <Button
                onClick={processPayment}
                disabled={isLoading}
                size="lg"
                className="w-full"
              >
                {isLoading
                  ? 'Processing...'
                  : 'Verify Identity ($0.10 - Refunded)'}
              </Button>
            </div>
          )}

        {/* KBA Flow */}
        {selectedMethod === 'kba' &&
          verificationStatus.status === 'pending' && (
            <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Knowledge-Based Verification
              </h3>

              <div className="bg-amber-50 rounded-lg p-4 mb-6">
                <p className="text-amber-800 text-sm">
                  <strong>Note:</strong> This verification method may not be
                  available in all regions due to privacy regulations. If
                  unavailable, please use credit card verification.
                </p>
              </div>

              <Button
                onClick={() => startVerification('kba')}
                disabled={
                  isLoading || verificationStatus.attempts_remaining <= 0
                }
                size="lg"
                className="w-full"
              >
                {isLoading
                  ? 'Starting verification...'
                  : 'Start Knowledge-Based Verification'}
              </Button>
            </div>
          )}

        {/* In Progress Status */}
        {verificationStatus.status === 'in_progress' &&
          selectedMethod === 'kba' && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
              <div className="flex items-center">
                <Clock className="w-5 h-5 text-blue-600 mr-3" />
                <div>
                  <h3 className="font-semibold text-blue-900 mb-1">
                    Verification in Progress
                  </h3>
                  <p className="text-blue-800 text-sm">
                    Please complete the verification questions in the new
                    window. This page will automatically update when
                    verification is complete.
                  </p>
                </div>
              </div>
            </div>
          )}

        {/* Failed Status */}
        {verificationStatus.status === 'failed' && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 mb-6">
            <div className="flex items-start">
              <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5 mr-3" />
              <div>
                <h3 className="font-semibold text-red-900 mb-1">
                  Verification Failed
                </h3>
                <p className="text-red-800 text-sm mb-4">
                  {verificationStatus.failure_reason === 'card_declined' &&
                    'Your card was declined. Please try with a different payment method.'}
                  {verificationStatus.failure_reason === 'kba_failed' &&
                    'Identity verification questions were not answered correctly. Please try credit card verification.'}
                  {!verificationStatus.failure_reason &&
                    'Verification failed. Please try again or contact support.'}
                </p>

                {verificationStatus.can_retry &&
                  verificationStatus.attempts_remaining > 0 && (
                    <Button
                      onClick={() => {
                        setSelectedMethod(null)
                        setError(null)
                        setVerificationStatus(prev => ({
                          ...prev,
                          status: 'pending',
                        }))
                      }}
                      variant="outline"
                      size="sm"
                    >
                      Try Again ({verificationStatus.attempts_remaining}{' '}
                      attempts remaining)
                    </Button>
                  )}
              </div>
            </div>
          </div>
        )}

        {/* Navigation */}
        <div className="flex justify-between">
          <Button variant="outline" onClick={onBack}>
            Back
          </Button>

          {verificationStatus.status !== 'verified' && (
            <Button
              variant="outline"
              onClick={() => {
                // Allow skipping for development/testing
                if (process.env.NODE_ENV === 'development') {
                  onNext()
                }
              }}
              className="text-gray-500"
            >
              Skip (Dev Only)
            </Button>
          )}
        </div>
      </div>
    </FadeInWhenVisible>
  )
}
