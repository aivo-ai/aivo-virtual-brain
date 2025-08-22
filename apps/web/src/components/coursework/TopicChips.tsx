import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { X, Plus, BookOpen, Tag, GraduationCap } from 'lucide-react'

interface TopicChipsProps {
  suggestedSubjects: string[]
  suggestedTopics: string[]
  suggestedGradeBands: string[]
  selectedSubject: string
  selectedTopics: string[]
  selectedGradeBand: string
  onSubjectChange: (subject: string) => void
  onTopicsChange: (topics: string[]) => void
  onGradeBandChange: (gradeBand: string) => void
}

export default function TopicChips({
  suggestedSubjects,
  suggestedTopics,
  selectedSubject,
  selectedTopics,
  selectedGradeBand,
  onSubjectChange,
  onTopicsChange,
  onGradeBandChange,
}: TopicChipsProps) {
  const { t } = useTranslation('coursework')
  const [newTopic, setNewTopic] = useState('')
  const [customSubject, setCustomSubject] = useState('')
  const [showCustomSubject, setShowCustomSubject] = useState(false)

  // Default subjects if none suggested
  const defaultSubjects = [
    'Mathematics',
    'English Language Arts',
    'Science',
    'Social Studies',
    'History',
    'Geography',
    'Physics',
    'Chemistry',
    'Biology',
    'Art',
  ]

  // Default grade bands if none suggested
  const defaultGradeBands = [
    'Kindergarten',
    'Grade 1',
    'Grade 2',
    'Grade 3',
    'Grade 4',
    'Grade 5',
    'Grade 6',
    'Grade 7',
    'Grade 8',
    'Grade 9',
    'Grade 10',
    'Grade 11',
    'Grade 12',
  ]

  const availableSubjects =
    suggestedSubjects.length > 0 ? suggestedSubjects : defaultSubjects
  const availableGradeBands = defaultGradeBands

  const handleSubjectSelect = (value: string) => {
    if (value === 'custom') {
      setShowCustomSubject(true)
      return
    }
    onSubjectChange(value)
    setShowCustomSubject(false)
    setCustomSubject('')
  }

  const handleCustomSubjectSubmit = () => {
    if (customSubject.trim()) {
      onSubjectChange(customSubject.trim())
      setShowCustomSubject(false)
      setCustomSubject('')
    }
  }

  const handleAddTopic = () => {
    if (newTopic.trim() && !selectedTopics.includes(newTopic.trim())) {
      onTopicsChange([...selectedTopics, newTopic.trim()])
      setNewTopic('')
    }
  }

  const handleRemoveTopic = (topicToRemove: string) => {
    onTopicsChange(selectedTopics.filter(topic => topic !== topicToRemove))
  }

  const handleSuggestedTopicClick = (topic: string) => {
    if (!selectedTopics.includes(topic)) {
      onTopicsChange([...selectedTopics, topic])
    }
  }

  const handleKeyPress = (
    e: React.KeyboardEvent<HTMLInputElement>,
    action: () => void
  ) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      action()
    }
  }

  return (
    <div className="space-y-6">
      {/* Subject Selection */}
      <div className="space-y-3">
        <Label className="flex items-center space-x-2">
          <BookOpen className="h-4 w-4" />
          <span>{t('metadata.subject.label')} *</span>
        </Label>

        {showCustomSubject ? (
          <div className="flex space-x-2">
            <Input
              value={customSubject}
              onChange={e => setCustomSubject(e.target.value)}
              placeholder={t('metadata.subject.customPlaceholder')}
              onKeyPress={e => handleKeyPress(e, handleCustomSubjectSubmit)}
            />
            <Button onClick={handleCustomSubjectSubmit} size="sm">
              <Plus className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setShowCustomSubject(false)
                setCustomSubject('')
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <Select value={selectedSubject} onValueChange={handleSubjectSelect}>
            <SelectTrigger>
              <SelectValue placeholder={t('metadata.subject.placeholder')} />
            </SelectTrigger>
            <SelectContent>
              {availableSubjects.map(subject => (
                <SelectItem key={subject} value={subject}>
                  {subject}
                </SelectItem>
              ))}
              <SelectItem value="custom">
                <span className="flex items-center space-x-2">
                  <Plus className="h-4 w-4" />
                  <span>{t('metadata.subject.custom')}</span>
                </span>
              </SelectItem>
            </SelectContent>
          </Select>
        )}

        {selectedSubject && (
          <div className="flex items-center space-x-2">
            <Badge variant="default" className="text-sm">
              {selectedSubject}
            </Badge>
          </div>
        )}
      </div>

      {/* Grade Band Selection */}
      <div className="space-y-3">
        <Label className="flex items-center space-x-2">
          <GraduationCap className="h-4 w-4" />
          <span>{t('metadata.gradeBand.label')}</span>
        </Label>

        <Select value={selectedGradeBand} onValueChange={onGradeBandChange}>
          <SelectTrigger>
            <SelectValue placeholder={t('metadata.gradeBand.placeholder')} />
          </SelectTrigger>
          <SelectContent>
            {availableGradeBands.map(grade => (
              <SelectItem key={grade} value={grade}>
                {grade}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {selectedGradeBand && (
          <div className="flex items-center space-x-2">
            <Badge variant="secondary" className="text-sm">
              {selectedGradeBand}
            </Badge>
          </div>
        )}
      </div>

      {/* Topics */}
      <div className="space-y-3">
        <Label className="flex items-center space-x-2">
          <Tag className="h-4 w-4" />
          <span>{t('metadata.topics.label')}</span>
        </Label>

        {/* Add New Topic */}
        <div className="flex space-x-2">
          <Input
            value={newTopic}
            onChange={e => setNewTopic(e.target.value)}
            placeholder={t('metadata.topics.placeholder')}
            onKeyPress={e => handleKeyPress(e, handleAddTopic)}
          />
          <Button
            onClick={handleAddTopic}
            size="sm"
            disabled={!newTopic.trim()}
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {/* Selected Topics */}
        {selectedTopics.length > 0 && (
          <div>
            <p className="text-sm text-muted-foreground mb-2">
              {t('metadata.topics.selected')}
            </p>
            <div className="flex flex-wrap gap-2">
              {selectedTopics.map((topic, idx) => (
                <Badge key={idx} variant="outline" className="text-sm">
                  {topic}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-1 h-4 w-4 p-0 hover:bg-transparent"
                    onClick={() => handleRemoveTopic(topic)}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Suggested Topics */}
        {suggestedTopics.length > 0 && (
          <div>
            <p className="text-sm text-muted-foreground mb-2">
              {t('metadata.topics.suggested')}
            </p>
            <div className="flex flex-wrap gap-2">
              {suggestedTopics
                .filter(topic => !selectedTopics.includes(topic))
                .map((topic, idx) => (
                  <Button
                    key={idx}
                    variant="ghost"
                    size="sm"
                    className="h-auto p-1 px-2 text-xs border border-dashed"
                    onClick={() => handleSuggestedTopicClick(topic)}
                  >
                    <Plus className="h-3 w-3 mr-1" />
                    {topic}
                  </Button>
                ))}
            </div>
          </div>
        )}
      </div>

      {/* Validation */}
      {!selectedSubject && (
        <div className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded p-3">
          {t('metadata.validation.subjectRequired')}
        </div>
      )}
    </div>
  )
}
