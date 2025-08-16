import { useState, useCallback } from 'react'

export interface GuardianProfile {
  firstName: string
  lastName: string
  email: string
  phone?: string
  timezone: string
  preferredLanguage: string
}

export interface LearnerProfile {
  firstName: string
  lastName: string
  dateOfBirth: string
  gradeDefault: number
  gradeBand: string
  specialNeeds?: string
  interests?: string[]
}

export interface ConsentSettings {
  mediaConsent: boolean
  chatConsent: boolean
  thirdPartyConsent: boolean
  dataProcessingConsent: boolean
  termsAccepted: boolean
}

export interface PlanSelection {
  planType: 'trial' | 'monthly' | 'quarterly' | 'half-year' | 'yearly'
  siblingDiscount: boolean
  totalPrice: number
  originalPrice: number
}

export interface ScheduleBaseline {
  weeklyGoal: number // hours per week
  preferredTimeSlots: string[]
  subjects: string[]
  difficulty: 'beginner' | 'intermediate' | 'advanced'
}

export interface OnboardingState {
  currentStep: number
  guardian: GuardianProfile | null
  learners: LearnerProfile[]
  consent: ConsentSettings | null
  plan: PlanSelection | null
  schedule: ScheduleBaseline | null
  isComplete: boolean
}

const INITIAL_STATE: OnboardingState = {
  currentStep: 0,
  guardian: null,
  learners: [],
  consent: null,
  plan: null,
  schedule: null,
  isComplete: false,
}

export function useOnboarding() {
  const [state, setState] = useState<OnboardingState>(INITIAL_STATE)

  const updateGuardian = useCallback((guardian: GuardianProfile) => {
    setState(prev => ({ ...prev, guardian }))
  }, [])

  const addLearner = useCallback((learner: LearnerProfile) => {
    setState(prev => ({
      ...prev,
      learners: [...prev.learners, learner],
    }))
  }, [])

  const updateLearner = useCallback(
    (index: number, learner: LearnerProfile) => {
      setState(prev => ({
        ...prev,
        learners: prev.learners.map((l, i) => (i === index ? learner : l)),
      }))
    },
    []
  )

  const removeLearner = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      learners: prev.learners.filter((_, i) => i !== index),
    }))
  }, [])

  const updateConsent = useCallback((consent: ConsentSettings) => {
    setState(prev => ({ ...prev, consent }))
  }, [])

  const updatePlan = useCallback((plan: PlanSelection) => {
    setState(prev => ({ ...prev, plan }))
  }, [])

  const updateSchedule = useCallback((schedule: ScheduleBaseline) => {
    setState(prev => ({ ...prev, schedule }))
  }, [])

  const nextStep = useCallback(() => {
    setState(prev => ({ ...prev, currentStep: prev.currentStep + 1 }))
  }, [])

  const prevStep = useCallback(() => {
    setState(prev => ({
      ...prev,
      currentStep: Math.max(0, prev.currentStep - 1),
    }))
  }, [])

  const goToStep = useCallback((step: number) => {
    setState(prev => ({ ...prev, currentStep: step }))
  }, [])

  const complete = useCallback(() => {
    setState(prev => ({ ...prev, isComplete: true }))
  }, [])

  const reset = useCallback(() => {
    setState(INITIAL_STATE)
  }, [])

  // Utility functions
  const calculateAge = useCallback((dateOfBirth: string): number => {
    const birth = new Date(dateOfBirth)
    const today = new Date()
    let age = today.getFullYear() - birth.getFullYear()
    const monthDiff = today.getMonth() - birth.getMonth()
    if (
      monthDiff < 0 ||
      (monthDiff === 0 && today.getDate() < birth.getDate())
    ) {
      age--
    }
    return age
  }, [])

  const calculateGrade = useCallback(
    (dateOfBirth: string): number => {
      const age = calculateAge(dateOfBirth)
      // Typical US grade calculation: age - 5 for kindergarten start
      return Math.max(0, Math.min(12, age - 5))
    },
    [calculateAge]
  )

  const getGradeBand = useCallback((grade: number): string => {
    if (grade <= 2) return 'Early Elementary (K-2)'
    if (grade <= 5) return 'Elementary (3-5)'
    if (grade <= 8) return 'Middle School (6-8)'
    return 'High School (9-12)'
  }, [])

  const calculatePlanPrice = useCallback(
    (
      planType: PlanSelection['planType'],
      siblingCount: number
    ): { originalPrice: number; finalPrice: number; discount: number } => {
      const basePrices = {
        trial: 0,
        monthly: 29.99,
        quarterly: 23.99, // 20% off monthly
        'half-year': 20.99, // 30% off monthly
        yearly: 14.99, // 50% off monthly
      }

      const originalPrice = basePrices[planType]
      let finalPrice = originalPrice

      // Sibling discount: 10% off for 2+ learners
      if (siblingCount >= 2) {
        finalPrice *= 0.9
      }

      const discount = originalPrice - finalPrice
      return { originalPrice, finalPrice, discount }
    },
    []
  )

  const isStepValid = useCallback(
    (step: number): boolean => {
      switch (step) {
        case 0: // Guardian Profile
          return !!(
            state.guardian?.firstName &&
            state.guardian?.lastName &&
            state.guardian?.email
          )
        case 1: // Add Learner
          return state.learners.length > 0
        case 2: // Consent
          return !!(
            state.consent?.dataProcessingConsent && state.consent?.termsAccepted
          )
        case 3: // Plan Picker
          return !!state.plan
        case 4: // Schedule Baseline
          return !!(
            state.schedule?.weeklyGoal && state.schedule?.subjects.length > 0
          )
        default:
          return false
      }
    },
    [state]
  )

  return {
    state,
    updateGuardian,
    addLearner,
    updateLearner,
    removeLearner,
    updateConsent,
    updatePlan,
    updateSchedule,
    nextStep,
    prevStep,
    goToStep,
    complete,
    reset,
    calculateAge,
    calculateGrade,
    getGradeBand,
    calculatePlanPrice,
    isStepValid,
  }
}

export type UseOnboardingReturn = ReturnType<typeof useOnboarding>
