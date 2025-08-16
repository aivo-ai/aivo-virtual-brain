import React, { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import { VoiceSelect } from '../forms/VoiceSelect'
import { ToneSelect } from '../forms/ToneSelect'
import {
  learnerClient,
  type BrainPersona as BrainPersonaType,
} from '../../api/learnerClient'

interface BrainPersonaProps {
  learnerId: string
  userRole: 'guardian' | 'teacher' | 'learner'
  onUpdate?: () => void
}

export const BrainPersona: React.FC<BrainPersonaProps> = ({
  learnerId,
  userRole,
  onUpdate,
}) => {
  const [persona, setPersona] = useState<BrainPersonaType | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)

  // Form state
  const [formData, setFormData] = useState<{
    alias: string
    voice: 'friendly' | 'encouraging' | 'professional' | 'playful'
    tone: 'casual' | 'formal' | 'nurturing' | 'direct'
  }>({
    alias: '',
    voice: 'friendly',
    tone: 'casual',
  })
  const [aliasError, setAliasError] = useState<string>('')

  const loadPersona = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const personaData = await learnerClient.getBrainPersona(learnerId)
      setPersona(personaData)
      setFormData({
        alias: personaData.alias || '',
        voice: personaData.voice || 'friendly',
        tone: personaData.tone || 'casual',
      })
    } catch (err) {
      console.error('Error loading persona:', err)
      setError('Failed to load brain persona')
    } finally {
      setLoading(false)
    }
  }, [learnerId])

  useEffect(() => {
    loadPersona()
  }, [loadPersona])

  const validateAlias = async (alias: string): Promise<boolean> => {
    if (!alias || alias.length < 2) {
      setAliasError('Alias must be at least 2 characters long')
      return false
    }

    if (alias.length > 50) {
      setAliasError('Alias must be maximum 50 characters long')
      return false
    }

    try {
      const sanitizedAlias = learnerClient.sanitizePersona({ alias })
      if (!sanitizedAlias.isValid) {
        setAliasError(
          sanitizedAlias.reason ||
            'This alias contains inappropriate language or personal information'
        )
        return false
      }

      setAliasError('')
      return true
    } catch {
      setAliasError('Unable to validate alias')
      return false
    }
  }

  const handleAliasChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const newAlias = e.target.value
    setFormData(prev => ({ ...prev, alias: newAlias }))

    if (newAlias) {
      await validateAlias(newAlias)
    } else {
      setAliasError('')
    }
  }

  const handleAliasBlur = async () => {
    if (formData.alias) {
      await validateAlias(formData.alias)
    }
  }

  const handleSave = async () => {
    if (!(await validateAlias(formData.alias))) {
      return
    }

    try {
      setSaving(true)
      setError(null)

      await learnerClient.updateBrainPersona(learnerId, {
        alias: formData.alias,
        voice: formData.voice,
        tone: formData.tone,
      })

      setSaveSuccess(true)
      setTimeout(() => setSaveSuccess(false), 3000)

      setIsEditing(false)
      await loadPersona()
      onUpdate?.()
    } catch (err) {
      console.error('Error saving persona:', err)
      setError('Failed to save brain persona')
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    setFormData({
      alias: persona?.alias || '',
      voice: persona?.voice || 'friendly',
      tone: persona?.tone || 'casual',
    })
    setAliasError('')
  }

  const handleVoicePreview = async (_voice: string) => {
    // Simulate voice preview
    return new Promise(resolve => {
      setTimeout(resolve, 1500)
    })
  }

  const handleTonePreview = async (_tone: string) => {
    // Simulate tone preview
    return new Promise(resolve => {
      setTimeout(resolve, 1500)
    })
  }

  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-1/3"></div>
          <div className="h-20 bg-gray-200 dark:bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  if (error && !persona) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="text-center text-red-600 dark:text-red-400">
          {error}
        </div>
      </div>
    )
  }

  const canEdit = userRole === 'guardian' || userRole === 'teacher'

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6"
      data-testid="brain-persona-section"
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Brain Persona
        </h2>
        {canEdit && !isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            data-testid="edit-persona-btn"
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            Edit Persona
          </button>
        )}
      </div>

      {saveSuccess && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          data-testid="save-success"
          className="mb-4 p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md text-green-800 dark:text-green-200 text-sm"
        >
          Persona updated successfully!
        </motion.div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md text-red-800 dark:text-red-200 text-sm">
          {error}
        </div>
      )}

      {!isEditing ? (
        // Display Mode
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Persona Name
            </label>
            <p
              className="text-gray-900 dark:text-white"
              data-testid="persona-alias"
            >
              {persona?.alias || 'Not set'}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Voice Type
              </label>
              <p
                className="text-gray-900 dark:text-white capitalize"
                data-testid="persona-voice"
              >
                {persona?.voice || 'Not set'}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Communication Tone
              </label>
              <p
                className="text-gray-900 dark:text-white capitalize"
                data-testid="persona-tone"
              >
                {persona?.tone || 'Not set'}
              </p>
            </div>
          </div>
        </div>
      ) : (
        // Edit Mode
        <div className="space-y-6" data-testid="persona-edit-form">
          <div>
            <label
              htmlFor="alias"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
            >
              Persona Name
            </label>
            <input
              type="text"
              id="alias"
              data-testid="alias-input"
              value={formData.alias}
              onChange={handleAliasChange}
              onBlur={handleAliasBlur}
              placeholder="Enter a name for your AI tutor"
              className={`w-full px-3 py-2 border rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 ${
                aliasError
                  ? 'border-red-300 dark:border-red-600'
                  : 'border-gray-300 dark:border-gray-600'
              } bg-white dark:bg-gray-700 text-gray-900 dark:text-white`}
            />
            {aliasError && (
              <p
                className="mt-1 text-sm text-red-600 dark:text-red-400"
                data-testid="alias-error"
              >
                {aliasError}
              </p>
            )}
          </div>

          <VoiceSelect
            value={formData.voice}
            onChange={voice =>
              setFormData(prev => ({
                ...prev,
                voice: voice as
                  | 'friendly'
                  | 'encouraging'
                  | 'professional'
                  | 'playful',
              }))
            }
            onPreview={handleVoicePreview}
          />

          <ToneSelect
            value={formData.tone}
            onChange={tone =>
              setFormData(prev => ({
                ...prev,
                tone: tone as 'casual' | 'formal' | 'nurturing' | 'direct',
              }))
            }
            onPreview={handleTonePreview}
          />

          <div className="flex space-x-3">
            <button
              onClick={handleSave}
              disabled={saving || !!aliasError || !formData.alias}
              data-testid="save-persona-btn"
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white px-4 py-2 rounded-md transition-colors"
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button
              onClick={handleCancel}
              disabled={saving}
              className="bg-gray-300 hover:bg-gray-400 text-gray-700 px-4 py-2 rounded-md transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
