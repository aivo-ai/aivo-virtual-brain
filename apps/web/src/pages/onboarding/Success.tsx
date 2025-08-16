import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Button } from '../../components/ui/Button'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import { OnboardingState } from '../../hooks/useOnboarding'

interface SuccessStepProps {
  onboardingData: OnboardingState
  onComplete: () => void
}

export const SuccessStep: React.FC<SuccessStepProps> = ({
  onboardingData,
  onComplete,
}) => {
  const [isProcessing, setIsProcessing] = useState(true)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    // Simulate processing steps
    const steps = [
      { message: 'Creating your account...', delay: 1000 },
      { message: 'Setting up learner profiles...', delay: 1500 },
      { message: 'Configuring learning preferences...', delay: 1000 },
      { message: 'Initializing AI recommendations...', delay: 1200 },
      { message: 'Preparing your dashboard...', delay: 800 },
    ]

    let currentStep = 0

    const processStep = () => {
      if (currentStep < steps.length) {
        setProgress(((currentStep + 1) / steps.length) * 100)
        setTimeout(() => {
          currentStep++
          processStep()
        }, steps[currentStep]?.delay || 1000)
      } else {
        setIsProcessing(false)
      }
    }

    processStep()
  }, [])

  const { guardian, learners, plan, schedule } = onboardingData

  if (isProcessing) {
    return (
      <div className="max-w-2xl mx-auto text-center">
        <FadeInWhenVisible>
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center justify-center w-20 h-20 bg-blue-100 dark:bg-blue-900 rounded-full mb-6"
          >
            <motion.svg
              className="w-10 h-10 text-blue-600 dark:text-blue-400"
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </motion.svg>
          </motion.div>

          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Setting Up Your AIVO Experience
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-8">
            We're personalizing everything just for you. This will only take a
            moment...
          </p>

          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 mb-4">
            <motion.div
              className="bg-blue-600 h-3 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>

          <p className="text-sm text-gray-500 dark:text-gray-400">
            {Math.round(progress)}% complete
          </p>
        </FadeInWhenVisible>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto">
      <FadeInWhenVisible>
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, type: 'spring', bounce: 0.5 }}
            className="inline-flex items-center justify-center w-20 h-20 bg-green-100 dark:bg-green-900 rounded-full mb-6"
          >
            <svg
              className="w-10 h-10 text-green-600 dark:text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </motion.div>

          <motion.h1
            className="text-4xl font-bold text-gray-900 dark:text-white mb-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            🎉 Welcome to AIVO!
          </motion.h1>

          <motion.p
            className="text-xl text-gray-600 dark:text-gray-400 mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            Your personalized learning journey starts now
          </motion.p>
        </div>
      </FadeInWhenVisible>

      {/* Success Summary */}
      <FadeInWhenVisible delay={0.3}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Account Summary */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center mr-3">
                <svg
                  className="w-5 h-5 text-blue-600 dark:text-blue-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Guardian Profile
              </h3>
            </div>
            <div className="space-y-2 text-sm">
              <p>
                <span className="text-gray-600 dark:text-gray-400">Name:</span>{' '}
                {guardian?.firstName} {guardian?.lastName}
              </p>
              <p>
                <span className="text-gray-600 dark:text-gray-400">Email:</span>{' '}
                {guardian?.email}
              </p>
              <p>
                <span className="text-gray-600 dark:text-gray-400">
                  Language:
                </span>{' '}
                {guardian?.preferredLanguage}
              </p>
            </div>
          </div>

          {/* Learners Summary */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 bg-green-100 dark:bg-green-900 rounded-lg flex items-center justify-center mr-3">
                <svg
                  className="w-5 h-5 text-green-600 dark:text-green-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Learners ({learners.length})
              </h3>
            </div>
            <div className="space-y-2 text-sm">
              {learners.map((learner, index) => (
                <p key={index}>
                  <span className="font-medium">
                    {learner.firstName} {learner.lastName}
                  </span>
                  <span className="text-gray-600 dark:text-gray-400 ml-2">
                    {learner.gradeBand}
                  </span>
                </p>
              ))}
            </div>
          </div>

          {/* Plan Summary */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900 rounded-lg flex items-center justify-center mr-3">
                <svg
                  className="w-5 h-5 text-purple-600 dark:text-purple-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Plan & Billing
              </h3>
            </div>
            <div className="space-y-2 text-sm">
              <p>
                <span className="text-gray-600 dark:text-gray-400">Plan:</span>{' '}
                {plan?.planType === 'trial'
                  ? '30-Day Free Trial'
                  : `${plan?.planType} Plan`}
              </p>
              <p>
                <span className="text-gray-600 dark:text-gray-400">Cost:</span>{' '}
                {plan?.planType === 'trial'
                  ? 'Free'
                  : `$${plan?.totalPrice.toFixed(2)}/month`}
              </p>
              {plan?.siblingDiscount && (
                <p className="text-green-600 dark:text-green-400">
                  ✓ Sibling discount applied
                </p>
              )}
            </div>
          </div>

          {/* Schedule Summary */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center mb-4">
              <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900 rounded-lg flex items-center justify-center mr-3">
                <svg
                  className="w-5 h-5 text-indigo-600 dark:text-indigo-400"
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
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Learning Schedule
              </h3>
            </div>
            <div className="space-y-2 text-sm">
              <p>
                <span className="text-gray-600 dark:text-gray-400">
                  Weekly Goal:
                </span>{' '}
                {schedule?.weeklyGoal} hours
              </p>
              <p>
                <span className="text-gray-600 dark:text-gray-400">
                  Difficulty:
                </span>{' '}
                {schedule?.difficulty}
              </p>
              <p>
                <span className="text-gray-600 dark:text-gray-400">
                  Subjects:
                </span>{' '}
                {schedule?.subjects.length} selected
              </p>
            </div>
          </div>
        </div>
      </FadeInWhenVisible>

      {/* Next Steps */}
      <FadeInWhenVisible delay={0.5}>
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-lg border border-blue-200 dark:border-blue-800 p-6 mb-8">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            🚀 What's Next?
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-start space-x-3">
              <div className="w-6 h-6 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold text-xs mt-0.5">
                1
              </div>
              <div>
                <div className="font-medium text-gray-900 dark:text-white">
                  Explore Dashboard
                </div>
                <div className="text-gray-600 dark:text-gray-400">
                  View progress, assignments, and insights
                </div>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="w-6 h-6 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold text-xs mt-0.5">
                2
              </div>
              <div>
                <div className="font-medium text-gray-900 dark:text-white">
                  Start Learning
                </div>
                <div className="text-gray-600 dark:text-gray-400">
                  Begin first lesson with AI guidance
                </div>
              </div>
            </div>
            <div className="flex items-start space-x-3">
              <div className="w-6 h-6 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center text-blue-600 dark:text-blue-400 font-bold text-xs mt-0.5">
                3
              </div>
              <div>
                <div className="font-medium text-gray-900 dark:text-white">
                  Track Progress
                </div>
                <div className="text-gray-600 dark:text-gray-400">
                  Monitor learning achievements daily
                </div>
              </div>
            </div>
          </div>
        </div>
      </FadeInWhenVisible>

      {/* Action Buttons */}
      <FadeInWhenVisible delay={0.7}>
        <div className="text-center space-y-4">
          <Button size="lg" onClick={onComplete} className="px-8 py-4 text-lg">
            🎯 Go to Dashboard
          </Button>

          <div className="text-sm text-gray-600 dark:text-gray-400 space-x-4">
            <a
              href="/help"
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              📖 View Getting Started Guide
            </a>
            <span>•</span>
            <a
              href="/support"
              className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
            >
              💬 Contact Support
            </a>
          </div>
        </div>
      </FadeInWhenVisible>

      {/* Celebration Animation */}
      <motion.div
        className="fixed inset-0 pointer-events-none"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
      >
        {[...Array(20)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-2 h-2 bg-blue-500 rounded-full"
            initial={{
              x: Math.random() * window.innerWidth,
              y: window.innerHeight,
            }}
            animate={{
              y: -50,
              x: Math.random() * window.innerWidth,
            }}
            transition={{
              duration: 3,
              delay: Math.random() * 2,
              repeat: Infinity,
              repeatType: 'loop',
            }}
            style={{
              backgroundColor: ['#3B82F6', '#8B5CF6', '#10B981', '#F59E0B'][
                i % 4
              ],
            }}
          />
        ))}
      </motion.div>
    </div>
  )
}
