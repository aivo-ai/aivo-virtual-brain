import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  CardHeader,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Grid,
  Switch,
  FormControlLabel,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Chip,
  Divider,
} from '@mui/material'
import { styled } from '@mui/material/styles'
import {
  Save,
  Verified,
  Error,
  Info,
  Business,
  LocationOn,
} from '@mui/icons-material'

const StyledCard = styled(Card)(({ theme }) => ({
  marginBottom: theme.spacing(3),
  '& .MuiCardHeader-root': {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
    '& .MuiTypography-root': {
      fontWeight: 600,
    },
  },
}))

const TaxIDField = styled(TextField)(({ theme }) => ({
  '& .MuiInputBase-root': {
    fontFamily: 'monospace',
    fontSize: '0.95rem',
  },
}))

interface TaxProfile {
  tax_id?: string
  tax_id_type?: string
  tax_exempt: boolean
  exemption_certificate?: string
  billing_address: {
    line1: string
    line2?: string
    city: string
    state?: string
    postal_code: string
    country: string
  }
}

interface TaxValidationResult {
  valid: boolean
  tax_id_type?: string
  errors: string[]
  requirements: string[]
}

interface AddressValidationResult {
  valid: boolean
  errors: string[]
  suggestions?: any[]
}

const COUNTRY_OPTIONS = [
  { code: 'US', name: 'United States' },
  { code: 'CA', name: 'Canada' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  { code: 'AU', name: 'Australia' },
  { code: 'NL', name: 'Netherlands' },
  { code: 'BE', name: 'Belgium' },
  { code: 'IT', name: 'Italy' },
  { code: 'ES', name: 'Spain' },
]

const US_STATES = [
  { code: 'AL', name: 'Alabama' },
  { code: 'AK', name: 'Alaska' },
  { code: 'AZ', name: 'Arizona' },
  { code: 'AR', name: 'Arkansas' },
  { code: 'CA', name: 'California' },
  { code: 'CO', name: 'Colorado' },
  { code: 'CT', name: 'Connecticut' },
  { code: 'DE', name: 'Delaware' },
  { code: 'FL', name: 'Florida' },
  { code: 'GA', name: 'Georgia' },
  // Add more states as needed
]

const TaxSettings: React.FC = () => {
  const [taxProfile, setTaxProfile] = useState<TaxProfile>({
    tax_exempt: false,
    billing_address: {
      line1: '',
      city: '',
      postal_code: '',
      country: 'US',
    },
  })

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [taxValidation, setTaxValidation] =
    useState<TaxValidationResult | null>(null)
  const [addressValidation, setAddressValidation] =
    useState<AddressValidationResult | null>(null)
  const [showTaxIdHelp, setShowTaxIdHelp] = useState(false)

  useEffect(() => {
    loadTaxProfile()
  }, [])

  const loadTaxProfile = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/tax/profile')
      if (response.ok) {
        const profile = await response.json()
        setTaxProfile(profile)
      }
    } catch (error) {
      console.error('Failed to load tax profile:', error)
    } finally {
      setLoading(false)
    }
  }

  const validateTaxId = async (taxId: string, country: string) => {
    if (!taxId || !country) return

    try {
      const response = await fetch('/api/tax/validate-id', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tax_id: taxId, country }),
      })

      const result = await response.json()
      setTaxValidation(result)
    } catch (error) {
      console.error('Tax ID validation failed:', error)
      setTaxValidation({
        valid: false,
        errors: ['Validation service unavailable'],
        requirements: [],
      })
    }
  }

  const validateAddress = async () => {
    try {
      const response = await fetch('/api/tax/validate-address', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taxProfile.billing_address),
      })

      const result = await response.json()
      setAddressValidation(result)
    } catch (error) {
      console.error('Address validation failed:', error)
      setAddressValidation({
        valid: false,
        errors: ['Address validation service unavailable'],
      })
    }
  }

  const saveTaxProfile = async () => {
    setSaving(true)
    try {
      const response = await fetch('/api/tax/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taxProfile),
      })

      if (response.ok) {
        alert('Tax settings saved successfully')
      } else {
        alert('Failed to save tax settings')
      }
    } catch (error) {
      console.error('Failed to save tax profile:', error)
      alert('Failed to save tax settings')
    } finally {
      setSaving(false)
    }
  }

  const handleTaxIdChange = (value: string) => {
    setTaxProfile(prev => ({ ...prev, tax_id: value }))
    setTaxValidation(null)

    // Debounced validation
    setTimeout(() => {
      validateTaxId(value, taxProfile.billing_address.country)
    }, 500)
  }

  const handleAddressChange = (field: string, value: string) => {
    setTaxProfile(prev => ({
      ...prev,
      billing_address: {
        ...prev.billing_address,
        [field]: value,
      },
    }))
    setAddressValidation(null)
  }

  const getTaxIdPlaceholder = (country: string) => {
    switch (country) {
      case 'US':
        return 'XX-XXXXXXX (e.g., 12-3456789)'
      case 'CA':
        return 'Business Number (e.g., 123456789RT0001)'
      case 'GB':
        return 'VAT Number (e.g., GB123456789)'
      case 'DE':
        return 'VAT ID (e.g., DE123456789)'
      case 'AU':
        return 'ABN (e.g., 12345678901)'
      default:
        return 'Tax ID Number'
    }
  }

  const getTaxIdHelp = (country: string) => {
    switch (country) {
      case 'US':
        return 'Employer Identification Number (EIN) issued by the IRS. Format: XX-XXXXXXX'
      case 'CA':
        return 'Business Number with GST/HST program identifier. Format: 9 digits + RT + 4 digits'
      case 'GB':
        return 'VAT registration number. Format: GB followed by 9 digits'
      case 'DE':
        return 'German VAT identification number. Format: DE followed by 9 digits'
      case 'AU':
        return 'Australian Business Number (ABN). Format: 11 digits'
      default:
        return 'Tax identification number for your jurisdiction'
    }
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Tax Settings
      </Typography>

      <Typography variant="body1" color="text.secondary" paragraph>
        Configure your tax information for accurate tax calculation and
        compliance.
      </Typography>

      {/* Tax Exemption */}
      <StyledCard>
        <CardHeader title="Tax Exemption Status" avatar={<Business />} />
        <CardContent>
          <FormControlLabel
            control={
              <Switch
                checked={taxProfile.tax_exempt}
                onChange={e =>
                  setTaxProfile(prev => ({
                    ...prev,
                    tax_exempt: e.target.checked,
                  }))
                }
              />
            }
            label="This organization is tax exempt"
          />

          {taxProfile.tax_exempt && (
            <Box sx={{ mt: 2 }}>
              <TextField
                fullWidth
                label="Tax Exemption Certificate Number"
                value={taxProfile.exemption_certificate || ''}
                onChange={e =>
                  setTaxProfile(prev => ({
                    ...prev,
                    exemption_certificate: e.target.value,
                  }))
                }
                placeholder="Enter exemption certificate number"
                helperText="Provide your tax exemption certificate number for verification"
              />
            </Box>
          )}
        </CardContent>
      </StyledCard>

      {/* Tax ID */}
      <StyledCard>
        <CardHeader title="Tax Identification" avatar={<Verified />} />
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Country</InputLabel>
                <Select
                  value={taxProfile.billing_address.country}
                  onChange={e => handleAddressChange('country', e.target.value)}
                  label="Country"
                >
                  {COUNTRY_OPTIONS.map(country => (
                    <MenuItem key={country.code} value={country.code}>
                      {country.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TaxIDField
                  fullWidth
                  label="Tax ID Number"
                  value={taxProfile.tax_id || ''}
                  onChange={e => handleTaxIdChange(e.target.value)}
                  placeholder={getTaxIdPlaceholder(
                    taxProfile.billing_address.country
                  )}
                  InputProps={{
                    endAdornment: taxValidation && (
                      <Chip
                        size="small"
                        icon={taxValidation.valid ? <Verified /> : <Error />}
                        label={taxValidation.valid ? 'Valid' : 'Invalid'}
                        color={taxValidation.valid ? 'success' : 'error'}
                      />
                    ),
                  }}
                />
                <Button
                  variant="outlined"
                  onClick={() => setShowTaxIdHelp(true)}
                  sx={{ minWidth: 'auto', px: 1 }}
                >
                  <Info />
                </Button>
              </Box>

              {taxValidation && !taxValidation.valid && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  {taxValidation.errors.join(', ')}
                </Alert>
              )}

              {taxValidation &&
                taxValidation.valid &&
                taxValidation.tax_id_type && (
                  <Alert severity="success" sx={{ mt: 1 }}>
                    Valid{' '}
                    {taxValidation.tax_id_type.replace('_', ' ').toUpperCase()}
                  </Alert>
                )}
            </Grid>
          </Grid>
        </CardContent>
      </StyledCard>

      {/* Billing Address */}
      <StyledCard>
        <CardHeader title="Billing Address" avatar={<LocationOn />} />
        <CardContent>
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                required
                label="Address Line 1"
                value={taxProfile.billing_address.line1}
                onChange={e => handleAddressChange('line1', e.target.value)}
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Address Line 2"
                value={taxProfile.billing_address.line2 || ''}
                onChange={e => handleAddressChange('line2', e.target.value)}
              />
            </Grid>

            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                required
                label="City"
                value={taxProfile.billing_address.city}
                onChange={e => handleAddressChange('city', e.target.value)}
              />
            </Grid>

            <Grid item xs={12} md={4}>
              {taxProfile.billing_address.country === 'US' ? (
                <FormControl fullWidth required>
                  <InputLabel>State</InputLabel>
                  <Select
                    value={taxProfile.billing_address.state || ''}
                    onChange={e => handleAddressChange('state', e.target.value)}
                    label="State"
                  >
                    {US_STATES.map(state => (
                      <MenuItem key={state.code} value={state.code}>
                        {state.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              ) : (
                <TextField
                  fullWidth
                  label="State/Province"
                  value={taxProfile.billing_address.state || ''}
                  onChange={e => handleAddressChange('state', e.target.value)}
                />
              )}
            </Grid>

            <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                required
                label="Postal Code"
                value={taxProfile.billing_address.postal_code}
                onChange={e =>
                  handleAddressChange('postal_code', e.target.value)
                }
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
            <Button
              variant="outlined"
              onClick={validateAddress}
              disabled={
                !taxProfile.billing_address.line1 ||
                !taxProfile.billing_address.city
              }
            >
              Validate Address
            </Button>
          </Box>

          {addressValidation && !addressValidation.valid && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Address validation failed: {addressValidation.errors.join(', ')}
            </Alert>
          )}

          {addressValidation && addressValidation.valid && (
            <Alert severity="success" sx={{ mt: 2 }}>
              Address is valid
            </Alert>
          )}
        </CardContent>
      </StyledCard>

      {/* Save Button */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3 }}>
        <Button
          variant="contained"
          size="large"
          onClick={saveTaxProfile}
          disabled={saving || loading}
          startIcon={<Save />}
        >
          {saving ? 'Saving...' : 'Save Tax Settings'}
        </Button>
      </Box>

      {/* Tax ID Help Dialog */}
      <Dialog
        open={showTaxIdHelp}
        onClose={() => setShowTaxIdHelp(false)}
        maxWidth="md"
      >
        <DialogTitle>Tax ID Requirements</DialogTitle>
        <DialogContent>
          <Typography variant="h6" gutterBottom>
            {
              COUNTRY_OPTIONS.find(
                c => c.code === taxProfile.billing_address.country
              )?.name
            }
          </Typography>
          <Typography paragraph>
            {getTaxIdHelp(taxProfile.billing_address.country)}
          </Typography>

          {taxValidation && taxValidation.requirements.length > 0 && (
            <>
              <Typography variant="subtitle2" gutterBottom>
                Requirements:
              </Typography>
              <ul>
                {taxValidation.requirements.map((req, index) => (
                  <li key={index}>{req}</li>
                ))}
              </ul>
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowTaxIdHelp(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default TaxSettings
