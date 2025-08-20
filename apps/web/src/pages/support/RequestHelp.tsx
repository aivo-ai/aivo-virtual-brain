/**
 * RequestHelp Component
 * Guardian interface for requesting Just-In-Time support sessions
 */

import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  AlertTitle,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Grid,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Tooltip,
} from '@mui/material'
import {
  Help as HelpIcon,
  Security as SecurityIcon,
  Timer as TimerIcon,
  Visibility as VisibilityIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Info as InfoIcon,
} from '@mui/icons-material'

interface SupportRequest {
  learner_id: string
  reason: string
  description?: string
  urgency: 'low' | 'normal' | 'high' | 'emergency'
  max_duration_minutes: number
  allowed_data_types: string[]
}

interface SupportSession {
  id: string
  learner_id: string
  guardian_id: string
  support_agent_id?: string
  status:
    | 'requested'
    | 'pending_approval'
    | 'approved'
    | 'denied'
    | 'active'
    | 'completed'
    | 'expired'
  reason: string
  description?: string
  urgency: string
  requested_at: string
  approved_at?: string
  denied_at?: string
  session_start?: string
  session_end?: string
  max_duration_minutes: number
  allowed_data_types: string[]
  approval_reason?: string
}

interface Learner {
  id: string
  name: string
  email: string
  grade: string
}

const URGENCY_COLORS = {
  low: 'info',
  normal: 'primary',
  high: 'warning',
  emergency: 'error',
} as const

const DATA_TYPE_OPTIONS = [
  {
    value: 'account_info',
    label: 'Account Information',
    description: 'Login credentials, profile data',
  },
  {
    value: 'learning_progress',
    label: 'Learning Progress',
    description: 'Lesson completion, scores',
  },
  {
    value: 'assignments',
    label: 'Assignments',
    description: 'Homework, projects, submissions',
  },
  {
    value: 'assessments',
    label: 'Assessments',
    description: 'Tests, quizzes, grades',
  },
  {
    value: 'behavioral_data',
    label: 'Behavioral Data',
    description: 'Learning patterns, engagement',
  },
  {
    value: 'communication',
    label: 'Communication',
    description: 'Messages, notifications',
  },
]

const RequestHelp: React.FC = () => {
  const [learners, setLearners] = useState<Learner[]>([])
  const [sessions, setSessions] = useState<SupportSession[]>([])
  const [loading, setLoading] = useState(false)
  const [showRequestForm, setShowRequestForm] = useState(false)
  const [showConsentDialog, setShowConsentDialog] = useState(false)
  const [pendingRequest, setPendingRequest] = useState<SupportRequest | null>(
    null
  )

  // Form state
  const [selectedLearner, setSelectedLearner] = useState('')
  const [reason, setReason] = useState('')
  const [description, setDescription] = useState('')
  const [urgency, setUrgency] = useState<
    'low' | 'normal' | 'high' | 'emergency'
  >('normal')
  const [maxDuration, setMaxDuration] = useState(60)
  const [allowedDataTypes, setAllowedDataTypes] = useState<string[]>([
    'account_info',
  ])
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Mock data for development
  useEffect(() => {
    // In a real implementation, this would fetch from the API
    setLearners([
      {
        id: '1',
        name: 'Emma Johnson',
        email: 'emma.j@student.aivo.com',
        grade: '5th Grade',
      },
      {
        id: '2',
        name: 'Liam Smith',
        email: 'liam.s@student.aivo.com',
        grade: '7th Grade',
      },
    ])

    // Load existing sessions
    loadSessions()
  }, [])

  const loadSessions = async () => {
    try {
      setLoading(true)
      // Mock API call - replace with actual API
      await new Promise(resolve => setTimeout(resolve, 1000))

      setSessions([
        {
          id: 'session-1',
          learner_id: '1',
          guardian_id: 'guardian-1',
          status: 'pending_approval',
          reason: 'Login issues preventing homework submission',
          description: 'Student cannot access learning platform',
          urgency: 'high',
          requested_at: new Date().toISOString(),
          max_duration_minutes: 30,
          allowed_data_types: ['account_info', 'assignments'],
        },
      ])
    } catch (err) {
      setError('Failed to load support sessions')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitRequest = async () => {
    if (!selectedLearner || !reason.trim()) {
      setError(
        'Please select a learner and provide a reason for the support request'
      )
      return
    }

    const request: SupportRequest = {
      learner_id: selectedLearner,
      reason: reason.trim(),
      description: description.trim() || undefined,
      urgency,
      max_duration_minutes: maxDuration,
      allowed_data_types: allowedDataTypes,
    }

    setPendingRequest(request)
    setShowConsentDialog(true)
  }

  const handleConsentGiven = async () => {
    if (!pendingRequest) return

    try {
      setLoading(true)
      setError(null)

      // API call to create support session
      const response = await fetch('/api/v1/support-sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify(pendingRequest),
      })

      if (!response.ok) {
        throw new Error('Failed to create support session')
      }

      const newSession = await response.json()
      setSessions(prev => [newSession, ...prev])

      setSuccess(
        'Support session requested successfully. You will receive a notification when it requires approval.'
      )
      setShowRequestForm(false)
      setShowConsentDialog(false)
      resetForm()
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to create support session'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleApproveSession = async (
    sessionId: string,
    approved: boolean,
    reason?: string
  ) => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(
        `/api/v1/support-sessions/${sessionId}/approve`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
          },
          body: JSON.stringify({
            approved,
            reason,
          }),
        }
      )

      if (!response.ok) {
        throw new Error('Failed to process approval')
      }

      const updatedSession = await response.json()
      setSessions(prev =>
        prev.map(s => (s.id === sessionId ? updatedSession : s))
      )

      setSuccess(
        `Support session ${approved ? 'approved' : 'denied'} successfully`
      )
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to process approval'
      )
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setSelectedLearner('')
    setReason('')
    setDescription('')
    setUrgency('normal')
    setMaxDuration(60)
    setAllowedDataTypes(['account_info'])
    setPendingRequest(null)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'success'
      case 'denied':
        return 'error'
      case 'active':
        return 'info'
      case 'completed':
        return 'success'
      case 'expired':
        return 'warning'
      default:
        return 'default'
    }
  }

  const formatDateTime = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          gutterBottom
          sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
        >
          <HelpIcon />
          Support Request Center
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Request Just-In-Time support sessions for your learners with secure,
          time-limited access
        </Typography>
      </Box>

      {/* Alerts */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          <AlertTitle>Error</AlertTitle>
          {error}
        </Alert>
      )}

      {success && (
        <Alert
          severity="success"
          sx={{ mb: 3 }}
          onClose={() => setSuccess(null)}
        >
          <AlertTitle>Success</AlertTitle>
          {success}
        </Alert>
      )}

      {/* Security Notice */}
      <Alert severity="info" sx={{ mb: 4 }}>
        <AlertTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SecurityIcon fontSize="small" />
          Privacy & Security Notice
        </AlertTitle>
        Support sessions are time-limited, read-only by default, and fully
        audited. All actions performed during sessions are logged for compliance
        and security.
      </Alert>

      {/* Action Buttons */}
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item>
          <Button
            variant="contained"
            startIcon={<HelpIcon />}
            onClick={() => setShowRequestForm(true)}
          >
            Request New Support Session
          </Button>
        </Grid>
        <Grid item>
          <Button variant="outlined" onClick={loadSessions} disabled={loading}>
            Refresh Sessions
          </Button>
        </Grid>
      </Grid>

      {/* Request Form Dialog */}
      <Dialog
        open={showRequestForm}
        onClose={() => setShowRequestForm(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Request Support Session</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Learner Selection */}
            <FormControl fullWidth required>
              <InputLabel>Select Learner</InputLabel>
              <Select
                value={selectedLearner}
                onChange={e => setSelectedLearner(e.target.value)}
                label="Select Learner"
              >
                {learners.map(learner => (
                  <MenuItem key={learner.id} value={learner.id}>
                    {learner.name} ({learner.grade}) - {learner.email}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Reason */}
            <TextField
              label="Reason for Support"
              value={reason}
              onChange={e => setReason(e.target.value)}
              required
              fullWidth
              placeholder="e.g., Student unable to access assignments"
              helperText="Brief description of the issue requiring support"
            />

            {/* Description */}
            <TextField
              label="Detailed Description"
              value={description}
              onChange={e => setDescription(e.target.value)}
              multiline
              rows={3}
              fullWidth
              placeholder="Provide additional context about the issue..."
              helperText="Optional: Additional details to help the support agent"
            />

            {/* Urgency */}
            <FormControl fullWidth>
              <InputLabel>Urgency Level</InputLabel>
              <Select
                value={urgency}
                onChange={e => setUrgency(e.target.value as typeof urgency)}
                label="Urgency Level"
              >
                <MenuItem value="low">Low - Can wait 24+ hours</MenuItem>
                <MenuItem value="normal">
                  Normal - Within business hours
                </MenuItem>
                <MenuItem value="high">
                  High - Same day response needed
                </MenuItem>
                <MenuItem value="emergency">
                  Emergency - Immediate attention
                </MenuItem>
              </Select>
            </FormControl>

            {/* Session Duration */}
            <TextField
              label="Maximum Session Duration (minutes)"
              type="number"
              value={maxDuration}
              onChange={e => setMaxDuration(parseInt(e.target.value) || 60)}
              InputProps={{ inputProps: { min: 5, max: 240 } }}
              fullWidth
              helperText="Sessions automatically expire after this duration"
            />

            {/* Data Access Permissions */}
            <FormControl fullWidth>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Allowed Data Types
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {DATA_TYPE_OPTIONS.map(option => (
                  <Tooltip key={option.value} title={option.description}>
                    <Chip
                      label={option.label}
                      onClick={() => {
                        if (allowedDataTypes.includes(option.value)) {
                          setAllowedDataTypes(prev =>
                            prev.filter(type => type !== option.value)
                          )
                        } else {
                          setAllowedDataTypes(prev => [...prev, option.value])
                        }
                      }}
                      color={
                        allowedDataTypes.includes(option.value)
                          ? 'primary'
                          : 'default'
                      }
                      variant={
                        allowedDataTypes.includes(option.value)
                          ? 'filled'
                          : 'outlined'
                      }
                    />
                  </Tooltip>
                ))}
              </Box>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ mt: 1 }}
              >
                Select which types of data the support agent may access during
                the session
              </Typography>
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowRequestForm(false)}>Cancel</Button>
          <Button
            onClick={handleSubmitRequest}
            variant="contained"
            disabled={loading}
          >
            Request Support
          </Button>
        </DialogActions>
      </Dialog>

      {/* Consent Dialog */}
      <Dialog
        open={showConsentDialog}
        onClose={() => setShowConsentDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <SecurityIcon />
          Consent for Support Session
        </DialogTitle>
        <DialogContent>
          <Typography paragraph>
            You are about to authorize a Just-In-Time support session with the
            following details:
          </Typography>

          {pendingRequest && (
            <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
              <Typography variant="subtitle2">Session Details:</Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                <strong>Learner:</strong>{' '}
                {learners.find(l => l.id === pendingRequest.learner_id)?.name}
              </Typography>
              <Typography variant="body2">
                <strong>Reason:</strong> {pendingRequest.reason}
              </Typography>
              <Typography variant="body2">
                <strong>Urgency:</strong>{' '}
                <Chip
                  size="small"
                  label={pendingRequest.urgency}
                  color={URGENCY_COLORS[pendingRequest.urgency]}
                />
              </Typography>
              <Typography variant="body2">
                <strong>Max Duration:</strong>{' '}
                {pendingRequest.max_duration_minutes} minutes
              </Typography>
              <Typography variant="body2">
                <strong>Data Access:</strong>{' '}
                {pendingRequest.allowed_data_types.join(', ')}
              </Typography>
            </Paper>
          )}

          <Alert severity="info" sx={{ mt: 2 }}>
            <AlertTitle>Privacy & Security</AlertTitle>
            <ul style={{ margin: 0, paddingLeft: '20px' }}>
              <li>Support session will be read-only by default</li>
              <li>All actions are logged and audited</li>
              <li>
                Session will automatically expire after the specified duration
              </li>
              <li>You can end the session at any time</li>
              <li>Support agent can only access the specified data types</li>
            </ul>
          </Alert>

          <Typography sx={{ mt: 2, fontWeight: 'bold' }}>
            Do you consent to this support session?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowConsentDialog(false)}>Cancel</Button>
          <Button
            onClick={handleConsentGiven}
            variant="contained"
            disabled={loading}
            startIcon={
              loading ? <CircularProgress size={16} /> : <CheckCircleIcon />
            }
          >
            I Consent
          </Button>
        </DialogActions>
      </Dialog>

      {/* Existing Sessions */}
      <Card>
        <CardContent>
          <Typography
            variant="h6"
            gutterBottom
            sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
          >
            <TimerIcon />
            Support Sessions
          </Typography>

          {loading && sessions.length === 0 ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : sessions.length === 0 ? (
            <Typography
              color="text.secondary"
              sx={{ textAlign: 'center', p: 3 }}
            >
              No support sessions found. Request a new session to get started.
            </Typography>
          ) : (
            <List>
              {sessions.map(session => {
                const learner = learners.find(l => l.id === session.learner_id)

                return (
                  <ListItem key={session.id} divider>
                    <ListItemText
                      primary={
                        <Box
                          sx={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1,
                            mb: 1,
                          }}
                        >
                          <Typography variant="subtitle1">
                            {learner?.name} - {session.reason}
                          </Typography>
                          <Chip
                            size="small"
                            label={session.status}
                            color={getStatusColor(session.status)}
                          />
                          <Chip
                            size="small"
                            label={session.urgency}
                            color={
                              URGENCY_COLORS[
                                session.urgency as keyof typeof URGENCY_COLORS
                              ]
                            }
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            Requested: {formatDateTime(session.requested_at)}
                          </Typography>
                          {session.description && (
                            <Typography variant="body2" color="text.secondary">
                              {session.description}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary">
                            Duration: {session.max_duration_minutes}min | Data:{' '}
                            {session.allowed_data_types.join(', ')}
                          </Typography>
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      {session.status === 'pending_approval' && (
                        <Box sx={{ display: 'flex', gap: 1 }}>
                          <Button
                            size="small"
                            color="success"
                            variant="contained"
                            startIcon={<CheckCircleIcon />}
                            onClick={() =>
                              handleApproveSession(
                                session.id,
                                true,
                                'Approved for support'
                              )
                            }
                            disabled={loading}
                          >
                            Approve
                          </Button>
                          <Button
                            size="small"
                            color="error"
                            variant="outlined"
                            startIcon={<CancelIcon />}
                            onClick={() =>
                              handleApproveSession(
                                session.id,
                                false,
                                'Support not needed'
                              )
                            }
                            disabled={loading}
                          >
                            Deny
                          </Button>
                        </Box>
                      )}
                      {session.status === 'active' && (
                        <Tooltip title="Session is currently active">
                          <IconButton color="info">
                            <VisibilityIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                    </ListItemSecondaryAction>
                  </ListItem>
                )
              })}
            </List>
          )}
        </CardContent>
      </Card>
    </Box>
  )
}

export default RequestHelp
