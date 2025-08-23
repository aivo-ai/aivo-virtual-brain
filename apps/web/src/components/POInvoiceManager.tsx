import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Grid,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Fab,
  IconButton,
  Tooltip,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material'
import { styled } from '@mui/material/styles'
import {
  Add,
  Download,
  Email,
  Payment,
  Receipt,
  Warning,
  CheckCircle,
  Schedule,
  Business,
  AttachMoney,
  Description,
  DateRange,
  Print,
  Refresh,
} from '@mui/icons-material'
import { format, parseISO, addDays } from 'date-fns'

const StyledCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(3),
  '& .MuiCardHeader-root': {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
  },
}))

const StatusChip = styled(Chip)<{ status: string }>(({ theme, status }) => ({
  fontWeight: 'bold',
  ...(status === 'paid' && {
    backgroundColor: theme.palette.success.main,
    color: theme.palette.success.contrastText,
  }),
  ...(status === 'overdue' && {
    backgroundColor: theme.palette.error.main,
    color: theme.palette.error.contrastText,
  }),
  ...(status === 'pending' && {
    backgroundColor: theme.palette.warning.main,
    color: theme.palette.warning.contrastText,
  }),
  ...(status === 'draft' && {
    backgroundColor: theme.palette.grey[500],
    color: theme.palette.grey[50],
  }),
}))

interface POInvoice {
  invoice_id: string
  invoice_number: string
  tenant_id: string
  po_number?: string
  status: 'draft' | 'sent' | 'pending' | 'paid' | 'overdue' | 'cancelled'
  issue_date: string
  due_date: string
  payment_terms: string
  subtotal: number
  tax_total: number
  total: number
  total_payments: number
  remaining_balance: number
  billing_contact: {
    name: string
    email: string
    phone?: string
    title?: string
  }
  billing_address: {
    line1: string
    line2?: string
    city: string
    state?: string
    postal_code: string
    country: string
  }
  line_items: Array<{
    description: string
    quantity: number
    unit_price: number
    total_price: number
    tax_rate?: number
    tax_amount?: number
  }>
  notes?: string
  created_at: string
  updated_at: string
}

interface Payment {
  payment_id: string
  invoice_id: string
  payment_amount: number
  payment_date: string
  payment_method: string
  reference_number?: string
  notes?: string
}

const POInvoiceManager: React.FC = () => {
  const [invoices, setInvoices] = useState<POInvoice[]>([])
  const [selectedInvoice, setSelectedInvoice] = useState<POInvoice | null>(null)
  const [payments, setPayments] = useState<Payment[]>([])
  const [loading, setLoading] = useState(false)
  const [showPaymentDialog, setShowPaymentDialog] = useState(false)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [filters, setFilters] = useState({
    status: '',
    tenant_id: '',
    page: 1,
    page_size: 25,
  })

  const [newPayment, setNewPayment] = useState({
    payment_amount: '',
    payment_date: format(new Date(), 'yyyy-MM-dd'),
    payment_method: 'check',
    reference_number: '',
    notes: '',
  })

  const [newInvoice, setNewInvoice] = useState({
    tenant_id: '',
    po_number: '',
    billing_contact: {
      name: '',
      email: '',
      phone: '',
      title: '',
    },
    billing_address: {
      line1: '',
      line2: '',
      city: '',
      state: '',
      postal_code: '',
      country: 'US',
    },
    line_items: [
      {
        description: '',
        quantity: 1,
        unit_price: 0,
        total_price: 0,
      },
    ],
    payment_terms: 'net_30',
    notes: '',
  })

  useEffect(() => {
    loadInvoices()
  }, [filters])

  const loadInvoices = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.append(key, value.toString())
      })

      const response = await fetch(`/api/po/invoices?${params}`)
      if (response.ok) {
        const data = await response.json()
        setInvoices(data.invoices)
      }
    } catch (error) {
      console.error('Failed to load invoices:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadInvoiceDetails = async (invoiceId: string) => {
    try {
      const response = await fetch(`/api/po/invoices/${invoiceId}`)
      if (response.ok) {
        const invoice = await response.json()
        setSelectedInvoice(invoice)

        // Load payments for this invoice
        const paymentsResponse = await fetch(
          `/api/po/invoices/${invoiceId}/payments`
        )
        if (paymentsResponse.ok) {
          const paymentsData = await paymentsResponse.json()
          setPayments(paymentsData.payments || [])
        }
      }
    } catch (error) {
      console.error('Failed to load invoice details:', error)
    }
  }

  const createInvoice = async () => {
    try {
      const response = await fetch('/api/po/invoices', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newInvoice),
      })

      if (response.ok) {
        const invoice = await response.json()
        setInvoices(prev => [invoice, ...prev])
        setShowCreateDialog(false)
        resetNewInvoice()
        alert('Invoice created successfully')
      } else {
        alert('Failed to create invoice')
      }
    } catch (error) {
      console.error('Failed to create invoice:', error)
      alert('Failed to create invoice')
    }
  }

  const recordPayment = async () => {
    if (!selectedInvoice) return

    try {
      const response = await fetch(
        `/api/po/invoices/${selectedInvoice.invoice_id}/payment`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...newPayment,
            payment_amount: parseFloat(newPayment.payment_amount),
            invoice_id: selectedInvoice.invoice_id,
          }),
        }
      )

      if (response.ok) {
        const result = await response.json()
        setSelectedInvoice(prev =>
          prev
            ? {
                ...prev,
                total_payments: result.total_payments,
                remaining_balance: result.remaining_balance,
                status: result.status,
              }
            : null
        )

        loadInvoiceDetails(selectedInvoice.invoice_id)
        setShowPaymentDialog(false)
        resetNewPayment()
        alert('Payment recorded successfully')
      } else {
        alert('Failed to record payment')
      }
    } catch (error) {
      console.error('Failed to record payment:', error)
      alert('Failed to record payment')
    }
  }

  const sendDunningReminder = async (
    invoiceId: string,
    reminderType: string
  ) => {
    try {
      const response = await fetch(`/api/po/invoices/${invoiceId}/dunning`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          invoice_id: invoiceId,
          reminder_type: reminderType,
        }),
      })

      if (response.ok) {
        alert('Dunning reminder sent successfully')
      } else {
        alert('Failed to send reminder')
      }
    } catch (error) {
      console.error('Failed to send reminder:', error)
      alert('Failed to send reminder')
    }
  }

  const downloadInvoicePDF = async (invoiceId: string) => {
    try {
      const response = await fetch(`/api/po/invoices/${invoiceId}/pdf`)
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `invoice-${invoiceId}.pdf`
        a.click()
        window.URL.revokeObjectURL(url)
      }
    } catch (error) {
      console.error('Failed to download PDF:', error)
    }
  }

  const exportToCSV = async () => {
    try {
      const response = await fetch('/api/po/export/csv')
      if (response.ok) {
        const data = await response.json()
        const blob = new Blob([data.csv_data], { type: 'text/csv' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `invoices-export-${format(new Date(), 'yyyy-MM-dd')}.csv`
        a.click()
        window.URL.revokeObjectURL(url)
      }
    } catch (error) {
      console.error('Failed to export CSV:', error)
    }
  }

  const resetNewInvoice = () => {
    setNewInvoice({
      tenant_id: '',
      po_number: '',
      billing_contact: {
        name: '',
        email: '',
        phone: '',
        title: '',
      },
      billing_address: {
        line1: '',
        line2: '',
        city: '',
        state: '',
        postal_code: '',
        country: 'US',
      },
      line_items: [
        {
          description: '',
          quantity: 1,
          unit_price: 0,
          total_price: 0,
        },
      ],
      payment_terms: 'net_30',
      notes: '',
    })
  }

  const resetNewPayment = () => {
    setNewPayment({
      payment_amount: '',
      payment_date: format(new Date(), 'yyyy-MM-dd'),
      payment_method: 'check',
      reference_number: '',
      notes: '',
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
        return <CheckCircle />
      case 'overdue':
        return <Warning />
      case 'pending':
        return <Schedule />
      default:
        return <Description />
    }
  }

  const getDaysOverdue = (dueDate: string) => {
    const due = parseISO(dueDate)
    const today = new Date()
    const diffTime = today.getTime() - due.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays > 0 ? diffDays : 0
  }

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', p: 3 }}>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'between',
          alignItems: 'center',
          mb: 3,
        }}
      >
        <Typography variant="h4">PO Invoice Management</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={exportToCSV}
          >
            Export CSV
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setShowCreateDialog(true)}
          >
            Create Invoice
          </Button>
        </Box>
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={filters.status}
                  onChange={e =>
                    setFilters(prev => ({ ...prev, status: e.target.value }))
                  }
                  label="Status"
                >
                  <MenuItem value="">All</MenuItem>
                  <MenuItem value="draft">Draft</MenuItem>
                  <MenuItem value="sent">Sent</MenuItem>
                  <MenuItem value="pending">Pending</MenuItem>
                  <MenuItem value="paid">Paid</MenuItem>
                  <MenuItem value="overdue">Overdue</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Tenant ID"
                value={filters.tenant_id}
                onChange={e =>
                  setFilters(prev => ({ ...prev, tenant_id: e.target.value }))
                }
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={loadInvoices}
                disabled={loading}
              >
                Refresh
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Invoice List */}
      <StyledCard>
        <CardHeader title="Invoices" />
        <CardContent sx={{ p: 0 }}>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Invoice #</TableCell>
                  <TableCell>PO Number</TableCell>
                  <TableCell>Tenant</TableCell>
                  <TableCell>Amount</TableCell>
                  <TableCell>Due Date</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {invoices.map(invoice => (
                  <TableRow key={invoice.invoice_id}>
                    <TableCell>
                      <Button
                        variant="text"
                        onClick={() => loadInvoiceDetails(invoice.invoice_id)}
                      >
                        {invoice.invoice_number}
                      </Button>
                    </TableCell>
                    <TableCell>{invoice.po_number || '-'}</TableCell>
                    <TableCell>{invoice.tenant_id}</TableCell>
                    <TableCell>${invoice.total.toFixed(2)}</TableCell>
                    <TableCell>
                      {format(parseISO(invoice.due_date), 'MMM dd, yyyy')}
                      {invoice.status === 'overdue' && (
                        <Chip
                          size="small"
                          label={`${getDaysOverdue(invoice.due_date)} days overdue`}
                          color="error"
                          sx={{ ml: 1 }}
                        />
                      )}
                    </TableCell>
                    <TableCell>
                      <StatusChip
                        status={invoice.status}
                        label={invoice.status.toUpperCase()}
                        icon={getStatusIcon(invoice.status)}
                      />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <Tooltip title="Download PDF">
                          <IconButton
                            size="small"
                            onClick={() =>
                              downloadInvoicePDF(invoice.invoice_id)
                            }
                          >
                            <Download />
                          </IconButton>
                        </Tooltip>
                        {invoice.status === 'overdue' && (
                          <Tooltip title="Send Reminder">
                            <IconButton
                              size="small"
                              onClick={() =>
                                sendDunningReminder(
                                  invoice.invoice_id,
                                  'gentle'
                                )
                              }
                            >
                              <Email />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </StyledCard>

      {/* Invoice Details Dialog */}
      <Dialog
        open={!!selectedInvoice}
        onClose={() => setSelectedInvoice(null)}
        maxWidth="lg"
        fullWidth
      >
        {selectedInvoice && (
          <>
            <DialogTitle>
              Invoice {selectedInvoice.invoice_number}
              <StatusChip
                status={selectedInvoice.status}
                label={selectedInvoice.status.toUpperCase()}
                sx={{ ml: 2 }}
              />
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    Billing Information
                  </Typography>
                  <Typography>
                    <strong>Contact:</strong>{' '}
                    {selectedInvoice.billing_contact.name}
                  </Typography>
                  <Typography>
                    <strong>Email:</strong>{' '}
                    {selectedInvoice.billing_contact.email}
                  </Typography>
                  {selectedInvoice.billing_contact.phone && (
                    <Typography>
                      <strong>Phone:</strong>{' '}
                      {selectedInvoice.billing_contact.phone}
                    </Typography>
                  )}
                  <Typography>
                    <strong>Address:</strong>
                  </Typography>
                  <Typography variant="body2">
                    {selectedInvoice.billing_address.line1}
                    <br />
                    {selectedInvoice.billing_address.line2 && (
                      <>
                        {selectedInvoice.billing_address.line2}
                        <br />
                      </>
                    )}
                    {selectedInvoice.billing_address.city},{' '}
                    {selectedInvoice.billing_address.state}{' '}
                    {selectedInvoice.billing_address.postal_code}
                    <br />
                    {selectedInvoice.billing_address.country}
                  </Typography>
                </Grid>

                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom>
                    Invoice Details
                  </Typography>
                  <Typography>
                    <strong>Issue Date:</strong>{' '}
                    {format(
                      parseISO(selectedInvoice.issue_date),
                      'MMM dd, yyyy'
                    )}
                  </Typography>
                  <Typography>
                    <strong>Due Date:</strong>{' '}
                    {format(parseISO(selectedInvoice.due_date), 'MMM dd, yyyy')}
                  </Typography>
                  <Typography>
                    <strong>Payment Terms:</strong>{' '}
                    {selectedInvoice.payment_terms
                      .replace('_', ' ')
                      .toUpperCase()}
                  </Typography>
                  {selectedInvoice.po_number && (
                    <Typography>
                      <strong>PO Number:</strong> {selectedInvoice.po_number}
                    </Typography>
                  )}

                  <Box sx={{ mt: 2 }}>
                    <Typography>
                      <strong>Subtotal:</strong> $
                      {selectedInvoice.subtotal.toFixed(2)}
                    </Typography>
                    <Typography>
                      <strong>Tax:</strong> $
                      {selectedInvoice.tax_total.toFixed(2)}
                    </Typography>
                    <Typography variant="h6">
                      <strong>Total:</strong> $
                      {selectedInvoice.total.toFixed(2)}
                    </Typography>
                    <Typography>
                      <strong>Paid:</strong> $
                      {selectedInvoice.total_payments.toFixed(2)}
                    </Typography>
                    <Typography
                      color={
                        selectedInvoice.remaining_balance > 0
                          ? 'error'
                          : 'success'
                      }
                    >
                      <strong>Balance:</strong> $
                      {selectedInvoice.remaining_balance.toFixed(2)}
                    </Typography>
                  </Box>
                </Grid>

                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Line Items
                  </Typography>
                  <TableContainer component={Paper}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Description</TableCell>
                          <TableCell align="right">Quantity</TableCell>
                          <TableCell align="right">Unit Price</TableCell>
                          <TableCell align="right">Total</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {selectedInvoice.line_items.map((item, index) => (
                          <TableRow key={index}>
                            <TableCell>{item.description}</TableCell>
                            <TableCell align="right">{item.quantity}</TableCell>
                            <TableCell align="right">
                              ${item.unit_price.toFixed(2)}
                            </TableCell>
                            <TableCell align="right">
                              ${item.total_price.toFixed(2)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Grid>

                {payments.length > 0 && (
                  <Grid item xs={12}>
                    <Typography variant="h6" gutterBottom>
                      Payment History
                    </Typography>
                    <List>
                      {payments.map(payment => (
                        <ListItem key={payment.payment_id}>
                          <ListItemIcon>
                            <Receipt />
                          </ListItemIcon>
                          <ListItemText
                            primary={`$${payment.payment_amount.toFixed(2)} - ${payment.payment_method}`}
                            secondary={`${format(parseISO(payment.payment_date), 'MMM dd, yyyy')} ${payment.reference_number ? `(${payment.reference_number})` : ''}`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Grid>
                )}
              </Grid>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setSelectedInvoice(null)}>Close</Button>
              <Button
                startIcon={<Download />}
                onClick={() => downloadInvoicePDF(selectedInvoice.invoice_id)}
              >
                Download PDF
              </Button>
              {selectedInvoice.remaining_balance > 0 && (
                <Button
                  variant="contained"
                  startIcon={<Payment />}
                  onClick={() => setShowPaymentDialog(true)}
                >
                  Record Payment
                </Button>
              )}
            </DialogActions>
          </>
        )}
      </Dialog>

      {/* Payment Dialog */}
      <Dialog
        open={showPaymentDialog}
        onClose={() => setShowPaymentDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Record Payment</DialogTitle>
        <DialogContent>
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                required
                label="Payment Amount"
                type="number"
                value={newPayment.payment_amount}
                onChange={e =>
                  setNewPayment(prev => ({
                    ...prev,
                    payment_amount: e.target.value,
                  }))
                }
                InputProps={{ startAdornment: '$' }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                required
                label="Payment Date"
                type="date"
                value={newPayment.payment_date}
                onChange={e =>
                  setNewPayment(prev => ({
                    ...prev,
                    payment_date: e.target.value,
                  }))
                }
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth required>
                <InputLabel>Payment Method</InputLabel>
                <Select
                  value={newPayment.payment_method}
                  onChange={e =>
                    setNewPayment(prev => ({
                      ...prev,
                      payment_method: e.target.value,
                    }))
                  }
                  label="Payment Method"
                >
                  <MenuItem value="check">Check</MenuItem>
                  <MenuItem value="wire_transfer">Wire Transfer</MenuItem>
                  <MenuItem value="ach">ACH</MenuItem>
                  <MenuItem value="credit_card">Credit Card</MenuItem>
                  <MenuItem value="cash">Cash</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Reference Number"
                value={newPayment.reference_number}
                onChange={e =>
                  setNewPayment(prev => ({
                    ...prev,
                    reference_number: e.target.value,
                  }))
                }
                placeholder="Check #, Transaction ID, etc."
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Notes"
                value={newPayment.notes}
                onChange={e =>
                  setNewPayment(prev => ({ ...prev, notes: e.target.value }))
                }
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowPaymentDialog(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={recordPayment}
            disabled={!newPayment.payment_amount || !newPayment.payment_date}
          >
            Record Payment
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default POInvoiceManager
