/**
 * S3-12 SLP Therapy Plan Component
 * Displays and manages therapy plans with session scheduling
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Label } from '../ui/Label'
import { Textarea } from '../ui/Textarea'
import { Badge } from '../ui/Badge'
import { Alert, AlertDescription } from '../ui/Alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/Tabs'
import {
  Calendar,
  Target,
  CheckCircle2,
  AlertTriangle,
  Plus,
  Edit,
  Trash2,
} from '../ui/Icons'
import {
  type SLPPlan,
  type SLPScreening,
  type SLPStudent,
  GoalCategory,
  Priority,
  useSLPMutations,
} from '../../api/slpClient'

interface TherapyPlanProps {
  student: SLPStudent
  screening: SLPScreening
  onPlanCreated: (plan: SLPPlan) => void
  onBack: () => void
}

interface GoalFormData {
  category: GoalCategory
  description: string
  targetBehavior: string
  measurableOutcome: string
  timeframe: string
  priority: Priority
}

const GOAL_CATEGORIES = [
  { value: GoalCategory.ARTICULATION, label: 'Articulation' },
  { value: GoalCategory.LANGUAGE_EXPRESSION, label: 'Language Expression' },
  {
    value: GoalCategory.LANGUAGE_COMPREHENSION,
    label: 'Language Comprehension',
  },
  { value: GoalCategory.FLUENCY, label: 'Fluency' },
  { value: GoalCategory.VOICE, label: 'Voice' },
  { value: GoalCategory.SOCIAL_COMMUNICATION, label: 'Social Communication' },
]

const PRIORITY_LEVELS = [
  { value: Priority.LOW, label: 'Low', color: 'bg-gray-100 text-gray-800' },
  {
    value: Priority.MEDIUM,
    label: 'Medium',
    color: 'bg-yellow-100 text-yellow-800',
  },
  {
    value: Priority.HIGH,
    label: 'High',
    color: 'bg-orange-100 text-orange-800',
  },
  {
    value: Priority.CRITICAL,
    label: 'Critical',
    color: 'bg-red-100 text-red-800',
  },
]

const generateRecommendedGoals = (
  screening: SLPScreening
): Partial<GoalFormData>[] => {
  const goals: Partial<GoalFormData>[] = []

  // Analyze screening responses to generate recommendations
  screening.responses.forEach(response => {
    if (response.score >= 2) {
      // High scoring responses need goals
      if (response.questionId.startsWith('art_')) {
        goals.push({
          category: GoalCategory.ARTICULATION,
          description: 'Improve speech sound production accuracy',
          targetBehavior:
            'Produce target sounds correctly in words and sentences',
          measurableOutcome: '80% accuracy in structured activities',
          timeframe: '12 weeks',
          priority: Priority.HIGH,
        })
      } else if (response.questionId.startsWith('lang_')) {
        goals.push({
          category: GoalCategory.LANGUAGE_EXPRESSION,
          description: 'Enhance expressive language skills',
          targetBehavior: 'Use complete sentences with appropriate grammar',
          measurableOutcome: '90% accuracy in conversation samples',
          timeframe: '16 weeks',
          priority: Priority.MEDIUM,
        })
      } else if (response.questionId.startsWith('flu_')) {
        goals.push({
          category: GoalCategory.FLUENCY,
          description: 'Increase speech fluency',
          targetBehavior: 'Speak with fewer than 3 disfluencies per minute',
          measurableOutcome: 'Maintain fluent speech in 5-minute conversations',
          timeframe: '20 weeks',
          priority: Priority.HIGH,
        })
      } else if (response.questionId.startsWith('voice_')) {
        goals.push({
          category: GoalCategory.VOICE,
          description: 'Improve vocal quality and breath support',
          targetBehavior: 'Use appropriate vocal intensity and quality',
          measurableOutcome: 'Maintain clear voice quality throughout sessions',
          timeframe: '8 weeks',
          priority: Priority.MEDIUM,
        })
      }
    }
  })

  return goals.slice(0, 4) // Limit to 4 goals maximum
}

export function TherapyPlan({
  student,
  screening,
  onPlanCreated,
  onBack,
}: TherapyPlanProps) {
  const [goals, setGoals] = useState<GoalFormData[]>([])
  const [duration, setDuration] = useState(12) // weeks
  const [frequency, setFrequency] = useState(2) // sessions per week
  const [editingGoal, setEditingGoal] = useState<number | null>(null)
  const [currentGoal, setCurrentGoal] = useState<GoalFormData>({
    category: GoalCategory.ARTICULATION,
    description: '',
    targetBehavior: '',
    measurableOutcome: '',
    timeframe: '',
    priority: Priority.MEDIUM,
  })

  const { createPlan, loading, error } = useSLPMutations()

  useEffect(() => {
    // Load recommended goals based on screening
    const recommended = generateRecommendedGoals(screening)
    const initialGoals = recommended.map(goal => ({
      category: goal.category || GoalCategory.ARTICULATION,
      description: goal.description || '',
      targetBehavior: goal.targetBehavior || '',
      measurableOutcome: goal.measurableOutcome || '',
      timeframe: goal.timeframe || '',
      priority: goal.priority || Priority.MEDIUM,
    }))
    setGoals(initialGoals)
  }, [screening])

  const handleAddGoal = () => {
    setGoals(prev => [...prev, currentGoal])
    setCurrentGoal({
      category: GoalCategory.ARTICULATION,
      description: '',
      targetBehavior: '',
      measurableOutcome: '',
      timeframe: '',
      priority: Priority.MEDIUM,
    })
    setEditingGoal(null)
  }

  const handleEditGoal = (index: number) => {
    setCurrentGoal(goals[index])
    setEditingGoal(index)
  }

  const handleUpdateGoal = () => {
    if (editingGoal !== null) {
      const updatedGoals = [...goals]
      updatedGoals[editingGoal] = currentGoal
      setGoals(updatedGoals)
      setEditingGoal(null)
      setCurrentGoal({
        category: GoalCategory.ARTICULATION,
        description: '',
        targetBehavior: '',
        measurableOutcome: '',
        timeframe: '',
        priority: Priority.MEDIUM,
      })
    }
  }

  const handleDeleteGoal = (index: number) => {
    setGoals(prev => prev.filter((_, i) => i !== index))
  }

  const handleCreatePlan = async () => {
    try {
      const result = await createPlan({
        studentId: student.id,
        tenantId: student.tenantId,
        screeningId: screening.id,
        goals: goals.map(goal => ({
          category: goal.category,
          description: goal.description,
          targetBehavior: goal.targetBehavior,
          measurableOutcome: goal.measurableOutcome,
          timeframe: goal.timeframe,
          priority: goal.priority,
        })),
        duration,
        frequency,
      })

      if (result.success) {
        onPlanCreated(result.plan)
      }
    } catch (err) {
      console.error('Failed to create therapy plan:', err)
    }
  }

  const getPriorityColor = (priority: Priority) => {
    return (
      PRIORITY_LEVELS.find(p => p.value === priority)?.color ||
      'bg-gray-100 text-gray-800'
    )
  }

  const totalSessions = duration * frequency
  const estimatedWeeks = Math.ceil(totalSessions / frequency)

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="w-5 h-5" />
            Therapy Plan for {student.firstName} {student.lastName}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="text-center p-4 bg-muted rounded-lg">
              <div className="text-2xl font-bold text-primary">
                {screening.totalScore}
              </div>
              <div className="text-sm text-muted-foreground">
                Screening Score
              </div>
            </div>
            <div className="text-center p-4 bg-muted rounded-lg">
              <Badge
                variant={
                  screening.riskLevel === 'HIGH' ||
                  screening.riskLevel === 'SEVERE'
                    ? 'destructive'
                    : 'secondary'
                }
              >
                {screening.riskLevel}
              </Badge>
              <div className="text-sm text-muted-foreground mt-1">
                Risk Level
              </div>
            </div>
            <div className="text-center p-4 bg-muted rounded-lg">
              <div className="text-2xl font-bold text-primary">
                {screening.recommendations.length}
              </div>
              <div className="text-sm text-muted-foreground">
                Recommendations
              </div>
            </div>
          </div>

          {screening.recommendations.length > 0 && (
            <Alert className="mb-6">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <strong>Recommendations:</strong>
                <ul className="mt-2 space-y-1">
                  {screening.recommendations.map((rec, index) => (
                    <li key={index} className="text-sm">
                      • {rec}
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      <Tabs defaultValue="goals" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="goals">Therapy Goals</TabsTrigger>
          <TabsTrigger value="schedule">Schedule & Duration</TabsTrigger>
        </TabsList>

        <TabsContent value="goals" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Therapy Goals</span>
                <Badge variant="outline">{goals.length} goals</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {goals.map((goal, index) => (
                <Card key={index} className="border-l-4 border-l-primary">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">
                          {goal.category.replace('_', ' ')}
                        </Badge>
                        <Badge className={getPriorityColor(goal.priority)}>
                          {goal.priority}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEditGoal(index)}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteGoal(index)}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0 space-y-2">
                    <div>
                      <Label className="text-sm font-medium">Description</Label>
                      <p className="text-sm text-muted-foreground">
                        {goal.description}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">
                        Target Behavior
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        {goal.targetBehavior}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">
                        Measurable Outcome
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        {goal.measurableOutcome}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium">Timeframe</Label>
                      <p className="text-sm text-muted-foreground">
                        {goal.timeframe}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              ))}

              <Card className="border-dashed">
                <CardHeader>
                  <CardTitle className="text-lg">
                    {editingGoal !== null ? 'Edit Goal' : 'Add New Goal'}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="category">Category</Label>
                      <select
                        id="category"
                        value={currentGoal.category}
                        onChange={e =>
                          setCurrentGoal(prev => ({
                            ...prev,
                            category: e.target.value as GoalCategory,
                          }))
                        }
                        className="w-full p-2 border rounded-md"
                      >
                        {GOAL_CATEGORIES.map(cat => (
                          <option key={cat.value} value={cat.value}>
                            {cat.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label htmlFor="priority">Priority</Label>
                      <select
                        id="priority"
                        value={currentGoal.priority}
                        onChange={e =>
                          setCurrentGoal(prev => ({
                            ...prev,
                            priority: e.target.value as Priority,
                          }))
                        }
                        className="w-full p-2 border rounded-md"
                      >
                        {PRIORITY_LEVELS.map(priority => (
                          <option key={priority.value} value={priority.value}>
                            {priority.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="description">Description</Label>
                    <Input
                      id="description"
                      value={currentGoal.description}
                      onChange={e =>
                        setCurrentGoal(prev => ({
                          ...prev,
                          description: e.target.value,
                        }))
                      }
                      placeholder="Enter goal description..."
                    />
                  </div>

                  <div>
                    <Label htmlFor="targetBehavior">Target Behavior</Label>
                    <Textarea
                      id="targetBehavior"
                      value={currentGoal.targetBehavior}
                      onChange={e =>
                        setCurrentGoal(prev => ({
                          ...prev,
                          targetBehavior: e.target.value,
                        }))
                      }
                      placeholder="Describe the specific behavior to target..."
                      rows={3}
                    />
                  </div>

                  <div>
                    <Label htmlFor="measurableOutcome">
                      Measurable Outcome
                    </Label>
                    <Textarea
                      id="measurableOutcome"
                      value={currentGoal.measurableOutcome}
                      onChange={e =>
                        setCurrentGoal(prev => ({
                          ...prev,
                          measurableOutcome: e.target.value,
                        }))
                      }
                      placeholder="Define how success will be measured..."
                      rows={3}
                    />
                  </div>

                  <div>
                    <Label htmlFor="timeframe">Timeframe</Label>
                    <Input
                      id="timeframe"
                      value={currentGoal.timeframe}
                      onChange={e =>
                        setCurrentGoal(prev => ({
                          ...prev,
                          timeframe: e.target.value,
                        }))
                      }
                      placeholder="e.g., 12 weeks, 6 months..."
                    />
                  </div>

                  <div className="flex gap-2">
                    {editingGoal !== null ? (
                      <>
                        <Button
                          onClick={handleUpdateGoal}
                          className="flex items-center gap-2"
                        >
                          <CheckCircle2 className="w-4 h-4" />
                          Update Goal
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => {
                            setEditingGoal(null)
                            setCurrentGoal({
                              category: GoalCategory.ARTICULATION,
                              description: '',
                              targetBehavior: '',
                              measurableOutcome: '',
                              timeframe: '',
                              priority: Priority.MEDIUM,
                            })
                          }}
                        >
                          Cancel
                        </Button>
                      </>
                    ) : (
                      <Button
                        onClick={handleAddGoal}
                        className="flex items-center gap-2"
                        disabled={
                          !currentGoal.description ||
                          !currentGoal.targetBehavior ||
                          !currentGoal.measurableOutcome
                        }
                      >
                        <Plus className="w-4 h-4" />
                        Add Goal
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="schedule" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Schedule & Duration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <Label htmlFor="duration">Plan Duration (weeks)</Label>
                  <Input
                    id="duration"
                    type="number"
                    min="1"
                    max="52"
                    value={duration}
                    onChange={e => setDuration(Number(e.target.value))}
                  />
                </div>
                <div>
                  <Label htmlFor="frequency">Sessions per Week</Label>
                  <Input
                    id="frequency"
                    type="number"
                    min="1"
                    max="5"
                    value={frequency}
                    onChange={e => setFrequency(Number(e.target.value))}
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-muted rounded-lg">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {totalSessions}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Total Sessions
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {estimatedWeeks}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Estimated Weeks
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {Math.round(totalSessions * 30)}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    Est. Minutes
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Back to Screening
        </Button>
        <Button
          onClick={handleCreatePlan}
          disabled={loading || goals.length === 0}
          className="flex items-center gap-2"
        >
          {loading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
          ) : (
            <CheckCircle2 className="w-4 h-4" />
          )}
          Create Therapy Plan
        </Button>
      </div>
    </div>
  )
}
