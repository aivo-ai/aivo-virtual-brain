import React, { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Textarea } from '@/components/ui/Textarea'
import { Label } from '@/components/ui/Label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/Badge'
import {
  Upload,
  Save,
  Eye,
  Send,
  Plus,
  Trash2,
  Image,
  Video,
  FileText,
  Book,
} from 'lucide-react'

interface ContentBlock {
  id: string
  type: 'text' | 'heading' | 'image' | 'video' | 'quiz' | 'code'
  content: any
  order: number
}

interface LessonDraft {
  id?: string
  title: string
  description: string
  subject: string
  grade_level: string
  content_blocks: ContentBlock[]
  learning_objectives: string[]
  status: 'draft' | 'under_review' | 'approved' | 'published'
  completion_percentage: number
  is_valid: boolean
  validation_errors: string[]
}

interface DraftAsset {
  id: string
  filename: string
  original_filename: string
  content_type: string
  size_bytes: number
  asset_type: string
  temp_url: string
}

const TeacherContentAuthoringPage: React.FC = () => {
  const [draft, setDraft] = useState<LessonDraft>({
    title: '',
    description: '',
    subject: '',
    grade_level: '',
    content_blocks: [],
    learning_objectives: [],
    status: 'draft',
    completion_percentage: 0,
    is_valid: false,
    validation_errors: [],
  })

  const [assets, setAssets] = useState<DraftAsset[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  // Draft operations
  const saveDraft = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/v1/authoring/drafts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify(draft),
      })

      if (response.ok) {
        const savedDraft = await response.json()
        setDraft(savedDraft)
        console.log('Draft saved successfully')
      }
    } catch (error) {
      console.error('Failed to save draft:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Asset upload
  const uploadAsset = async () => {
    if (!selectedFile || !draft.id) return

    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('asset_type', getAssetType(selectedFile.type))
    formData.append('usage_context', 'lesson_content')

    setIsLoading(true)
    try {
      const response = await fetch(
        `/api/v1/authoring/drafts/${draft.id}/assets`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
          },
          body: formData,
        }
      )

      if (response.ok) {
        const newAsset = await response.json()
        setAssets(prev => [...prev, newAsset])
        setSelectedFile(null)
        console.log('Asset uploaded successfully')
      }
    } catch (error) {
      console.error('Failed to upload asset:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Content block management
  const addContentBlock = (type: ContentBlock['type']) => {
    const newBlock: ContentBlock = {
      id: `block_${Date.now()}`,
      type,
      content: getDefaultContent(type),
      order: draft.content_blocks.length,
    }

    setDraft(prev => ({
      ...prev,
      content_blocks: [...prev.content_blocks, newBlock],
    }))
  }

  const updateContentBlock = (blockId: string, content: any) => {
    setDraft(prev => ({
      ...prev,
      content_blocks: prev.content_blocks.map(block =>
        block.id === blockId ? { ...block, content } : block
      ),
    }))
  }

  const removeContentBlock = (blockId: string) => {
    setDraft(prev => ({
      ...prev,
      content_blocks: prev.content_blocks.filter(block => block.id !== blockId),
    }))
  }

  // Learning objectives management
  const addLearningObjective = () => {
    setDraft(prev => ({
      ...prev,
      learning_objectives: [...prev.learning_objectives, ''],
    }))
  }

  const updateLearningObjective = (index: number, value: string) => {
    setDraft(prev => ({
      ...prev,
      learning_objectives: prev.learning_objectives.map((obj, i) =>
        i === index ? value : obj
      ),
    }))
  }

  const removeLearningObjective = (index: number) => {
    setDraft(prev => ({
      ...prev,
      learning_objectives: prev.learning_objectives.filter(
        (_, i) => i !== index
      ),
    }))
  }

  // Publish workflow
  const publishDraft = async () => {
    if (!draft.id) return

    setIsLoading(true)
    try {
      const response = await fetch(
        `/api/v1/authoring/drafts/${draft.id}/publish`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
          },
          body: JSON.stringify({
            version_number: '1.0.0',
            changelog: 'Initial lesson version',
            publish_immediately: false,
            requires_approval: true,
          }),
        }
      )

      if (response.ok) {
        const workflow = await response.json()
        console.log('Publishing workflow initiated:', workflow)
      }
    } catch (error) {
      console.error('Failed to publish draft:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Utility functions
  const getAssetType = (mimeType: string): string => {
    if (mimeType.startsWith('image/')) return 'image'
    if (mimeType.startsWith('video/')) return 'video'
    if (mimeType.startsWith('audio/')) return 'audio'
    return 'document'
  }

  const getDefaultContent = (type: ContentBlock['type']): any => {
    switch (type) {
      case 'text':
        return { text: '' }
      case 'heading':
        return { level: 2, text: '' }
      case 'image':
        return { src: '', alt: '', caption: '' }
      case 'video':
        return { src: '', title: '', duration: 0 }
      case 'quiz':
        return { question: '', options: [], correct_answer: 0 }
      case 'code':
        return { language: 'javascript', code: '' }
      default:
        return {}
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          <Book className="h-8 w-8" />
          Lesson Authoring
        </h1>
        <div className="flex gap-2">
          <Button onClick={saveDraft} disabled={isLoading}>
            <Save className="h-4 w-4 mr-2" />
            Save Draft
          </Button>
          <Button variant="outline">
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </Button>
          <Button
            onClick={publishDraft}
            disabled={!draft.is_valid || isLoading}
          >
            <Send className="h-4 w-4 mr-2" />
            Publish
          </Button>
        </div>
      </div>

      {/* Status and Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            Lesson Status
            <Badge variant={draft.status === 'draft' ? 'secondary' : 'default'}>
              {draft.status}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <div className="text-sm text-gray-600 mb-1">
                Completion: {draft.completion_percentage}%
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{ width: `${draft.completion_percentage}%` }}
                />
              </div>
            </div>
            <div className="text-sm">
              {draft.is_valid ? (
                <span className="text-green-600">✓ Valid</span>
              ) : (
                <span className="text-red-600">
                  ⚠ {draft.validation_errors.length} errors
                </span>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Basic Information */}
          <Card>
            <CardHeader>
              <CardTitle>Lesson Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
                  value={draft.title}
                  onChange={e =>
                    setDraft(prev => ({ ...prev, title: e.target.value }))
                  }
                  placeholder="Enter lesson title"
                />
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={draft.description}
                  onChange={e =>
                    setDraft(prev => ({ ...prev, description: e.target.value }))
                  }
                  placeholder="Describe this lesson"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="subject">Subject</Label>
                  <Select
                    value={draft.subject}
                    onValueChange={value =>
                      setDraft(prev => ({ ...prev, subject: value }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select subject" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="math">Mathematics</SelectItem>
                      <SelectItem value="science">Science</SelectItem>
                      <SelectItem value="english">English</SelectItem>
                      <SelectItem value="history">History</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="grade_level">Grade Level</Label>
                  <Select
                    value={draft.grade_level}
                    onValueChange={value =>
                      setDraft(prev => ({ ...prev, grade_level: value }))
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select grade" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="K">Kindergarten</SelectItem>
                      <SelectItem value="1">Grade 1</SelectItem>
                      <SelectItem value="2">Grade 2</SelectItem>
                      <SelectItem value="3">Grade 3</SelectItem>
                      <SelectItem value="4">Grade 4</SelectItem>
                      <SelectItem value="5">Grade 5</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Learning Objectives */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Learning Objectives
                <Button size="sm" onClick={addLearningObjective}>
                  <Plus className="h-4 w-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {draft.learning_objectives.map((objective, index) => (
                <div key={index} className="flex gap-2">
                  <Input
                    value={objective}
                    onChange={e =>
                      updateLearningObjective(index, e.target.value)
                    }
                    placeholder="Students will be able to..."
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => removeLearningObjective(index)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Content Blocks */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Content Blocks
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => addContentBlock('text')}>
                    <FileText className="h-4 w-4 mr-1" />
                    Text
                  </Button>
                  <Button size="sm" onClick={() => addContentBlock('image')}>
                    <Image className="h-4 w-4 mr-1" />
                    Image
                  </Button>
                  <Button size="sm" onClick={() => addContentBlock('video')}>
                    <Video className="h-4 w-4 mr-1" />
                    Video
                  </Button>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {draft.content_blocks.map((block, index) => (
                <div key={block.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <Badge variant="outline">{block.type}</Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => removeContentBlock(block.id)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>

                  {block.type === 'text' && (
                    <Textarea
                      value={block.content.text || ''}
                      onChange={e =>
                        updateContentBlock(block.id, { text: e.target.value })
                      }
                      placeholder="Enter text content"
                      rows={4}
                    />
                  )}

                  {block.type === 'heading' && (
                    <div className="space-y-2">
                      <Select
                        value={block.content.level?.toString() || '2'}
                        onValueChange={value =>
                          updateContentBlock(block.id, {
                            ...block.content,
                            level: parseInt(value),
                          })
                        }
                      >
                        <SelectTrigger className="w-32">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">H1</SelectItem>
                          <SelectItem value="2">H2</SelectItem>
                          <SelectItem value="3">H3</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input
                        value={block.content.text || ''}
                        onChange={e =>
                          updateContentBlock(block.id, {
                            ...block.content,
                            text: e.target.value,
                          })
                        }
                        placeholder="Heading text"
                      />
                    </div>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        </div>

        {/* Asset Management Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Asset Library</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="file-upload">Upload New Asset</Label>
                <div className="mt-1">
                  <input
                    id="file-upload"
                    type="file"
                    onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                    accept="image/*,video/*,audio/*,.pdf,.doc,.docx"
                    className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                  />
                </div>
                {selectedFile && (
                  <Button
                    onClick={uploadAsset}
                    className="mt-2 w-full"
                    disabled={isLoading}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Upload Asset
                  </Button>
                )}
              </div>

              <div className="space-y-2">
                <Label>Uploaded Assets</Label>
                {assets.map(asset => (
                  <div
                    key={asset.id}
                    className="flex items-center justify-between p-2 border rounded"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {asset.original_filename}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(asset.size_bytes / 1024).toFixed(1)} KB
                      </p>
                    </div>
                    <Badge variant="secondary" className="ml-2">
                      {asset.asset_type}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Publishing</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-gray-600">
                Ready to publish your lesson? This will create a new version and
                send it for review.
              </div>

              <Button
                onClick={publishDraft}
                className="w-full"
                disabled={!draft.is_valid || isLoading}
              >
                <Send className="h-4 w-4 mr-2" />
                Submit for Review
              </Button>

              {draft.validation_errors.length > 0 && (
                <div className="text-sm text-red-600">
                  <div className="font-medium">Validation Errors:</div>
                  <ul className="mt-1 list-disc list-inside">
                    {draft.validation_errors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default TeacherContentAuthoringPage
