import { ConsentSettings } from '../hooks/useOnboarding'

// Base API URL
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export interface ConsentRecord {
  id: string
  userId: string
  learnerId?: string
  consentType: 'media' | 'chat' | 'third_party' | 'data_processing' | 'terms'
  granted: boolean
  timestamp: string
  ipAddress?: string
  userAgent?: string
  version: string
}

export interface ConsentRequest {
  userId: string
  learnerId?: string
  consents: Array<{
    consentType: ConsentRecord['consentType']
    granted: boolean
  }>
}

export interface ConsentSummary {
  userId: string
  learnerId?: string
  mediaConsent: boolean
  chatConsent: boolean
  thirdPartyConsent: boolean
  dataProcessingConsent: boolean
  termsAccepted: boolean
  lastUpdated: string
}

class ConsentClient {
  async recordConsents(consentData: ConsentRequest): Promise<ConsentRecord[]> {
    const response = await fetch(`${API_BASE}/consent-svc/consents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token')}`,
      },
      body: JSON.stringify(consentData),
    })

    if (!response.ok) {
      throw new Error(`Failed to record consents: ${response.statusText}`)
    }

    return response.json()
  }

  async getConsentSummary(
    userId: string,
    learnerId?: string
  ): Promise<ConsentSummary> {
    const params = new URLSearchParams({ userId })
    if (learnerId) {
      params.append('learnerId', learnerId)
    }

    const response = await fetch(
      `${API_BASE}/consent-svc/consents/summary?${params}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get consent summary: ${response.statusText}`)
    }

    return response.json()
  }

  async getConsentHistory(
    userId: string,
    learnerId?: string
  ): Promise<ConsentRecord[]> {
    const params = new URLSearchParams({ userId })
    if (learnerId) {
      params.append('learnerId', learnerId)
    }

    const response = await fetch(
      `${API_BASE}/consent-svc/consents/history?${params}`,
      {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to get consent history: ${response.statusText}`)
    }

    return response.json()
  }

  async updateConsent(
    userId: string,
    consentType: ConsentRecord['consentType'],
    granted: boolean,
    learnerId?: string
  ): Promise<ConsentRecord> {
    const response = await fetch(
      `${API_BASE}/consent-svc/consents/${consentType}`,
      {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          userId,
          learnerId,
          granted,
        }),
      }
    )

    if (!response.ok) {
      throw new Error(`Failed to update consent: ${response.statusText}`)
    }

    return response.json()
  }

  async revokeConsent(
    userId: string,
    consentType: ConsentRecord['consentType'],
    learnerId?: string
  ): Promise<ConsentRecord> {
    return this.updateConsent(userId, consentType, false, learnerId)
  }

  async recordOnboardingConsents(
    userId: string,
    settings: ConsentSettings
  ): Promise<ConsentRecord[]> {
    const consents = [
      { consentType: 'media' as const, granted: settings.mediaConsent },
      { consentType: 'chat' as const, granted: settings.chatConsent },
      {
        consentType: 'third_party' as const,
        granted: settings.thirdPartyConsent,
      },
      {
        consentType: 'data_processing' as const,
        granted: settings.dataProcessingConsent,
      },
      { consentType: 'terms' as const, granted: settings.termsAccepted },
    ]

    return this.recordConsents({
      userId,
      consents,
    })
  }

  async checkRequiredConsents(userId: string): Promise<{
    hasRequiredConsents: boolean
    missingConsents: ConsentRecord['consentType'][]
  }> {
    const summary = await this.getConsentSummary(userId)
    const requiredConsents: ConsentRecord['consentType'][] = [
      'data_processing',
      'terms',
    ]
    const missingConsents = requiredConsents.filter(type => {
      switch (type) {
        case 'data_processing':
          return !summary.dataProcessingConsent
        case 'terms':
          return !summary.termsAccepted
        default:
          return false
      }
    })

    return {
      hasRequiredConsents: missingConsents.length === 0,
      missingConsents,
    }
  }
}

export const consentClient = new ConsentClient()
