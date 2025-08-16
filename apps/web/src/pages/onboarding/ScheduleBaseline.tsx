import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Button } from '../../components/ui/Button'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import {
  ScheduleBaseline,
  UseOnboardingReturn,
} from '../../hooks/useOnboarding'

interface ScheduleBaselineStepProps {
  onboardingData: UseOnboardingReturn
  onNext: () => void
  onBack: () => void
}

export const ScheduleBaselineStep: React.FC<ScheduleBaselineStepProps> = ({
  onboardingData,
  onNext,
  onBack,
}) => {
  const { state, updateSchedule } = onboardingData
  const [schedule, setSchedule] = useState<ScheduleBaseline>({
    weeklyGoal: 5,
    preferredTimeSlots: [],
    subjects: [],
    difficulty: 'intermediate',
  })

  const [errors, setErrors] = useState<Record<string, string>>({})

  useEffect(() => {
    if (state.schedule) {
      setSchedule(state.schedule)
    }
  }, [state.schedule])

  const weeklyGoalOptions = [
    { value: 2, label: '2 hours/week', description: 'Light learning' },
    { value: 5, label: '5 hours/week', description: 'Recommended' },
    { value: 10, label: '10 hours/week', description: 'Intensive' },
    { value: 15, label: '15+ hours/week', description: 'Comprehensive' },
  ]

  const timeSlotOptions = [
    {
      value: 'early-morning',
      label: 'Early Morning',
      time: '6:00-8:00 AM',
      icon: '🌅',
    },
    { value: 'morning', label: 'Morning', time: '8:00-11:00 AM', icon: '☀️' },
    { value: 'midday', label: 'Midday', time: '11:00 AM-2:00 PM', icon: '🌞' },
    {
      value: 'afternoon',
      label: 'Afternoon',
      time: '2:00-5:00 PM',
      icon: '🌤️',
    },
    {
      value: 'after-school',
      label: 'After School',
      time: '3:00-6:00 PM',
      icon: '🎒',
    },
    { value: 'evening', label: 'Evening', time: '6:00-8:00 PM', icon: '🌆' },
    {
      value: 'late-evening',
      label: 'Late Evening',
      time: '8:00-10:00 PM',
      icon: '🌙',
    },
  ]

  const subjectOptions = [
    { value: 'math', label: 'Mathematics', icon: '📊', color: 'blue' },
    { value: 'science', label: 'Science', icon: '🔬', color: 'green' },
    {
      value: 'reading',
      label: 'Reading & Literature',
      icon: '📚',
      color: 'purple',
    },
    {
      value: 'writing',
      label: 'Writing & Composition',
      icon: '✍️',
      color: 'indigo',
    },
    {
      value: 'history',
      label: 'History & Social Studies',
      icon: '🏛️',
      color: 'amber',
    },
    {
      value: 'languages',
      label: 'Foreign Languages',
      icon: '🌍',
      color: 'rose',
    },
    { value: 'art', label: 'Art & Creativity', icon: '🎨', color: 'pink' },
    {
      value: 'music',
      label: 'Music & Performing Arts',
      icon: '🎵',
      color: 'violet',
    },
    {
      value: 'technology',
      label: 'Technology & Coding',
      icon: '💻',
      color: 'cyan',
    },
  ]

  const difficultyOptions = [
    {
      value: 'beginner' as const,
      label: 'Beginner',
      description: 'Just starting out or needs extra support',
      icon: '🌱',
    },
    {
      value: 'intermediate' as const,
      label: 'Intermediate',
      description: 'At grade level and ready for standard challenges',
      icon: '🌿',
    },
    {
      value: 'advanced' as const,
      label: 'Advanced',
      description: 'Above grade level and seeks challenging content',
      icon: '🌳',
    },
  ]

  const validateSchedule = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!schedule.weeklyGoal || schedule.weeklyGoal < 1) {
      newErrors.weeklyGoal = 'Please select a weekly goal'
    }

    if (schedule.preferredTimeSlots.length === 0) {
      newErrors.preferredTimeSlots = 'Please select at least one time slot'
    }

    if (schedule.subjects.length === 0) {
      newErrors.subjects = 'Please select at least one subject'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleWeeklyGoalChange = (goal: number) => {
    setSchedule(prev => ({ ...prev, weeklyGoal: goal }))
    if (errors.weeklyGoal) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors.weeklyGoal
        return newErrors
      })
    }
  }

  const handleTimeSlotToggle = (timeSlot: string) => {
    setSchedule(prev => ({
      ...prev,
      preferredTimeSlots: prev.preferredTimeSlots.includes(timeSlot)
        ? prev.preferredTimeSlots.filter(slot => slot !== timeSlot)
        : [...prev.preferredTimeSlots, timeSlot],
    }))
    if (errors.preferredTimeSlots) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors.preferredTimeSlots
        return newErrors
      })
    }
  }

  const handleSubjectToggle = (subject: string) => {
    setSchedule(prev => ({
      ...prev,
      subjects: prev.subjects.includes(subject)
        ? prev.subjects.filter(s => s !== subject)
        : [...prev.subjects, subject],
    }))
    if (errors.subjects) {
      setErrors(prev => {
        const newErrors = { ...prev }
        delete newErrors.subjects
        return newErrors
      })
    }
  }

  const handleDifficultyChange = (
    difficulty: ScheduleBaseline['difficulty']
  ) => {
    setSchedule(prev => ({ ...prev, difficulty }))
  }

  const handleContinue = () => {
    if (validateSchedule()) {
      updateSchedule(schedule)
      onNext()
    }
  }

  const getColorClasses = (color: string, isSelected: boolean) => {
    const colors = {
      blue: isSelected
        ? 'bg-blue-100 dark:bg-blue-900 border-blue-500 text-blue-800 dark:text-blue-200'
        : 'border-gray-300 dark:border-gray-600 hover:border-blue-400',
      green: isSelected
        ? 'bg-green-100 dark:bg-green-900 border-green-500 text-green-800 dark:text-green-200'
        : 'border-gray-300 dark:border-gray-600 hover:border-green-400',
      purple: isSelected
        ? 'bg-purple-100 dark:bg-purple-900 border-purple-500 text-purple-800 dark:text-purple-200'
        : 'border-gray-300 dark:border-gray-600 hover:border-purple-400',
      indigo: isSelected
        ? 'bg-indigo-100 dark:bg-indigo-900 border-indigo-500 text-indigo-800 dark:text-indigo-200'
        : 'border-gray-300 dark:border-gray-600 hover:border-indigo-400',
      amber: isSelected
        ? 'bg-amber-100 dark:bg-amber-900 border-amber-500 text-amber-800 dark:text-amber-200'
        : 'border-gray-300 dark:border-gray-600 hover:border-amber-400',
      rose: isSelected
        ? 'bg-rose-100 dark:bg-rose-900 border-rose-500 text-rose-800 dark:text-rose-200'
        : 'border-gray-300 dark:border-gray-600 hover:border-rose-400',
      pink: isSelected
        ? 'bg-pink-100 dark:bg-pink-900 border-pink-500 text-pink-800 dark:text-pink-200'
        : 'border-gray-300 dark:border-gray-600 hover:border-pink-400',
      violet: isSelected
        ? 'bg-violet-100 dark:bg-violet-900 border-violet-500 text-violet-800 dark:text-violet-200'
        : 'border-gray-300 dark:border-gray-600 hover:border-violet-400',
      cyan: isSelected
        ? 'bg-cyan-100 dark:bg-cyan-900 border-cyan-500 text-cyan-800 dark:text-cyan-200'
        : 'border-gray-300 dark:border-gray-600 hover:border-cyan-400',
    }
    return colors[color as keyof typeof colors] || colors.blue
  }

  return (
    <div className="max-w-4xl mx-auto">
      <FadeInWhenVisible>
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="inline-flex items-center justify-center w-16 h-16 bg-indigo-100 dark:bg-indigo-900 rounded-full mb-4"
          >
            <svg
              className="w-8 h-8 text-indigo-600 dark:text-indigo-400"
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
          </motion.div>

          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Create Learning Schedule
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Set up a personalized learning schedule that works for your family
          </p>
        </div>
      </FadeInWhenVisible>

      <div className="space-y-8">
        {/* Weekly Goal */}
        <FadeInWhenVisible delay={0.2}>
          <div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Weekly Learning Goal
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              How many hours per week would you like your child to spend
              learning with AIVO?
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {weeklyGoalOptions.map(option => (
                <button
                  key={option.value}
                  onClick={() => handleWeeklyGoalChange(option.value)}
                  className={`p-4 border-2 rounded-lg text-center transition-all ${
                    schedule.weeklyGoal === option.value
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'
                  }`}
                >
                  <div className="text-2xl font-bold text-gray-900 dark:text-white">
                    {option.value}h
                  </div>
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {option.label.split('/')[0]}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {option.description}
                  </div>
                </button>
              ))}
            </div>

            {errors.weeklyGoal && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                {errors.weeklyGoal}
              </p>
            )}
          </div>
        </FadeInWhenVisible>

        {/* Time Slots */}
        <FadeInWhenVisible delay={0.3}>
          <div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Preferred Time Slots
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              When does your child learn best? Select all that apply.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {timeSlotOptions.map(slot => (
                <button
                  key={slot.value}
                  onClick={() => handleTimeSlotToggle(slot.value)}
                  className={`p-4 border-2 rounded-lg text-left transition-all ${
                    schedule.preferredTimeSlots.includes(slot.value)
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{slot.icon}</span>
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {slot.label}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {slot.time}
                      </div>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            {errors.preferredTimeSlots && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                {errors.preferredTimeSlots}
              </p>
            )}
          </div>
        </FadeInWhenVisible>

        {/* Subjects */}
        <FadeInWhenVisible delay={0.4}>
          <div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Subject Preferences
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Which subjects would you like to focus on? Select all that
              interest your child.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {subjectOptions.map(subject => (
                <button
                  key={subject.value}
                  onClick={() => handleSubjectToggle(subject.value)}
                  className={`p-4 border-2 rounded-lg text-left transition-all ${getColorClasses(
                    subject.color,
                    schedule.subjects.includes(subject.value)
                  )}`}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">{subject.icon}</span>
                    <span className="font-medium">{subject.label}</span>
                  </div>
                </button>
              ))}
            </div>

            {errors.subjects && (
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">
                {errors.subjects}
              </p>
            )}
          </div>
        </FadeInWhenVisible>

        {/* Difficulty Level */}
        <FadeInWhenVisible delay={0.5}>
          <div>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Learning Difficulty
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              What level of challenge is appropriate for your child?
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {difficultyOptions.map(option => (
                <button
                  key={option.value}
                  onClick={() => handleDifficultyChange(option.value)}
                  className={`p-6 border-2 rounded-lg text-center transition-all ${
                    schedule.difficulty === option.value
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-gray-300 dark:border-gray-600 hover:border-blue-400'
                  }`}
                >
                  <div className="text-3xl mb-2">{option.icon}</div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                    {option.label}
                  </div>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    {option.description}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </FadeInWhenVisible>

        {/* Summary */}
        <FadeInWhenVisible delay={0.6}>
          <div className="p-6 bg-gray-50 dark:bg-gray-900 rounded-lg border">
            <h3 className="font-semibold text-gray-900 dark:text-white mb-4">
              Schedule Summary
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
              <div>
                <div className="text-gray-600 dark:text-gray-400 mb-1">
                  Weekly Goal
                </div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {schedule.weeklyGoal} hours per week
                </div>
              </div>
              <div>
                <div className="text-gray-600 dark:text-gray-400 mb-1">
                  Difficulty Level
                </div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {
                    difficultyOptions.find(d => d.value === schedule.difficulty)
                      ?.label
                  }
                </div>
              </div>
              <div>
                <div className="text-gray-600 dark:text-gray-400 mb-1">
                  Preferred Times
                </div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {schedule.preferredTimeSlots.length > 0
                    ? schedule.preferredTimeSlots
                        .map(
                          slot =>
                            timeSlotOptions.find(s => s.value === slot)?.label
                        )
                        .join(', ')
                    : 'None selected'}
                </div>
              </div>
              <div>
                <div className="text-gray-600 dark:text-gray-400 mb-1">
                  Focus Subjects
                </div>
                <div className="font-medium text-gray-900 dark:text-white">
                  {schedule.subjects.length > 0
                    ? schedule.subjects
                        .map(
                          subject =>
                            subjectOptions.find(s => s.value === subject)?.label
                        )
                        .join(', ')
                    : 'None selected'}
                </div>
              </div>
            </div>
          </div>
        </FadeInWhenVisible>
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-8">
        <Button variant="outline" onClick={onBack}>
          ← Previous: Plan
        </Button>

        <Button onClick={handleContinue}>Complete Setup →</Button>
      </div>
    </div>
  )
}
