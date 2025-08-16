import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '../../components/ui/Button'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import { ConsentSettings, UseOnboardingReturn } from '../../hooks/useOnboarding'

interface ConsentStepProps {
  onboardingData: UseOnboardingReturn
  onNext: () => void
  onBack: () => void
}

interface ConsentItem {
  key: keyof ConsentSettings
  title: string
  description: string
  required: boolean
  details: string[]
}

export const ConsentStep: React.FC<ConsentStepProps> = ({
  onboardingData,
  onNext,
  onBack,
}) => {
  const { state, updateConsent } = onboardingData
  const [consents, setConsents] = useState<ConsentSettings>({
    mediaConsent: false,
    chatConsent: false,
    thirdPartyConsent: false,
    dataProcessingConsent: false,
    termsAccepted: false,
  })

  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())

  useEffect(() => {
    if (state.consent) {
      setConsents(state.consent)
    }
  }, [state.consent])

  const consentItems: ConsentItem[] = [
    {
      key: 'dataProcessingConsent',
      title: 'Data Processing & Privacy',
      description:
        "Allow AIVO to process your child's educational data to provide personalized learning experiences.",
      required: true,
      details: [
        'Collection and analysis of learning progress data',
        'Personalized content recommendations based on performance',
        'Anonymous usage analytics to improve our platform',
        'Secure storage of educational records and assessments',
        'Data sharing only with authorized educational partners',
      ],
    },
    {
      key: 'termsAccepted',
      title: 'Terms of Service & User Agreement',
      description: "Accept AIVO's Terms of Service and User Agreement.",
      required: true,
      details: [
        'Platform usage rules and guidelines',
        'Account security and responsibility',
        'Content and intellectual property rights',
        'Limitation of liability and disclaimers',
        'Dispute resolution procedures',
      ],
    },
    {
      key: 'mediaConsent',
      title: 'Media & Content Sharing',
      description:
        'Allow your child to upload and share educational content like assignments and projects.',
      required: false,
      details: [
        'Upload homework, projects, and assignments for AI feedback',
        'Share learning achievements with teachers and parents',
        'Participate in virtual classroom discussions',
        'Submit creative work for peer collaboration',
        'All content is moderated and privacy-protected',
      ],
    },
    {
      key: 'chatConsent',
      title: 'AI Chat & Communication',
      description:
        "Enable your child to interact with AIVO's AI tutoring system and communicate with teachers.",
      required: false,
      details: [
        'Real-time AI tutoring and homework help',
        'Q&A sessions with subject matter experts',
        'Peer-to-peer learning discussions (moderated)',
        'Parent-teacher communication through platform',
        'All conversations are monitored for safety',
      ],
    },
    {
      key: 'thirdPartyConsent',
      title: 'Third-Party Educational Tools',
      description:
        'Allow integration with external educational platforms and tools to enhance learning.',
      required: false,
      details: [
        'Integration with school learning management systems',
        'Access to educational apps and online resources',
        'Synchronization with digital textbooks and libraries',
        'Educational game platforms and interactive content',
        'Only approved, vetted educational partners',
      ],
    },
  ]

  const toggleConsent = (key: keyof ConsentSettings) => {
    setConsents(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const toggleExpanded = (key: string) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev)
      if (newSet.has(key)) {
        newSet.delete(key)
      } else {
        newSet.add(key)
      }
      return newSet
    })
  }

  const requiredConsentsGiven =
    consents.dataProcessingConsent && consents.termsAccepted

  const handleContinue = () => {
    updateConsent(consents)
    onNext()
  }

  const ConsentItemComponent: React.FC<{ item: ConsentItem }> = ({ item }) => {
    const isExpanded = expandedItems.has(item.key)
    const isChecked = consents[item.key]

    return (
      <motion.div
        layout
        className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
      >
        <div className="p-6">
          <div className="flex items-start space-x-4">
            <div className="flex-shrink-0 mt-1">
              <button
                onClick={() => toggleConsent(item.key)}
                className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                  isChecked
                    ? 'bg-blue-600 border-blue-600'
                    : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'
                }`}
              >
                {isChecked && (
                  <svg
                    className="w-3 h-3 text-white"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={3}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                )}
              </button>
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {item.title}
                  </h3>
                  {item.required && (
                    <span className="px-2 py-1 bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 text-xs font-medium rounded">
                      Required
                    </span>
                  )}
                </div>

                <button
                  onClick={() => toggleExpanded(item.key)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                >
                  <svg
                    className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 9l-7 7-7-7"
                    />
                  </svg>
                </button>
              </div>

              <p className="mt-2 text-gray-600 dark:text-gray-400">
                {item.description}
              </p>

              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="mt-4 pl-4 border-l-2 border-gray-200 dark:border-gray-600"
                  >
                    <h4 className="font-medium text-gray-900 dark:text-white mb-2">
                      This includes:
                    </h4>
                    <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
                      {item.details.map((detail, index) => (
                        <li key={index} className="flex items-start space-x-2">
                          <span className="w-1.5 h-1.5 bg-gray-400 rounded-full mt-2 flex-shrink-0" />
                          <span>{detail}</span>
                        </li>
                      ))}
                    </ul>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <FadeInWhenVisible>
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="inline-flex items-center justify-center w-16 h-16 bg-purple-100 dark:bg-purple-900 rounded-full mb-4"
          >
            <svg
              className="w-8 h-8 text-purple-600 dark:text-purple-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.031 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </motion.div>

          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Privacy & Consent
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Help us understand how you&apos;d like your child to interact with
            AIVO
          </p>
        </div>
      </FadeInWhenVisible>

      <FadeInWhenVisible delay={0.2}>
        <div className="mb-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-start space-x-3">
            <svg
              className="w-6 h-6 text-blue-600 dark:text-blue-400 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                Your Privacy Matters
              </h3>
              <p className="text-blue-800 dark:text-blue-200 text-sm">
                AIVO is committed to protecting your family&apos;s privacy. Some
                permissions are required for basic functionality, while others
                are optional but enhance the learning experience. You can change
                these settings anytime in your account preferences.
              </p>
            </div>
          </div>
        </div>
      </FadeInWhenVisible>

      <div className="space-y-4 mb-8">
        {consentItems.map(item => (
          <FadeInWhenVisible
            key={item.key}
            delay={consentItems.indexOf(item) * 0.1}
          >
            <ConsentItemComponent item={item} />
          </FadeInWhenVisible>
        ))}
      </div>

      {!requiredConsentsGiven && (
        <FadeInWhenVisible>
          <div className="mb-6 p-4 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
            <div className="flex items-center space-x-2">
              <svg
                className="w-5 h-5 text-amber-600 dark:text-amber-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
              <p className="text-amber-800 dark:text-amber-200 text-sm font-medium">
                Please accept the required terms to continue
              </p>
            </div>
          </div>
        </FadeInWhenVisible>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-8">
        <Button variant="outline" onClick={onBack}>
          ← Previous: Learners
        </Button>

        <Button onClick={handleContinue} disabled={!requiredConsentsGiven}>
          Next: Choose Plan →
        </Button>
      </div>

      {/* Terms Links */}
      <FadeInWhenVisible delay={0.6}>
        <div className="mt-8 pt-6 border-t border-gray-200 dark:border-gray-700 text-center text-sm text-gray-600 dark:text-gray-400">
          <p>
            By continuing, you agree to our{' '}
            <a
              href="/terms"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Terms of Service
            </a>{' '}
            and{' '}
            <a
              href="/privacy"
              className="text-blue-600 dark:text-blue-400 hover:underline"
            >
              Privacy Policy
            </a>
          </p>
        </div>
      </FadeInWhenVisible>
    </div>
  )
}
