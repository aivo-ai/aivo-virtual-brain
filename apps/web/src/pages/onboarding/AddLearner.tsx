import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '../../components/ui/Button'
import { FadeInWhenVisible } from '../../components/ui/Animations'
import { LearnerProfile, UseOnboardingReturn } from '../../hooks/useOnboarding'

interface AddLearnerStepProps {
  onboardingData: UseOnboardingReturn
  onNext: () => void
  onBack: () => void
}

interface LearnerFormData extends LearnerProfile {
  id?: string
}

export const AddLearnerStep: React.FC<AddLearnerStepProps> = ({
  onboardingData,
  onNext,
  onBack,
}) => {
  const {
    state,
    addLearner: addLearnerToState,
    updateLearner,
    removeLearner,
    calculateGrade,
    getGradeBand,
  } = onboardingData
  const [currentLearners, setCurrentLearners] = useState<LearnerFormData[]>(
    state.learners.map((l, i) => ({ ...l, id: `learner-${i}` }))
  )
  const [showAddForm, setShowAddForm] = useState(state.learners.length === 0)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [errors, setErrors] = useState<Record<string, Partial<LearnerProfile>>>(
    {}
  )

  const interests = [
    'Math',
    'Science',
    'Reading',
    'Writing',
    'History',
    'Art',
    'Music',
    'Sports',
    'Technology',
    'Languages',
    'Drama',
    'Dance',
    'Coding',
  ]

  const emptyLearner: LearnerFormData = {
    id: `learner-${Date.now()}`,
    firstName: '',
    lastName: '',
    dateOfBirth: '',
    gradeDefault: 0,
    gradeBand: '',
    specialNeeds: '',
    interests: [],
  }

  useEffect(() => {
    setCurrentLearners(
      state.learners.map((l, i) => ({ ...l, id: `learner-${i}` }))
    )
  }, [state.learners])

  const validateLearner = (
    learner: LearnerFormData
  ): Partial<LearnerProfile> => {
    const newErrors: Partial<LearnerProfile> = {}

    if (!learner.firstName.trim()) {
      newErrors.firstName = 'First name is required'
    }

    if (!learner.lastName.trim()) {
      newErrors.lastName = 'Last name is required'
    }

    if (!learner.dateOfBirth) {
      newErrors.dateOfBirth = 'Date of birth is required'
    } else {
      const birthDate = new Date(learner.dateOfBirth)
      const today = new Date()
      const age = today.getFullYear() - birthDate.getFullYear()

      if (age < 3 || age > 18) {
        newErrors.dateOfBirth = 'Learner must be between 3 and 18 years old'
      }
    }

    return newErrors
  }

  const handleAddNewLearner = () => {
    const newLearner = { ...emptyLearner, id: `learner-${Date.now()}` }
    setCurrentLearners(prev => [...prev, newLearner])
    setEditingId(newLearner.id!)
    setShowAddForm(true)
  }

  const handleSaveLearner = (learnerData: LearnerFormData) => {
    const validationErrors = validateLearner(learnerData)

    if (Object.keys(validationErrors).length > 0) {
      setErrors(prev => ({ ...prev, [learnerData.id!]: validationErrors }))
      return
    }

    // Clear errors
    setErrors(prev => {
      const newErrors = { ...prev }
      delete newErrors[learnerData.id!]
      return newErrors
    })

    // Calculate grade and grade band
    const grade = calculateGrade(learnerData.dateOfBirth)
    const gradeBand = getGradeBand(grade)

    const updatedLearner: LearnerProfile = {
      ...learnerData,
      gradeDefault: grade,
      gradeBand,
    }

    // Find if this is an existing learner or new
    const existingIndex = currentLearners.findIndex(
      l => l.id === learnerData.id
    )
    if (existingIndex >= 0) {
      setCurrentLearners(prev =>
        prev.map((l, i) =>
          i === existingIndex ? { ...updatedLearner, id: l.id } : l
        )
      )
      updateLearner(existingIndex, updatedLearner)
    } else {
      addLearnerToState(updatedLearner)
    }

    setEditingId(null)
    setShowAddForm(false)
  }

  const handleRemoveLearner = (id: string) => {
    const index = currentLearners.findIndex(l => l.id === id)
    if (index >= 0) {
      setCurrentLearners(prev => prev.filter(l => l.id !== id))
      removeLearner(index)
    }
  }

  const handleNext = () => {
    if (currentLearners.length === 0) {
      alert('Please add at least one learner to continue.')
      return
    }
    onNext()
  }

  return (
    <div className="max-w-4xl mx-auto">
      <FadeInWhenVisible>
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Add Your Learners
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            Tell us about the children who will be using AIVO
          </p>
        </div>
      </FadeInWhenVisible>

      {/* Existing Learners */}
      {currentLearners.length > 0 && (
        <FadeInWhenVisible>
          <div className="mb-8">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
              Learners ({currentLearners.length})
            </h3>
            <div className="space-y-4">
              {currentLearners.map(learner => (
                <motion.div
                  key={learner.id}
                  className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-lg font-semibold text-gray-900 dark:text-white">
                        {learner.firstName} {learner.lastName}
                      </h4>
                      <p className="text-gray-600 dark:text-gray-400">
                        {learner.gradeBand} • Grade {learner.gradeDefault}
                      </p>
                      {learner.interests && learner.interests.length > 0 && (
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                          Interests: {learner.interests.join(', ')}
                        </p>
                      )}
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setEditingId(learner.id!)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleRemoveLearner(learner.id!)}
                        className="text-red-600 border-red-300 hover:bg-red-50"
                      >
                        Remove
                      </Button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </FadeInWhenVisible>
      )}

      {/* Add New Learner Button */}
      {!showAddForm && !editingId && (
        <FadeInWhenVisible>
          <div className="text-center mb-8">
            <Button onClick={handleAddNewLearner} size="lg" className="px-8">
              + Add Learner
            </Button>
          </div>
        </FadeInWhenVisible>
      )}

      {/* Add/Edit Form */}
      <AnimatePresence>
        {(showAddForm || editingId) && (
          <LearnerForm
            learner={
              editingId
                ? currentLearners.find(l => l.id === editingId) || emptyLearner
                : emptyLearner
            }
            interests={interests}
            errors={editingId ? errors[editingId] || {} : {}}
            onSave={handleSaveLearner}
            onCancel={() => {
              setShowAddForm(false)
              setEditingId(null)
            }}
          />
        )}
      </AnimatePresence>

      {/* Navigation */}
      <FadeInWhenVisible>
        <div className="flex justify-between mt-12">
          <Button variant="outline" onClick={onBack}>
            ← Previous
          </Button>
          <Button onClick={handleNext} disabled={currentLearners.length === 0}>
            Continue →
          </Button>
        </div>
      </FadeInWhenVisible>
    </div>
  )
}

interface LearnerFormProps {
  learner: LearnerFormData
  interests: string[]
  errors: Partial<LearnerProfile>
  onSave: (learner: LearnerFormData) => void
  onCancel: () => void
}

const LearnerForm: React.FC<LearnerFormProps> = ({
  learner,
  interests,
  errors,
  onSave,
  onCancel,
}) => {
  const [formData, setFormData] = useState<LearnerFormData>(learner)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave(formData)
  }

  const toggleInterest = (interest: string) => {
    setFormData(prev => ({
      ...prev,
      interests: (prev.interests || []).includes(interest)
        ? (prev.interests || []).filter(i => i !== interest)
        : [...(prev.interests || []), interest],
    }))
  }

  return (
    <motion.div
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 mb-8"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
    >
      <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-6">
        {learner.firstName ? 'Edit Learner' : 'Add New Learner'}
      </h3>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              First Name *
            </label>
            <input
              type="text"
              value={formData.firstName}
              onChange={e =>
                setFormData(prev => ({ ...prev, firstName: e.target.value }))
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="Enter first name"
            />
            {errors.firstName && (
              <p className="text-red-500 text-sm mt-1">{errors.firstName}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Last Name *
            </label>
            <input
              type="text"
              value={formData.lastName}
              onChange={e =>
                setFormData(prev => ({ ...prev, lastName: e.target.value }))
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="Enter last name"
            />
            {errors.lastName && (
              <p className="text-red-500 text-sm mt-1">{errors.lastName}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Date of Birth *
            </label>
            <input
              type="date"
              value={formData.dateOfBirth}
              onChange={e =>
                setFormData(prev => ({ ...prev, dateOfBirth: e.target.value }))
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            />
            {errors.dateOfBirth && (
              <p className="text-red-500 text-sm mt-1">{errors.dateOfBirth}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Special Needs (Optional)
            </label>
            <textarea
              value={formData.specialNeeds}
              onChange={e =>
                setFormData(prev => ({ ...prev, specialNeeds: e.target.value }))
              }
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              rows={3}
              placeholder="Any learning accommodations or special needs..."
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            Interests (Select all that apply)
          </label>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {interests.map(interest => (
              <button
                key={interest}
                type="button"
                onClick={() => toggleInterest(interest)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  (formData.interests || []).includes(interest)
                    ? 'bg-blue-100 text-blue-800 border-blue-300 dark:bg-blue-900 dark:text-blue-200'
                    : 'bg-gray-100 text-gray-700 border-gray-300 dark:bg-gray-700 dark:text-gray-300'
                } border hover:opacity-80`}
              >
                {interest}
              </button>
            ))}
          </div>
        </div>

        <div className="flex justify-end space-x-4">
          <Button type="button" variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit">Save Learner</Button>
        </div>
      </form>
    </motion.div>
  )
}
