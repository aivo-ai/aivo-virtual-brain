/**
 * ResetDialog Component (S5-08)
 *
 * Dialog for confirming adapter reset requests with clear explanation
 * of what will happen and approval workflow information.
 */

import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Typography,
  Alert,
  Box,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Chip,
} from '@mui/material'
import {
  Warning as WarningIcon,
  Refresh as ResetIcon,
  Psychology as BrainIcon,
  Timeline as ProgressIcon,
  CheckCircle as CheckIcon,
  School as SchoolIcon,
  Shield as GuardianIcon,
} from '@mui/icons-material'

interface ResetDialogProps {
  open: boolean
  onClose: () => void
  subject: string | null
  subjectDisplayName: string
  onConfirm: (subject: string, reason: string) => Promise<void>
}

export const ResetDialog: React.FC<ResetDialogProps> = ({
  open,
  onClose,
  subject,
  subjectDisplayName,
  onConfirm,
}) => {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [reasonError, setReasonError] = useState('')

  const handleSubmit = async () => {
    if (!subject) return

    // Validation
    if (!reason.trim()) {
      setReasonError('Please provide a reason for the reset')
      return
    }

    if (reason.trim().length < 10) {
      setReasonError(
        'Please provide a more detailed reason (at least 10 characters)'
      )
      return
    }

    try {
      setLoading(true)
      setReasonError('')

      await onConfirm(subject, reason.trim())

      // Close dialog and reset form
      handleClose()
    } catch (error) {
      console.error('Reset confirmation failed:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    setReason('')
    setReasonError('')
    setLoading(false)
    onClose()
  }

  if (!subject) return null

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <ResetIcon color="warning" />
          <Typography variant="h6">Reset {subjectDisplayName} Brain</Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Alert severity="warning" sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Important: This will completely reset your AI brain for{' '}
            {subjectDisplayName}
          </Typography>
          <Typography variant="body2">
            This action cannot be undone. Your brain will start learning from
            scratch.
          </Typography>
        </Alert>

        <Typography variant="h6" gutterBottom sx={{ mt: 3, mb: 2 }}>
          What will happen during the reset:
        </Typography>

        <List dense>
          <ListItem>
            <ListItemIcon>
              <BrainIcon color="primary" />
            </ListItemIcon>
            <ListItemText
              primary="Reset AI Adaptation"
              secondary="Your personalized learning model will be reset to the base foundation model"
            />
          </ListItem>

          <ListItem>
            <ListItemIcon>
              <ProgressIcon color="info" />
            </ListItemIcon>
            <ListItemText
              primary="Replay Learning History"
              secondary="Your past learning activities will be replayed to rebuild the model"
            />
          </ListItem>

          <ListItem>
            <ListItemIcon>
              <CheckIcon color="success" />
            </ListItemIcon>
            <ListItemText
              primary="Fresh Start"
              secondary="You'll get a clean, optimized AI brain based on your complete learning history"
            />
          </ListItem>
        </List>

        <Divider sx={{ my: 3 }} />

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Approval Process:
          </Typography>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <GuardianIcon color="primary" />
            <Typography variant="body1">
              Guardian approval is required for brain resets
            </Typography>
          </Box>

          <Alert severity="info">
            <Typography variant="body2">
              Your guardian will receive a notification to approve this reset
              request. The reset will begin automatically once approved.
            </Typography>
          </Alert>
        </Box>

        <TextField
          fullWidth
          multiline
          rows={4}
          label="Reason for Reset"
          placeholder="Please explain why you want to reset this brain (e.g., 'Having trouble with concepts', 'Want to start fresh', 'Brain seems confused')"
          value={reason}
          onChange={e => {
            setReason(e.target.value)
            if (reasonError) setReasonError('')
          }}
          error={!!reasonError}
          helperText={
            reasonError ||
            'This will help your guardian understand why the reset is needed'
          }
          required
          sx={{ mt: 2 }}
        />

        <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Expected Timeline:</strong> Approval process typically takes
            a few hours. Once approved, the reset process takes 5-10 minutes to
            complete.
          </Typography>
        </Box>
      </DialogContent>

      <DialogActions sx={{ p: 3, pt: 1 }}>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color="warning"
          onClick={handleSubmit}
          disabled={loading || !reason.trim()}
          startIcon={<ResetIcon />}
        >
          {loading ? 'Submitting...' : 'Request Reset'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
