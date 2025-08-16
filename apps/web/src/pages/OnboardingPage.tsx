import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useOnboarding } from '../hooks/useOnboarding'
import { GuardianProfileStep } from './onboarding/GuardianProfile'
import { AddLearnerStep } from './onboarding/AddLearner'
import { ConsentStep } from './onboarding/Consent'
import { PlanPickerStep } from './onboarding/PlanPicker'
import { ScheduleBaselineStep } from './onboarding/ScheduleBaseline'
import { SuccessStep } from './onboarding/Success'

export type OnboardingStep =
  | 'guardian-profile'
  | 'add-learner'
  | 'consent'
  | 'plan-picker'
  | 'schedule-baseline'
  | 'success'

const STEPS: { key: OnboardingStep; title: string; description: string }[] = [
  {
    key: 'guardian-profile',
    title: 'Guardian Profile',
    description: 'Tell us about yourself',
  },
  {
    key: 'add-learner',
    title: 'Add Learners',
    description: 'Add your children',
  },
  {
    key: 'consent',
    title: 'Privacy & Consent',
    description: 'Configure privacy settings',
  },
  {
    key: 'plan-picker',
    title: 'Choose Plan',
    description: 'Select your subscription',
  },
  {
    key: 'schedule-baseline',
    title: 'Learning Schedule',
    description: 'Set learning preferences',
  },
  {
    key: 'success',
    title: 'All Set!',
    description: 'Welcome to AIVO',
  },
]

export default function OnboardingPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const onboardingData = useOnboarding()
  const [currentStep, setCurrentStep] =
    useState<OnboardingStep>('guardian-profile')

  const currentStepIndex = STEPS.findIndex(step => step.key === currentStep)
  const progress = ((currentStepIndex + 1) / STEPS.length) * 100

  const handleNext = () => {
    const nextIndex = currentStepIndex + 1
    if (nextIndex < STEPS.length) {
      setCurrentStep(STEPS[nextIndex].key)
    }
  }

  const handleBack = () => {
    const prevIndex = currentStepIndex - 1
    if (prevIndex >= 0) {
      setCurrentStep(STEPS[prevIndex].key)
    }
  }

  const handleComplete = () => {
    // Navigate to dashboard after successful onboarding
    navigate('/dashboard')
  }

  const renderStep = () => {
    switch (currentStep) {
      case 'guardian-profile':
        return (
          <GuardianProfileStep
            onboardingData={onboardingData}
            onNext={handleNext}
          />
        )
      case 'add-learner':
        return (
          <AddLearnerStep
            onboardingData={onboardingData}
            onNext={handleNext}
            onBack={handleBack}
          />
        )
      case 'consent':
        return (
          <ConsentStep
            onboardingData={onboardingData}
            onNext={handleNext}
            onBack={handleBack}
          />
        )
      case 'plan-picker':
        return (
          <PlanPickerStep
            onboardingData={onboardingData}
            onNext={handleNext}
            onBack={handleBack}
          />
        )
      case 'schedule-baseline':
        return (
          <ScheduleBaselineStep
            onboardingData={onboardingData}
            onNext={handleNext}
            onBack={handleBack}
          />
        )
      case 'success':
        return (
          <SuccessStep
            onboardingData={onboardingData.state}
            onComplete={handleComplete}
          />
        )
      default:
        return null
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header with Progress */}
      <div className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                {t('onboarding.title', 'Welcome to AIVO')}
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                {STEPS[currentStepIndex]?.description}
              </p>
            </div>
            <div className="text-right">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Step {currentStepIndex + 1} of {STEPS.length}
              </p>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {STEPS[currentStepIndex]?.title}
              </p>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <motion.div
              className="bg-blue-600 h-2 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: 'easeOut' }}
            />
          </div>

          {/* Step Indicators */}
          <div className="flex justify-between mt-4">
            {STEPS.map((step, index) => (
              <div
                key={step.key}
                className={`flex items-center ${
                  index <= currentStepIndex
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-gray-400 dark:text-gray-500'
                }`}
              >
                <motion.div
                  className={`w-8 h-8 rounded-full border-2 flex items-center justify-center text-sm font-semibold ${
                    index < currentStepIndex
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : index === currentStepIndex
                        ? 'border-blue-600 bg-white dark:bg-gray-800 text-blue-600 dark:text-blue-400'
                        : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800'
                  }`}
                  initial={false}
                  animate={{
                    scale: index === currentStepIndex ? 1.1 : 1,
                  }}
                  transition={{ duration: 0.2 }}
                >
                  {index < currentStepIndex ? (
                    <svg
                      className="w-5 h-5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  ) : (
                    index + 1
                  )}
                </motion.div>
                <span className="ml-2 text-sm font-medium hidden md:block">
                  {step.title}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Step Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            {renderStep()}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}
